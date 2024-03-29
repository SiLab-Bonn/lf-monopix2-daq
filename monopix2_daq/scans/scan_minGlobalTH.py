import time
import numpy as np
from tqdm import tqdm

import monopix2_daq.scan_base as scan_base
import monopix2_daq.analysis.interpreter as interpreter
from monopix2_daq.analysis import plotting

"""
    This scan tries to find the lowest achievable global thresholds at certain initial TRIM settings for every enabled CSA. 
"""

local_configuration={
    "with_mon": False,                  # Enable Mon/Hit-Or timestamping (640 MHz) in data
    "monitor_pixel": None,  	        # Pixel to be monitored. Format: [COL,ROW]
    "exp_time": 1.0,                    # Time that the readout is enabled for data acquisition
    "cnt_th": 4,                        # Number of counts in "exp_time" to consider a pixel noisy
    "mask_factor": 0.005,               # Limit percentage of noisy pixels to be masked (per CSA)
    "th_start": [1.0, 1.0, 1.0],        # Initial global threshold values for every CSA implementation
    "th_stop": [0.7, 0.7, 0.7],         # Minimum global threshold values for every CSA implementation
    "th_step": [-0.01,-0.01,-0.01],     # Telescopic steps to reach the minimum global threshold
    "trim_mask": None,                  # TRIM mask (None: Go with TRIM limit, 'middle': Middle TRIM)
    "trim_limit": False,                # TRIM limit (True: High, False: Lowest, "unbiased": Unbiased)
    "lsb_dac": None,                    # LSB_DAC value set in scan

    "start_col": None,
    "stop_col": None,
    "start_row": None,
    "stop_row": None,
}

class ScanMinGlobalTH(scan_base.ScanBase):
    scan_id = "scan_minGlobalTH"
            
    def scan(self, with_mon=False, monitor_pixel=None, exp_time=1.0, cnt_th=4, mask_factor=0.005, th_start=[1.0, 1.0, 1.0], th_stop=[0.7, 0.7, 0.7], th_step=[-0.01, -0.01, -0.01], trim_mask=None, trim_limit=False, lsb_dac=None, **kwargs):
        """
            Execute a search scan for the lowest global threshold.
            This scan tries to find the lowest achievable global thresholds at certain initial TRIM settings for every enabled CSA. 
        """
        th = th_start

        if lsb_dac is not None:
            self.monopix.set_global_reg(TDAC_LSB=lsb_dac)

        # Enable pixels.
        self.monopix.set_preamp_en(self.enable_mask)

        # Enable monitored pixel.
        if monitor_pixel is not None:
            self.monopix.set_mon_en(monitor_pixel, overwrite=True)
        else:
            self.monopix.set_mon_en([26, 170], overwrite=True)

        # Enable timestamps.
        if with_mon:
            self.monopix.set_timestamp640(src="mon")

        # Set the minimum TH STEP to be reached on the TH search (Negative values)
        th_step_minimum= [-0.001,-0.001,-0.001]

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

        # Make useful copies of the original enabled pixel mask.
        en_current = np.copy(self.monopix.PIXEL_CONF["EnPre"])
        en_ref = np.ones_like(self.monopix.PIXEL_CONF["EnPre"])
        en_where = np.full_like(en_current, True, dtype=bool)

        # Count the total number of masked pixels: format [M1, M2, M3].
        orig_pix_n = np.array([np.count_nonzero(self.enable_mask[self.monopix.chip_props["COLS_M1"][0]:self.monopix.chip_props["COLS_M1"][-1]]),
                               np.count_nonzero(self.enable_mask[self.monopix.chip_props["COLS_M2"][0]:self.monopix.chip_props["COLS_M2"][-1]]),
                               np.count_nonzero(self.enable_mask[self.monopix.chip_props["COLS_M3"][0]:self.monopix.chip_props["COLS_M3"][-1]])])

        # Determine the maximum number of noisy/masked pixels in every CSA flavour.
        masked_pixel_limit = (orig_pix_n * mask_factor).astype(int)

        # Initialize the flag that indicates if a CSA has reached its minimum global threshold. 
        # Set to "True" immediately if no pixel from a CSA is enabled.
        lowestTH_flag = np.array([False,False,False])
        for i, n in enumerate(orig_pix_n):
            if n==0:
                self.logger.warning("There are no pixels enabled with CSA {0}".format(i+1))
                lowestTH_flag[i]=True

        # Initialize a counter of the number of noisy pixels.
        current_noisy = np.array([0, 0, 0])
        
        pbar = tqdm(total=int((th_start[0] - th_stop[0]) / np.abs(th_step[0]) * 2), unit=' Voltage steps')
        # Shift global THs and look for noisy pixels.
        while (lowestTH_flag.all() == False):
            self.logger.debug("----- Shifting global thresholds and checking for noisy pixels -----")
            self.logger.debug("Current global thresholds: CSA 1 ({0:.4f} V, Lowest: {1}) | CSA 2 ({2:.4f} V, Lowest: {3}) | CSA 3 ({4:.4f} V, Lowest: {5})".format(
                th[0], lowestTH_flag[0], 
                th[1], lowestTH_flag[1], 
                th[2], lowestTH_flag[2]))
            self.logger.debug("Noisy pixels in: CSA 1 ({0} / {1}) | CSA 2 ({2} / {3}) | CSA 3 ({4} / {5})".format(
                current_noisy[0],masked_pixel_limit[0],
                current_noisy[1],masked_pixel_limit[1],
                current_noisy[2],masked_pixel_limit[2]))
            self.logger.debug("Current global threshold steps for: CSA 1 ({0} V) | CSA 2 ({1} V) | CSA 3 ({2} V)".format(
                th_step[0],
                th_step[1],
                th_step[2]))

            # Shift global THs if you have not reached the limit.
            for i, n in enumerate(th):
                if (n <= th_stop[i]):
                    lowestTH_flag[i] == True
                if (lowestTH_flag[i] == False):
                    th[i] += th_step[i]
                    self.monopix.set_th(th_id = i+1, th_value = th[i])
            self.monopix.set_preamp_en(en_current, overwrite=True)

            # Enable read-out for the corresponding exposure time.
            self.monopix.set_monoread()
            for _ in range(10):
                self.monopix["fifo"]["RESET"] 
                time.sleep(0.002)
            time.sleep(exp_time)
            buf = self.monopix.get_data_now()
            self.monopix.stop_monoread()

            # Interpret data, count pixels with hits and identify if they have reached the limit occupancy.
            fast_interpreter=interpreter.Interpreter()
            int_data, _=fast_interpreter.interpret_data(raw_data=buf, meta_data=None)
            int_cleardata = int_data[np.bitwise_and(int_data["cnt"]<2, int_data["col"]<=self.monopix.chip_props["COL_SIZE"])]
            plot2d = np.histogram2d(int_cleardata["col"],int_cleardata["row"], bins=[np.arange(0,self.monopix.chip_props["COL_SIZE"]+1,1),np.arange(0,self.monopix.chip_props["ROW_SIZE"]+1,1)])[0]
            arg=np.argwhere(plot2d >= cnt_th)
            if len(arg)>0:
                for a in arg:
                    if a[0] in self.monopix.chip_props["COLS_M1"]:
                        current_noisy[0] +=1
                    elif a[0] in self.monopix.chip_props["COLS_M2"]:
                        current_noisy[1] +=1
                    elif a[0] in self.monopix.chip_props["COLS_M3"]:
                        current_noisy[2] +=1
            else:
                pass
            # Make a reference mask where the pixels which have reached the limit occupancy are masked.
            en_ref = np.bitwise_and(en_ref, plot2d <= cnt_th)
            pbar.update(1)

            # Check if the occupancy of pixels with hits corresponds to the limit value.
            for i, n in enumerate(th):
                if lowestTH_flag[i] == False:
                    # Check if the current number of pixels is higher than the maximum number allowed.
                    if (current_noisy[i]>masked_pixel_limit[i]):
                        # If half of the current TH step is still equal or higher than th_step_minimum:
                        # Go "up" one of the current steps and shift the step now by half of it. Enable the pixels with hits in the reference mask again. 
                        if ( (abs(th_step[i])/2.0) >= abs(th_step_minimum[i]) ):
                            th[i] -= th_step[i]
                            th_step[i] = th_step[i]/2.0
                            self.monopix.set_th(th_id = i+1, th_value = th[i])
                            current_noisy[i]=0
                            if i == 0:
                                csa_col_list = self.monopix.chip_props["COLS_M1"]
                            elif i == 1:
                                csa_col_list = self.monopix.chip_props["COLS_M2"]
                            elif i == 2:
                                csa_col_list = self.monopix.chip_props["COLS_M3"]
                            for col in csa_col_list:
                                en_ref[col,:]=1
                        # If half of the current TH step is smaller than th_step_minimum:
                        # Stop, flag the CSA's threshold as reaching its minimum and raise the TH by one step as safety measure. 
                        else:
                            self.logger.info("Pixels from CSA {0:s} have reached the lowest global TH ({1:.4f} V)".format(str(i+1), th[i]))
                            th[i] -= th_step[i]
                            lowestTH_flag[i] = True
                            col_string = "COLS_M{0}".format(str(i+1))
                            csa_col_list = self.monopix.chip_props[col_string]
                            for col in csa_col_list:
                                en_where[col,:]=False
                            self.logger.info("Increasing the final lowest global TH of CSA {0:s} by {1:.4f} V".format(str(i+1), th_step[i]))
                            self.monopix.set_th(th_id = i+1, th_value = th[i])

            # Update the current enabled pixel mask with the reference one. 
            en_current = np.bitwise_and(en_current, en_ref, where=en_where)

        pbar.close()
        self.monopix.stop_all_data()

        # Log final results. 
        self.logger.info("Minimum global thresholds reached for {0:%} of the pixels with an occupancy of {1:.1e} Hits / 25 ns".format(
            mask_factor*1.0, (cnt_th*(1e-9)*25/exp_time)
        ))
        self.logger.info("Final global thresholds: CSA 1 ({0:.4f} V, Lowest: {1}) | CSA 2 ({2:.4f} V, Lowest: {3}) | CSA 3 ({4:.4f} V, Lowest: {5})".format(
            th[0], lowestTH_flag[0], 
            th[1], lowestTH_flag[1], 
            th[2], lowestTH_flag[2]))
        self.logger.info("Number of pixels masked in: CSA 1 ({0} / {1}) | CSA 2 ({2} / {3}) | CSA 3 ({4} / {5})".format(
            current_noisy[0],masked_pixel_limit[0],
            current_noisy[1],masked_pixel_limit[1],
            current_noisy[2],masked_pixel_limit[2]))
            

    def analyze(self, data_file=None, cluster_hits=False, build_events=False, build_events_simple=False):
        pass

    def plot(self, analyzed_data_file=None):        
        if analyzed_data_file is None:
            analyzed_data_file = self.output_filename + '.h5'

        with plotting.Plotting(analyzed_data_file=analyzed_data_file) as p:
            p.create_config_table()
            try:
                #TODO: Print the right threshold values and masked pixels on top of one of the plots.
                final_mask = analyzed_data_file.root.pixel_conf.EnPre[:]
                p._plot_histogram2d(final_mask, z_min=None, z_max=None, suffix=None, xlabel='', ylabel='', title='', z_label='# of hits')
            except:
                pass
            p.create_pixel_conf_maps()
        

if __name__ == "__main__":
    from monopix2_daq import monopix2
    import argparse
    
    parser = argparse.ArgumentParser(usage="python scan_minGlobalTH.py -f 0:44 -p",
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
    
    scan = ScanMinGlobalTH(**local_configuration)
    scan.start(**local_configuration)
    scan.analyze()
    scan.plot()
