import time
import math
import numpy as np
from tqdm import tqdm

import monopix2_daq.scan_base as scan_base
import monopix2_daq.analysis.interpreter as interpreter
import monopix2_daq.analysis.scan_utils as scan_utils
from monopix2_daq.analysis import analysis_dataproc
from monopix2_daq.analysis import plotting

"""
    This script attempts to tune the current enabled pixels TRIM DAC to have a threshold as close as possible to the target injection value.  
"""

local_configuration={
    "with_inj": False,                      # Enable Inj timestamping (640 MHz) in data
    "with_mon": False,                      # Enable Mon/Hit-Or timestamping (640 MHz) in data
    "inj_lo": 0.2,                          # Fixed value on LF-Monopix2 board for VLo
    "inj_target": 0.258,                    # List of injection values to scan [start,end,step]
    "thlist": None,                         # List of global threshold values [TH1,TH2,TH3]
    "phaselist_param": None,                # List of phases
    "n_mask_pix":170,                       # Maximum number of enabled pixels on every injection/TH step
    "disable_noninjected_pixel": True,      # A flag to determine if non-injected pixels are disabled while injecting
    "mask_step": None,                      # Number of pixels between injected pixels in the same column (overwrites n_mask_pix if not None)
    "inj_n_param": 100,                     # Number of injection pulses per pixel and step
    "lsb_dac": None,                        # LSB dac value

    "start_col": None,
    "stop_col": None,
    "start_row": None,
    "stop_row": None,
}

class TuneTHinj(scan_base.ScanBase):
    scan_id = "tune_threshold_inj"

    def scan(self, with_inj=False, with_mon=False, inj_lo=0.2, inj_target=0.275, thlist=None, phaselist_param=None, n_mask_pix=170, disable_noninjected_pixel=True, mask_step=None, inj_n_param=100, lsb_dac=None, **kwargs):
        """
            Execute an injection based tuning scan.
            This script attempts to tune the current enabled pixels TRIM DAC to have a threshold as close as possible to the target injection value.
        """

        # Set a hard-coded limit on the maximum  number of pixels injected simultaneously.
        n_mask_pix_limit = 170

        # Calculate the occupancy target for the best tuning and its (What percentage around of it is considered as "valid" too)
        occ_target = inj_n_param/2.0
        occ_acceptance = 0.05

        # Enable pixels.
        self.monopix.set_preamp_en(self.enable_mask)

        # Enable timestamps.
        if with_inj:
            self.monopix.set_timestamp640(src="inj")
        if with_mon:
            self.monopix.set_timestamp640(src="mon")
        
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

        # Create initial list of injection masks
        if mask_step is not None:
            inj_mask_list = self.monopix.create_shift_pattern(mask_step)
        else:
            inj_mask_list = self.monopix.create_shift_pattern(math.ceil(self.monopix.chip_props['ROW_SIZE'] / n_mask_pix))

        # If changed from the initial configuration, set the LSB DAC value.
        if lsb_dac is not None:
            self.monopix.set_global_reg(TDAC_LSB=lsb_dac)

        # Initialize the scan parameter ID counter.
        scan_param_id=0

        # Set the indicated global thresholds to the chip.
        for i, n in enumerate(thlist):
            th_str_tmp="TH{0}".format(str(i+1))
            if thlist[i]>0 and self.monopix.SET_VALUE[th_str_tmp]!=thlist[i]:
                self.monopix.set_th(th_id = i+1, th_value = thlist[i])

        # Calculate INJ_HI to the desired value, while taking into account the INJ_LO defined in the board.
        inj_high=inj_target+inj_lo

        # Set the parameters for the target injection.
        self.monopix.set_inj_all(inj_high=inj_high, inj_n=inj_n_param, ext_trigger=False)

        # Make a useful copies of the original enabled pixel and TRIM DAC masks.
        en_org = np.copy(self.monopix.PIXEL_CONF["EnPre"])
        trim_org = np.copy(self.monopix.PIXEL_CONF["Trim"])
        en_ref = np.copy(self.monopix.PIXEL_CONF["EnPre"])
        trim_ref = np.copy(self.monopix.PIXEL_CONF["Trim"])
        tuned_flag = False

        # Define the corresponding TRIM steps to do in binary search.
        tune_steps = [4,2,1,1]
        # Initialize two empty maps that will keep track of the best current TRIM DAC values. (One for the TDAC value, one for the smallest absolute difference to target occupancy) 
        best_results_map = np.zeros((self.monopix.chip_props["COL_SIZE"], self.monopix.chip_props["ROW_SIZE"], 2), dtype=float)
        # Create an empty map that will keep track of the signs for the step in enabled pixels (According to its tuning circuitry). 
        trim_increase_sign = np.zeros(shape=self.monopix.PIXEL_CONF["EnPre"].shape, dtype=np.int16)

        for col in np.unique([coln[0] for coln in np.argwhere(self.enable_mask == 1)], axis=0):
            #Initialize TRIM DAC values in the middle of the range.
            trim_ref[col,0:self.monopix.chip_props["ROW_SIZE"]:1] = 7
            trim_ref[col,0:self.monopix.chip_props["ROW_SIZE"]:2] = 8
            # Fill the TRIM step sign map (According to its tuning circuitry). 
            if col in self.monopix.chip_props["COLS_TUNING_UNI"]:
                trim_increase_sign[col,0:self.monopix.chip_props["ROW_SIZE"]] = 1
            elif col in self.monopix.chip_props["COLS_TUNING_BI"]:
                trim_increase_sign[col,0:self.monopix.chip_props["ROW_SIZE"]] = -1
        self.monopix.set_tdac(trim_ref, overwrite=True)

        # Run the tuning logic with binary search.
        pbar = tqdm(total=int(len(tune_steps) * len(inj_mask_list)), unit=' Masks')
        for scan_param_id, t_step in enumerate(tune_steps):
            data=np.array([],dtype=np.int32)
            # Start Read-out.
            self.monopix.set_monoread()
            # Go through the masks.
            for mask_i in inj_mask_list:
                mask_i = np.logical_and(mask_i, self.enable_mask)
                # Skip masks with zero enabled pixels
                if not np.any(mask_i):
                    pbar.update(1)
                    continue

                self.logger.debug('Injecting: Mask {0}, aiming to tune to Injection {1:.3f}V'.format(scan_param_id,inj_target))

                # Enable monitors and wait a bit, since the setting seems to couple into the CSA output
                if with_mon:
                    monitor_pix = [int(np.argwhere(mask_i == True)[0][0]), int(np.argwhere(mask_i == True)[0][1])]
                    self.monopix.set_mon_en(monitor_pix, overwrite=True)
                    time.sleep(0.05)
                self.monopix.set_inj_en(mask_i, overwrite=True)
                if disable_noninjected_pixel:
                    self.monopix.set_preamp_en(mask_i, overwrite=True)

                # Reset and clear trash hits before injecting.
                time.sleep(0.01)
                for _ in range(10):
                    self.monopix["fifo"]["RESET"] 
                    time.sleep(0.002)

                # Inject and get data.
                buf = self.monopix.get_data()
                data = np.concatenate((data,buf), axis=None)
                # Disable the pixel masks.
                self.monopix.set_mon_en("none")
                self.monopix.set_preamp_en("none")
                self.monopix.set_inj_en("none")
                pbar.update(1)
                
            # Stop read-out.
            self.monopix.stop_monoread()

            # Interpret data and look at the occupancy map.
            fast_interpreter=interpreter.Interpreter()
            int_data, _=fast_interpreter.interpret_data(raw_data=data, meta_data=None)
            int_cleardata = int_data[np.bitwise_and(int_data["cnt"]<2, int_data["col"]<self.monopix.chip_props["COL_SIZE"])]
            occupancy_map = np.histogram2d(int_cleardata["col"],int_cleardata["row"], bins=[np.arange(0,self.monopix.chip_props["COL_SIZE"]+1,1),np.arange(0,self.monopix.chip_props["ROW_SIZE"]+1,1)])[0]

            # Compare the occupancy map to the occupancy target value.
            diff_mtx = np.abs(occupancy_map - occ_target)
            updated_sel = np.logical_or(diff_mtx <= best_results_map[:, :, 1], best_results_map[:, :, 1] == 0) 

            # Update to the best current results.
            best_results_map[updated_sel, 0] = trim_ref[updated_sel]  # Update best TDAC
            best_results_map[updated_sel, 1] = diff_mtx[updated_sel]  # Update smallest (absolute) difference to target occupancy (n_injections / 2)

            # If the occupancy is larger than target, increase the pixel threshold value in the right direction.
            larger_occ = (occupancy_map > ( occ_target + round(occ_target * occ_acceptance) ) )
            trim_ref[larger_occ] += ( t_step * trim_increase_sign[larger_occ]).astype(np.uint8) 

            # If the occupancy is smaller than target, reduce the pixel threshold value in the right direction.
            smaller_occ = (occupancy_map < ( occ_target - round(occ_target * occ_acceptance) ) )
            trim_ref[smaller_occ] -= ( t_step * trim_increase_sign[smaller_occ]).astype(np.uint8) 

            # Check if values went beyond the TDAC limit.
            trim_ref[trim_ref>15]=15
            trim_ref[trim_ref<0]=0

            """             
            for p in np.argwhere(en_ref == 1):
                if p in arg:
                    if p[0] in self.monopix.chip_props["COLS_TUNING_UNI"]:
                        trim_ref[p[0],p[1]] = min(trim_ref[p[0],p[1]]+1,15)
                    elif p[0] in self.monopix.chip_props["COLS_TUNING_BI"]:
                        trim_ref[p[0],p[1]] = max(trim_ref[p[0],p[1]]-1,0)
                    #en_ref[p[0],p[1]] = 0
                else:
                    if p[0] in self.monopix.chip_props["COLS_TUNING_UNI"]:
                        trim_ref[p[0],p[1]] = max(trim_ref[p[0],p[1]]-1,0)
                    elif p[0] in self.monopix.chip_props["COLS_TUNING_BI"]:
                        trim_ref[p[0],p[1]] = min(trim_ref[p[0],p[1]]+1,15) 
            """

            # Update the TDAC for the mask and enable again all the original pixels.
            self.monopix.set_tdac(trim_ref, overwrite=True)
            self.monopix.set_preamp_en(en_ref)

        pbar.close()
        # Update the TDAC and enable again all the original pixels.
        trim_ref = best_results_map[:, :, 0]
        self.monopix.set_tdac(trim_ref, overwrite=True)
        self.monopix.stop_all_data()  
        self.monopix.set_preamp_en(en_org)

    def analyze(self, data_file=None, cluster_hits=False, build_events=False, build_events_simple=False):
        pass

    def plot(self, analyzed_data_file=None, **kwargs):
        if analyzed_data_file is None:
            analyzed_data_file = self.output_filename + '.h5'

        with plotting.Plotting(analyzed_data_file=analyzed_data_file) as p:
            p.create_config_table()
            p.create_pixel_conf_maps()
            p.create_tdac_plot()
            p.create_tdac_map()

if __name__ == "__main__":
    from monopix2_daq import monopix2
    import argparse
    
    parser = argparse.ArgumentParser(usage="python scan_threshold.py -t1 0.8 -t2 0.8 -t3 0.8 -f 0:44 -p",
             formatter_class=argparse.RawTextHelpFormatter)
    parser.add_argument("-conf","--config_file", type=str, default=None)
    parser.add_argument('-t1',"--th1", type=float, default=None)
    parser.add_argument('-t2',"--th2", type=float, default=None)
    parser.add_argument('-t3',"--th3", type=float, default=None)
    parser.add_argument("-f","--flavor", type=str, default=None)
    parser.add_argument("-p","--power_reset", action='store_const', const=1, default=0) # Default = True: Skip power reset.
    
    args=parser.parse_args()
    args.no_power_reset = not bool(args.power_reset)
    local_configuration.update(vars(args))
    
    scan = TuneTHinj(**local_configuration)
    scan.start(**local_configuration)
    scan.analyze()
    scan.plot(**local_configuration)
