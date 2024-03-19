import time
import math
import numpy as np
from tqdm import tqdm

import monopix2_daq.scan_base as scan_base
from monopix2_daq.analysis import analysis_dataproc
from monopix2_daq.analysis import plotting

"""
    This script scans the injection amplitude over a chip with fixed DAC settings and fits the results to determine the current effective threshold.  
"""

local_configuration={
    "with_inj": False,                      # Enable Inj timestamping (640 MHz) in data
    "with_mon": False,                      # Enable Mon/Hit-Or timestamping (640 MHz) in data
    "inj_lo": 0.2,                          # Fixed value on LF-Monopix2 board for VLo
    "inj_value": 0.8,                       # List of injection values to scan [start,end,step]
    "thlist": None,                         # List of global threshold values [TH1,TH2,TH3]
    "phaselist_param": None,                # List of phases (None: Single default phase, otherwise [start,end,step])
    "n_mask_pix": 170,                      # Maximum number of enabled pixels on every injection/TH step
    "disable_noninjected_pixel": False,      # A flag to determine if non-injected pixels are disabled while injecting
    "mask_step": None,                      # Number of pixels between injected pixels in the same column (overwrites n_mask_pix if not None)
    "inj_n_param": 100,                     # Number of injection pulses per pixel and step
    "with_calibration": True,               # Determine if calibration is used in the output plots
    "c_inj": 2.76e-15,                      # Injection capacitance value in F

    "start_col": None,
    "stop_col": None,
    "start_row": None,
    "stop_row": None,
}

class ScanAnalog(scan_base.ScanBase):
    scan_id = "scan_analog"

    def scan(self, with_inj=False, with_mon=False, inj_lo=0.2, inj_value=1.0, thlist=None, n_mask_pix=170, disable_noninjected_pixel=True, mask_step=None, inj_n_param=100, **kwargs):
        """
            This script scans the injection amplitude over a chip with fixed DAC settings and fits the results to determine the current effective threshold.  
        """

        # Enable pixels.
        self.monopix.set_preamp_en(self.enable_mask)

        # Enable timestamps.
        if with_inj:
            self.monopix.set_timestamp640(src="inj")
        if with_mon:
            self.monopix.set_timestamp640(src="mon")

        # Create initial list of injection masks
        if mask_step is not None:
            inj_mask_list = self.monopix.create_shift_pattern(mask_step)
        else:
            inj_mask_list = self.monopix.create_shift_pattern(math.ceil(self.monopix.chip_props['ROW_SIZE'] / n_mask_pix))

        # Initialize the scan parameter ID counter.
        scan_param_id=0

        # If no TH values were given for every CSA, set to default ones in chip.
        if thlist is None or len(thlist)==0:
            thlist=[self.monopix.SET_VALUE["TH1"], self.monopix.SET_VALUE["TH2"], self.monopix.SET_VALUE["TH3"]]

        # Set the indicated global thresholds to the chip.
        for i, n in enumerate(thlist):
            th_str_tmp="TH{0}".format(str(i+1))
            if thlist[i]>0 and self.monopix.SET_VALUE[th_str_tmp]!=thlist[i]:
                self.monopix.set_th(th_id = i+1, th_value = thlist[i])

        # Start Read-out.
        self.monopix.set_monoread()

        pbar = tqdm(total=len(inj_mask_list), unit=' Masks')

        # Calculate INJ_HI to the desired value, while taking into account the INJ_LO defined in the board.
        inj_high= inj_value + inj_lo
        self.monopix.set_inj_all(inj_high=inj_high, inj_n=inj_n_param, ext_trigger=False)

        # Reset and clear trash hits before injecting.
        for _ in range(10):
            self.monopix["fifo"]["RESET"]
            time.sleep(0.002)

        # Go through the masks.
        for mask_i in inj_mask_list:
            mask_i = np.logical_and(mask_i, self.enable_mask)
            # Skip masks with zero enabled pixels
            if not np.any(mask_i):
                pbar.update(1)
                continue

            # Enable monitors and wait a bit, since the setting seems to couple into the CSA output
            if with_mon:
                monitor_pix = [int(np.argwhere(mask_i == True)[0][0]), int(np.argwhere(mask_i == True)[0][1])]
                self.monopix.set_mon_en(monitor_pix, overwrite=True)
                time.sleep(0.05)
            self.monopix.set_inj_en(mask_i, overwrite=True)
            if disable_noninjected_pixel:
                self.monopix.set_preamp_en(mask_i, overwrite=True)

            # Reset and clear trash hits before injecting.
            for _ in range(10):
                self.monopix["fifo"]["RESET"] 
                time.sleep(0.002)
            # Inject pixels in the mask with the current injection value.
            with self.readout(scan_param_id=scan_param_id,fill_buffer=False,clear_buffer=True, readout_interval=0.001, timeout=0):
                self.monopix.start_inj()
                time.sleep(0.05)
            pbar.update(1)
        
        # Increase scan parameter ID counter.
        scan_param_id=scan_param_id+1

        pbar.close()
        # Stop read-out and timestamps.
        self.monopix.stop_all_data() 
        
        # Enable all originally enabled pixels.
        self.monopix.set_preamp_en(self.enable_mask)

    def analyze(self, data_file=None, cluster_hits=False, build_events=False, build_events_simple=False):
        if data_file is None:
            data_file = self.output_filename + '.h5'

        with analysis_dataproc.Analysis(raw_data_file=data_file, cluster_hits=cluster_hits, build_events=build_events, build_events_simple=build_events_simple) as a:
            a.analyze_data()
            self.analyzed_data_file = a.analyzed_data_file
        return self.analyzed_data_file

    def plot(self, c_inj=2.76e-15, analyzed_data_file=None, **kwargs):
        if analyzed_data_file is None:
            analyzed_data_file = self.analyzed_data_file

        with plotting.Plotting(analyzed_data_file=analyzed_data_file, cal_factor=(c_inj/1.602E-19)) as p:
            p.create_config_table()
            p.create_standard_plots()
            p.create_tot_hist()
            p.create_tdac_plot()
            p.create_tdac_map()
            p.create_pixel_conf_maps()

if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(usage="python scan_threshold.py -t1 0.8 -t2 0.8 -t3 0.8 -f 0:44 -p",
             formatter_class=argparse.RawTextHelpFormatter)
    parser.add_argument("-conf", "--config_file", type=str, default=None)
    parser.add_argument('-t1',"--th1", type=float, default=None)
    parser.add_argument('-t2',"--th2", type=float, default=None)
    parser.add_argument('-t3',"--th3", type=float, default=None)
    parser.add_argument("-f","--flavor", type=str, default=None)
    parser.add_argument("-p","--power_reset", action='store_const', const=1, default=0) # Default = True: Skip power reset.
    
    args=parser.parse_args()
    args.no_power_reset = not bool(args.power_reset)
    local_configuration.update(vars(args))
    
    scan = ScanAnalog(**local_configuration)
    scan.start(**local_configuration)
    scan.analyze()
    scan.plot(**local_configuration)