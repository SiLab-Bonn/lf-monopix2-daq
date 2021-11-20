import os,sys,time
import numpy as np
import bitarray
import tables as tb
import yaml
import math

import monopix2_daq.scan_base as scan_base
import monopix2_daq.analysis.interpreter as interpreter
import monopix2_daq.analysis.scan_utils as scan_utils
from monopix2_daq.analysis import analysis_dataproc
from monopix2_daq.analysis import plotting

"""
    This script attempts to tune the current enabled pixels TRIM DAC to have a threshold as close as possible to the target injection value.  
"""

local_configuration={
                     "with_mon": False,                     # Enable Mon/Hit-Or timestamping (640 MHz) in data 
                     "inj_lo": 0.2,                         # Fixed value on LF-Monopix2 board for VLo
                     "inj_target": 0.258,                    # List of injection values to scan [start,end,step]
                     "thlist": None,                        # List of global threshold values [TH1,TH2,TH3]
                     "phaselist_param": None,               # List of phases
                     "n_mask_pix":170,                       # Maximum number of enabled pixels on every injection/TH step
                     "disable_noninjected_pixel": True,     # A flag to determine if non-injected pixels are disabled while injecting
                     "mask_step": None,                     # Number of pixels between injected pixels in the same column (overwrites n_mask_pix if not None)
                     "inj_n_param": 100,                    # Number of injection pulses per pixel and step
                     "with_calibration": True,              # Determine if calibration is used in the output plots
                     "c_inj": 2.76e-15,                     # Injection capacitance value in F
                     "lsb_dac": None,                       # LSB dac value
                     "pix":[18,25]                          # Single or list of Enabled pixels

}

class TuneTHinj(scan_base.ScanBase):
    scan_id = "tune_threshold_inj"

    def scan(self,**kwargs): 
        """
            Execute an injection based tuning scan.
            This script attempts to tune the current enabled pixels TRIM DAC to have a threshold as close as possible to the target injection value.
        """
        # Load kwargs or default values.
        with_tlu = kwargs.pop('with_tlu', False)
        with_inj = kwargs.pop('with_inj', False)
        with_rx1 = kwargs.pop('with_rx1', False)
        with_mon = kwargs.pop('with_mon', False)
        inj_lo = kwargs.pop('inj_lo', 0.2)
        inj_target = kwargs.pop('inj_target', 0.22)
        thlist = kwargs.pop('thlist', [1.0,1.0,1.0])
        phaselist_param = kwargs.pop('phaselist_param', [0,16,1])
        n_mask_pix = kwargs.pop('n_mask_pix', 170)
        disable_noninjected_pixel = kwargs.pop('disable_noninjected_pixel', False)
        mask_step = kwargs.pop('mask_step', 4)
        inj_n_param = kwargs.pop('inj_n_param', self.monopix["inj"]["REPEAT"])
        lsb_dac = kwargs.pop('lsb_dac', None)
        pix=kwargs.pop('pix',list(np.argwhere(self.monopix.PIXEL_CONF["EnPre"][:,:])))

        # Set a hard-coded limit on the maximum  number of pixels injected simultaneously.
        n_mask_pix_limit = 170

        # Calculate the occupancy target for the best tuning and its (What percentage around of it is considered as "valid" too)
        occ_target = inj_n_param/2.0
        occ_acceptance = 0.05

        # Enable pixels.
        self.monopix.set_preamp_en(pix)

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

        # Maybe not necessary
        # mask_n=int((len(pix)-0.5)/n_mask_pix+1)

        # Determine the number of pixels between the injected pixels for the mask. Limits by the maximum number of injected pixels, if needed.
        if mask_step is not None:    
            if mask_step < (math.ceil(len(pix)/n_mask_pix_limit)):
                mask_step = (math.ceil(len(pix)/n_mask_pix_limit))
            else:
                pass
        else:
            mask_step = (math.ceil(len(pix)/n_mask_pix))

        # Create a list of masks to be applied for every injection step.
        list_of_masks=scan_utils.generate_mask(n_cols=self.monopix.chip_props["COL_SIZE"], n_rows=self.monopix.chip_props["ROW_SIZE"], mask_steps=mask_step, return_lists=False)
        mask_n=len(list_of_masks)
        n_mask_pix=int(math.ceil(self.monopix.chip_props["ROW_SIZE"]/(mask_step*1.0)) * len(np.unique([coln[0] for coln in pix], axis=0)) )

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

        for col in np.unique([coln[0] for coln in pix], axis=0):
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
        cnt=0
        for scan_param_id, t_step in enumerate(tune_steps):
            data=np.array([],dtype=np.int32)
            # Start Read-out.
            self.monopix.set_monoread()
            # Go through the masks.
            for mask_i in range(mask_n):
                self.logger.info('Injecting: Mask {0}, aiming to tune to Injection {1:.3f}V'.format(scan_param_id,inj_target))
                mask_pix=[]
                pix_frommask=list_of_masks[mask_i]
                # Check if the pixel in the mask is enabled originally.
                for i in range(len(pix)):
                    if pix_frommask[pix[i][0], pix[i][1]]==1 and en_ref[pix[i][0], pix[i][1]]==1:
                        mask_pix.append(pix[i])
                # Enable injection to the pixels.
                self.monopix.set_inj_en(mask_pix)
                if disable_noninjected_pixel:
                    self.monopix.set_preamp_en(mask_pix)
                if with_mon:
                    self.monopix.set_mon_en(mask_pix[0])
                #mask_pix_tmp=mask_pix
                #for i in range(n_mask_pix-len(mask_pix)):
                #    mask_pix_tmp.append([-1,-1])
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

            pre_cnt=cnt
            self.logger.info('mask=%d pix=%s data=%d'%(mask_i,str(mask_pix),cnt-pre_cnt))
            time.sleep(0.1)
            pre_cnt=cnt
            cnt=self.fifo_readout.get_record_count()

            # Update the TDAC for the mask and enable again all the original pixels.
            self.monopix.set_tdac(trim_ref, overwrite=True)
            self.monopix.set_preamp_en(en_ref)

        # Update the TDAC and enable again all the original pixels.
        trim_ref = best_results_map[:, :, 0]
        self.monopix.set_tdac(trim_ref, overwrite=True)
        self.monopix.stop_all_data()  
        self.monopix.set_preamp_en(en_org)

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
    
    parser = argparse.ArgumentParser(usage="python scan_threshold.py -t1 0.8 -t2 0.8 -t3 0.8 -f 0:44 -p -time 50",
             formatter_class=argparse.RawTextHelpFormatter)
    parser.add_argument("-conf","--config_file", type=str, default=None)
    parser.add_argument('-t1',"--th1", type=float, default=None)
    parser.add_argument('-t2',"--th2", type=float, default=None)
    parser.add_argument('-t3',"--th3", type=float, default=None)
    parser.add_argument("-f","--flavor", type=str, default=None)
    parser.add_argument("-p","--power_reset", action='store_const', const=1, default=0) # Default = True: Skip power reset.
    parser.add_argument("-nmp","--n_mask_pix",type=int,default=local_configuration["n_mask_pix"])
    parser.add_argument('-ms',"--mask_step", type=int, default=None)
    parser.add_argument('-injn',"--inj_n_param",type=int,default=local_configuration["inj_n_param"])
    parser.add_argument("-dout","--output_dir", type=str, default=None)
    
    args=parser.parse_args()
    
    m=monopix2.Monopix2(no_power_reset=not bool(args.power_reset))
    m.init()
    if args.config_file is not None:
        m.load_config(args.config_file)

    m.set_inj_en(pix="none")

    if args.th1 is not None:
        m.set_th(1,args.th1)
    if args.th2 is not None:
        m.set_th(2, args.th2)
    if args.th3 is not None:
        m.set_th(3, args.th3)

    if args.flavor is not None:
        if args.flavor=="all":
            collist=range(0,m.chip_props["COL_SIZE"])
            m.logger.info("Enabled: Full matrix")
        else:
            tmp=args.flavor.split(":")
            collist=range(int(tmp[0]),int(tmp[1]))
            m.logger.info("Enabled: Columns {0:s} to {1:s}".format(tmp[0], tmp[1]))

        pix=[]
        for i in collist:
           for j in range(0,m.chip_props["ROW_SIZE"]):               
               if m.PIXEL_CONF["EnPre"][i,j]!=0:
                   pix.append([i,j])
               else:
                   pass
    else:
        pix=[]
        m.set_preamp_en(m.PIXEL_CONF["EnPre"], overwrite=True)
        m.set_tdac(m.PIXEL_CONF["Trim"], overwrite=True)
        
        for i in range(0,m.chip_props["COL_SIZE"]):
           for j in range(0,m.chip_props["ROW_SIZE"]):
               if m.PIXEL_CONF["EnPre"][i,j]!=0:
                   pix.append([i,j])
               else:
                   pass

    if len(pix)>0:
        local_configuration["pix"]=pix
    else:
        pass
    
    if args.output_dir is not None:
        scan = TuneTHinj(m, fout=args.output_dir, online_monitor_addr="tcp://127.0.0.1:6500")
    else:        
        scan = TuneTHinj(m,online_monitor_addr="tcp://127.0.0.1:6500")
    
    scan.start(**local_configuration)
    scan.analyze()
    scan.plot(**local_configuration)
