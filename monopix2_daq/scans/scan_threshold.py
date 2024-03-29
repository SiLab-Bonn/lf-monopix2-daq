import time
import math
import numpy as np
from tqdm import tqdm

import monopix2_daq.scan_base as scan_base
import monopix2_daq.analysis.scan_utils as scan_utils
from monopix2_daq.analysis import analysis_dataproc
from monopix2_daq.analysis import plotting

"""
    This script scans the injection amplitude over a chip with fixed DAC settings and fits the results to determine the current effective threshold.  
"""

local_configuration={
    "with_inj": False,                      # Enable Inj timestamping (640 MHz) in data
    "with_mon": False,                      # Enable Mon/Hit-Or timestamping (640 MHz) in data
    "inj_lo": 0.2,                          # Fixed value on LF-Monopix2 board for VLo
    "injlist_param": [0.0,0.7,0.005],       # List of injection values to scan [start,end,step]
    "thlist": None,                         # List of global threshold values [TH1,TH2,TH3]
    "phaselist_param": None,                # List of phases (None: Single default phase, otherwise [start,end,step])
    "n_mask_pix": 170,                      # Maximum number of enabled pixels on every injection/TH step
    "disable_noninjected_pixel": True,      # A flag to determine if non-injected pixels are disabled while injecting
    "mask_step": None,                      # Number of pixels between injected pixels in the same column (overwrites n_mask_pix if not None)
    "inj_n_param": 100,                     # Number of injection pulses per pixel and step
    "trim_mask": None,                      # TRIM mask (None: Go with TRIM limit, 'middle': Middle TRIM)
    "trim_limit": None,                     # TRIM limit (True: High, False: Lowest, "unbiased": Unbiased)
    "with_calibration": True,               # Determine if calibration is used in the output plots
    "c_inj": 2.76e-15,                      # Injection capacitance value in F

    "start_col": None,
    "stop_col": None,
    "start_row": None,
    "stop_row": None,
}

class ScanThreshold(scan_base.ScanBase):
    scan_id = "scan_threshold"

    def scan(self, with_inj=False, with_mon=False, inj_lo=0.2, injlist_param=[0.0, 0.7, 0.005], thlist=None, phaselist_param=None, n_mask_pix=170, disable_noninjected_pixel=True, mask_step=None, inj_n_param=100, trim_mask=None, trim_limit=None, **kwargs):
        """
            Execute a threshold scan.
            This script scans the injection amplitude over a chip with fixed DAC settings and fits the results to determine the current effective threshold.  
        """

        # Set a hard-coded limit on the maximum  number of pixels injected simultaneously.
        n_mask_pix_limit = 170

        # Enable pixels.
        self.monopix.set_preamp_en(self.enable_mask)

        # Set the corresponding TRIM DAC mask.
        if trim_mask is None:
            if trim_limit is not None and isinstance(trim_limit, bool):
                tdac_mask = self.monopix.default_TDAC_mask(limit=trim_limit)
                self.monopix.set_tdac(tdac_mask, overwrite=True)
            elif trim_limit is not None and trim_limit=="unbiased":
                tdac_mask = self.monopix.default_TDAC_mask(unbiased=True)
                self.monopix.set_tdac(tdac_mask, overwrite=True)
            else:
                pass
        else:
            if isinstance(trim_mask, int):
                self.monopix.set_tdac(trim_mask, overwrite=True)
            elif trim_mask=="middle":
                tdac_mask=np.full((self.monopix.chip_props["COL_SIZE"],self.monopix.chip_props["ROW_SIZE"]), 0, dtype=int)
                for col in list(range(0,self.monopix.chip_props["COL_SIZE"])):
                    tdac_mask[col,0:self.monopix.chip_props["ROW_SIZE"]:1] = 7
                    tdac_mask[col,0:self.monopix.chip_props["ROW_SIZE"]:2] = 8
                self.monopix.set_tdac(tdac_mask, overwrite=True)
            else:
                self.logger.info('Not a valid DAC setting') 

        # Enable timestamps.
        if with_inj:
            self.monopix.set_timestamp640(src="inj")
        if with_mon:
            self.monopix.set_timestamp640(src="mon")

        # Create the list of values to be injected. If no values were given, it will inject to the default INJ_HI in chip.
        if injlist_param is None:
            injlist=[self.monopix.SET_VALUE["INJ_HI"]]
        elif len(injlist_param)==3:
            injlist=list(np.arange(injlist_param[0],injlist_param[1],injlist_param[2]))
        else:
            injlist=[self.monopix.SET_VALUE["INJ_HI"]]
        
        # If no TH values were given for every CSA, set to default ones in chip.
        if thlist is None or len(thlist)==0:
            thlist=[self.monopix.SET_VALUE["TH1"], self.monopix.SET_VALUE["TH2"], self.monopix.SET_VALUE["TH3"]]
        
        # Create the list of injection phases to be scanned. If no values were given, it will take the current phase enabled in chip.
        if phaselist_param is None:
            phaselist=[self.monopix["inj"].get_phase()]
        elif len(phaselist_param)==3:
            phaselist=list(np.arange(phaselist_param[0],phaselist_param[1],phaselist_param[2]))
        else:
            phaselist=[self.monopix["inj"].get_phase()]

        # Create an array with all phases for every corresponding injection.
        inj_th_phase = np.reshape(np.stack(np.meshgrid(injlist,phaselist),axis=2),[-1,2])

        # Create initial list of injection masks
        if mask_step is not None:
            inj_mask_list = self.monopix.create_shift_pattern(mask_step)
        else:
            inj_mask_list = self.monopix.create_shift_pattern(math.ceil(self.monopix.chip_props['ROW_SIZE'] / n_mask_pix))

        # Initialize the scan parameter ID counter.
        scan_param_id=0

        # Save the initial injection delay and width values (Mainly used for phase-related measurements)
        inj_delay_org=self.monopix["inj"].DELAY
        inj_width_org=self.monopix["inj"].WIDTH

        # Set the indicated global thresholds to the chip.
        for i, n in enumerate(thlist):
            th_str_tmp="TH{0}".format(str(i+1))
            if thlist[i]>0 and self.monopix.SET_VALUE[th_str_tmp]!=thlist[i]:
                self.monopix.set_th(th_id = i+1, th_value = thlist[i])

        # Start Read-out.
        self.monopix.set_monoread()

        pbar = tqdm(total=len(inj_th_phase) * len(inj_mask_list), unit=' Masks')
        # Scan over injection steps and record the corresponding hits.
        for inj, phase in inj_th_phase.tolist():
            # Calculate INJ_HI to the desired value, while taking into account the INJ_LO defined in the board.
            inj_high=inj+inj_lo
            # Set the parameters for every injection step.
            if (inj_high-inj_lo)>=0 and self.monopix.SET_VALUE["INJ_HI"]!=inj_high:
                if phase>0 and self.monopix["inj"].get_phase()!=phase:
                    #self.monopix["inj"].set_phase(int(phase)%16)
                    #self.monopix["inj"].DELAY=inj_delay_org+int(phase)/16
                    #self.monopix["inj"].WIDTH=inj_width_org-int(phase)/16
                    self.monopix.set_inj_all(inj_high=inj_high, inj_n=inj_n_param, inj_width=inj_width_org-int(phase)/16, 
                                            inj_delay=inj_delay_org+int(phase)/16, inj_phase=int(phase)%16, ext_trigger=False)      
                else:
                    self.monopix.set_inj_all(inj_high=inj_high, inj_n=inj_n_param, ext_trigger=False)
            else:
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

                self.monopix.set_preamp_en("none")
                self.logger.debug('Injecting: Mask {0}, from {1:.3f} to {2:.3f} V'.format(scan_param_id,injlist[0], injlist[-1]))

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

    def plot(self, with_calibration=True, c_inj=2.76e-15, analyzed_data_file=None, **kwargs):
        if analyzed_data_file is None:
            analyzed_data_file = self.analyzed_data_file

        with plotting.Plotting(analyzed_data_file=analyzed_data_file, cal_factor=(c_inj/1.602E-19)) as p:
            p.create_config_table()
            p.create_scurves_plot()
            p.create_tot_calibration()
            p.create_threshold_map(electron_axis = with_calibration)
            p.create_noise_map(electron_axis = with_calibration)
            p.create_threshold_plot(scan_parameter_name = "Injection [V]", electron_axis=with_calibration)
            p.create_noise_plot(scan_parameter_name = "Injection [V]", electron_axis=with_calibration)
            p.create_stacked_threshold_plot(scan_parameter_name = "Injection [V]", electron_axis=with_calibration)
            p.create_tdac_plot()
            p.create_tdac_map()
            p.create_pixel_conf_maps()
            #p.create_single_scurves(scan_parameter_name="Injection [V]", electron_axis = with_calibration)

if __name__ == "__main__":
    from monopix2_daq import monopix2
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
    
    scan = ScanThreshold(**local_configuration)
    scan.start(**local_configuration)
    scan.analyze()
    scan.plot(**local_configuration)
