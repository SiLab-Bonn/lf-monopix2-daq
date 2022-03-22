import os,sys,time
import numpy as np
import bitarray
import tables as tb
import yaml
import math
import matplotlib.pyplot as plt

import monopix2_daq.scan_base as scan_base
import monopix2_daq.analysis.interpreter as interpreter
import monopix2_daq.analysis.scan_utils as scan_utils
from monopix2_daq.analysis import analysis_dataproc
from monopix2_daq.analysis import plotting
from matplotlib import colors, cm, figure
from tqdm import tqdm

"""
    This script attempts to tune the current enabled pixels TRIM DAC to have a threshold as close as possible to the target injection value.  
"""

local_configuration={
    "exp_time": 0.5,
    "cnt_th": 2,                           # Number of counts in "exp_time" to consider a pixel noisy
    "thlist": None,                        # List of global threshold values [TH1,TH2,TH3]
    "phaselist_param": None,               # List of phases
    "n_mask_pix":170,                       # Maximum number of enabled pixels on every injection/TH step
    "disable_notenabled_pixel": False,     # A flag to determine if non-injected pixels are disabled while injecting
    "mask_step": None,                     # Number of pixels between injected pixels in the same column (overwrites n_mask_pix if not None)
    "with_calibration": True,              # Determine if calibration is used in the output plots
    "c_inj": 2.76e-15,                     # Injection capacitance value in F
    "lsb_dac": None,                       # LSB dac value
}

class TuneTHnoise(scan_base.ScanBase):
    scan_id = "tune_threshold_noise"

    def scan(self, exp_time=1.0, cnt_th=4, thlist=[1.0, 1.0, 1.0], phaselist_param=[0, 16, 1], n_mask_pix=170, mask_step=4, lsb_dac=None, disable_notenabled_pixel=False, **kwargs):
        """
            Execute an injection based tuning scan.
            This script attempts to tune the current enabled pixels TRIM DAC to have a threshold as close as possible to the target injection value.
        """
        # Load kwargs or default values.
        with_tlu = kwargs.pop('with_tlu', False)
        with_inj = kwargs.pop('with_inj', False)
        with_rx1 = kwargs.pop('with_rx1', False)
        with_mon = kwargs.pop('with_mon', False)
        debug_flag=False

        # Set a hard-coded limit on the maximum  number of pixels injected simultaneously.
        n_mask_pix_limit = 170

        # Calculate the occupancy target for the best tuning and its (What percentage around of it is considered as "valid" too)
        occ_target = cnt_th

        # Enable pixels.
        self.monopix.set_preamp_en(self.pix, overwrite=True)

        # Enable timestamps.
        if with_tlu:
            tlu_delay = kwargs.pop('tlu_delay', 8)
            self.monopix.set_tlu(tlu_delay)
            self.monopix.set_timestamp640(src="tlu")
        if with_inj:
            self.monopix.set_timestamp640(src="inj")
        if with_rx1:
            self.monopix.set_timestamp640(src="rx1")
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

        # Determine the number of pixels between the injected pixels for the mask. Limits by the maximum number of injected pixels, if needed.
        if mask_step is not None:    
            if mask_step < (math.ceil(len(self.pix)/n_mask_pix_limit)):
                mask_step = (math.ceil(len(self.pix)/n_mask_pix_limit))
            else:
                pass
        else:
            mask_step = (math.ceil(len(self.pix)/n_mask_pix))

        # Create a list of masks to be applied for every injection step.
        list_of_masks=scan_utils.generate_mask(n_cols=self.monopix.chip_props["COL_SIZE"], n_rows=self.monopix.chip_props["ROW_SIZE"], mask_steps=mask_step, return_lists=False)
        mask_n=len(list_of_masks)
        n_mask_pix=int(math.ceil(self.monopix.chip_props["ROW_SIZE"]/(mask_step*1.0)) * len(np.unique([coln[0] for coln in self.pix], axis=0)) )

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

        # Make a useful copies of the original enabled pixel and TRIM DAC masks.
        en_org = np.copy(self.monopix.PIXEL_CONF["EnPre"])
        trim_org = np.copy(self.monopix.PIXEL_CONF["Trim"])
        en_ref = np.copy(self.monopix.PIXEL_CONF["EnPre"])
        trim_ref = np.copy(self.monopix.PIXEL_CONF["Trim"])

        # Define the corresponding TRIM steps to do in binary search.
        tune_steps = np.arange(0,16,1)
        # Initialize two empty maps that will keep track of the best current TRIM DAC values. (One for the TDAC value, one for the smallest absolute difference to target occupancy) 
        best_results_map = np.zeros(shape=(self.monopix.chip_props["COL_SIZE"], self.monopix.chip_props["ROW_SIZE"]), dtype=float)
        # Create an empty map that will keep track of the signs for the step in enabled pixels (According to its tuning circuitry). 
        trim_increase_sign = np.zeros(shape=self.monopix.PIXEL_CONF["EnPre"].shape, dtype=np.int8)

        tuned_flags = np.ones(shape=self.monopix.PIXEL_CONF["EnPre"].shape, dtype=np.uint32)
        tuned_flags = np.invert(np.logical_and(tuned_flags.astype(bool),en_org.astype(bool)))

        trim_ref = self.monopix.default_TDAC_mask(limit=True)
        for col in np.unique([coln[0] for coln in self.pix], axis=0):
            # Fill the TRIM step sign map (According to its tuning circuitry). 
            if col in self.monopix.chip_props["COLS_TUNING_UNI"]:
                trim_increase_sign[col,0:self.monopix.chip_props["ROW_SIZE"]] = 1
            elif col in self.monopix.chip_props["COLS_TUNING_BI"]:
                trim_increase_sign[col,0:self.monopix.chip_props["ROW_SIZE"]] = -1
        self.monopix.set_tdac(trim_ref, overwrite=True)

        # Run the tuning logic with binary search. 
        cnt=0
        for scan_param_id, t_step in enumerate(tune_steps):
            data=np.array([],dtype=np.int32)
            # Start Read-out.
            self.monopix.set_monoread()  
            for _ in range(10):
                self.monopix["fifo"]["RESET"] 
                time.sleep(0.002)
            self.monopix.set_preamp_en("none", overwrite=True)
            time.sleep(0.1)

            # Go through the masks.
            self.logger.info('Tune step {0}, aiming to tune to a noise occupancy of {1:.1e} Hits / 25 ns'.format(scan_param_id,(cnt_th*(1e-9)*25/exp_time)))
            for mask_i in range(mask_n):

                self.logger.info('Pixel Mask {0}'.format(mask_i))
                mask_pix=[]
                pix_frommask=list_of_masks[mask_i]

                # Check if the pixel in the mask is enabled originally.
                for i in range(len(pix)):
                    if pix_frommask[pix[i][0], pix[i][1]]==1 and en_ref[pix[i][0], pix[i][1]]==1:
                        mask_pix.append(pix[i])
                if disable_notenabled_pixel:
                    self.monopix.set_preamp_en(mask_pix, overwrite=True)
                    time.sleep(0.1)
                
                #if with_mon:
                #    self.monopix.set_mon_en(mask_pix[0])
                # Reset and clear trash hits before measuring.
                for _ in range(10):
                    self.monopix["fifo"]["RESET"] 
                    time.sleep(0.002)
                # Get data.
                time.sleep(exp_time)
                buf = self.monopix.get_data_now()
                self.logger.info("Amount of buf: {}".format(len(buf)))
                data = np.concatenate((data,buf), axis=None)

                self.logger.info("Amount of data: {}".format(len(data)))
                # Disable the pixel masks.
                #self.monopix.set_mon_en("none")
                pre_cnt=cnt
                cnt=self.fifo_readout.get_record_count()

            # Stop read-out.
            self.monopix.stop_monoread()

            # Interpret data and look at the occupancy map.
            fast_interpreter=interpreter.Interpreter()
            int_data, _=fast_interpreter.interpret_data(raw_data=data, meta_data=None)
            int_cleardata = int_data[np.bitwise_and(int_data["cnt"]<2, int_data["col"]<=self.monopix.chip_props["COL_SIZE"])]
            self.logger.info("Original words: {}, Expected hits: {}, Interpreted hits: {}, Filtered hits:{}".format(len(data),len(data)/3, len(int_data), len (int_cleardata)))
            occupancy_map = np.histogram2d(int_cleardata["col"],int_cleardata["row"], bins=[np.arange(0,self.monopix.chip_props["COL_SIZE"]+1,1),np.arange(0,self.monopix.chip_props["ROW_SIZE"]+1,1)])[0]

            # If the occupancy is larger than target, increase the pixel threshold value in the right direction and update the best TDAC value.
            larger_occ = (occupancy_map > ( occ_target ) )
            # Update the best results before reaching the noise.
            best_results_map[larger_occ] = trim_ref[larger_occ] + trim_increase_sign[larger_occ]
            
            for mask_i in list(range(mask_n)):
                occupied_counter=0
                pix_frommask=list_of_masks[mask_i]
                for i in range(len(self.pix)):
                    if pix_frommask[self.pix[i][0], self.pix[i][1]]==1 and en_ref[self.pix[i][0], self.pix[i][1]]==1:
                        if occupancy_map[self.pix[i][0],self.pix[i][1]] > occ_target:
                            occupied_counter=occupied_counter+1
                self.logger.info("Pixels from mask {0} with occupancy larger than threshold: {1}".format(mask_i, occupied_counter))
                if debug_flag:
                    for occupix in np.argwhere(larger_occ & pix_frommask):
                        self.logger.info("Pixel {0}: {1}".format(occupix, occupancy_map[occupix[0], occupix[1]])) 

            trim_ref[larger_occ] += ( trim_increase_sign[larger_occ] )
            tuned_flags = np.logical_or(larger_occ, tuned_flags)

            # If the occupancy is smaller than target, reduce the pixel threshold value in the right direction.
            smaller_occ = (occupancy_map < ( occ_target ) )
            smaller_occ_notTuned = np.logical_and(smaller_occ, np.invert(tuned_flags))
            trim_ref[smaller_occ_notTuned] -= ( trim_increase_sign[smaller_occ_notTuned] ) 

            # Check if values went beyond the TDAC limit.
            trim_ref[trim_ref>15]=15
            trim_ref[trim_ref<0]=0

            # Update the TDAC for the mask.
            self.monopix.set_tdac(trim_ref, overwrite=True)
            time.sleep(0.1)

        # Update the TDAC and enable again all the original pixels.
        trim_ref = best_results_map
        self.monopix.set_tdac(trim_ref, overwrite=True)
        self.monopix.stop_all_data()  
        self.monopix.set_preamp_en(en_org, overwrite=True)

    def analyze(self, data_file=None, cluster_hits=False, build_events=False, build_events_simple=False):
        pass

    def plot(self, analyzed_data_file=None, **kwargs):        
        with_calibration = kwargs.pop('with_calibration', False)
        c_inj = kwargs.pop('c_inj', 2.76e-15)

        if analyzed_data_file is None:
            analyzed_data_file = self.output_filename + '.h5'

        with plotting.Plotting(analyzed_data_file=analyzed_data_file) as p:
            p.create_config_table()
            p.create_pixel_conf_maps()
            p.create_tdac_plot()

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
    
    scan = TuneTHnoise(**vars(args))
    scan.start(**local_configuration)
    scan.analyze()
    scan.plot(**local_configuration)
