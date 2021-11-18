import os,sys,time
import numpy as np
import bitarray
import tables as tb
import yaml
import math

import monopix2_daq.scan_base as scan_base
import monopix2_daq.analysis.scan_utils as scan_utils
from monopix2_daq.analysis import analysis_dataproc
from monopix2_daq.analysis import plotting

"""
    This script scans the injection amplitude over a chip with fixed DAC settings and fits the results to determine the current effective threshold.  
"""

local_configuration={
                     "with_mon": True,                      # Enable Mon/Hit-Or timestamping (640 MHz) in data 
                     "inj_lo": 0.2,                         # Fixed value on LF-Monopix2 board for VLo
                     "injlist_param": [0.0,0.7,0.005],       # List of injection values to scan [start,end,step]
                     "thlist": None,                        # List of global threshold values [TH1,TH2,TH3]
                     "phaselist_param": None,               # List of phases
                     "n_mask_pix": 170,                       # Maximum number of enabled pixels on every injection/TH step
                     "disable_noninjected_pixel": True,     # A flag to determine if non-injected pixels are disabled while injecting
                     "mask_step": None,                     # Number of pixels between injected pixels in the same column (overwrites n_mask_pix if not None)
                     "inj_n_param": 170,                    # Number of injection pulses per pixel and step
                     "with_calibration": True,              # Determine if calibration is used in the output plots
                     "c_inj": 2.76e-15,                     # Injection capacitance value in F
                     "trim_mask": None,                     # TRIM mask
                     "trim_limit": None,                   # TRIM limit (True: High, False: Lowest, "unbiased": Unbiased)
                     "pix":[18,25]                          # Single or list of Enabled pixels

}

class ScanThreshold(scan_base.ScanBase):
    scan_id = "scan_threshold"

    def scan(self,**kwargs): 
        """
            Execute a threshold scan.
            This script scans the injection amplitude over a chip with fixed DAC settings and fits the results to determine the current effective threshold.  
        """
        # Load kwargs or default values.
        with_tlu = kwargs.pop('with_tlu', False)
        with_inj = kwargs.pop('with_inj', False)
        with_rx1 = kwargs.pop('with_rx1', False)
        with_mon = kwargs.pop('with_mon', False)
        inj_lo = kwargs.pop('inj_lo', 0.2)
        injlist_param = kwargs.pop('injlist_param', [0.0,0.5,0.05])
        thlist = kwargs.pop('thlist', [1.0,1.0,1.0])
        phaselist_param = kwargs.pop('phaselist_param', [0,16,1])
        n_mask_pix = kwargs.pop('n_mask_pix', 170)
        disable_noninjected_pixel = kwargs.pop('disable_noninjected_pixel', False)
        mask_step = kwargs.pop('mask_step', 4)
        inj_n_param = kwargs.pop('inj_n_param', self.monopix["inj"]["REPEAT"])
        trim_mask = kwargs.pop('trim_mask', None)
        trim_limit = kwargs.pop('trim_limit', None)
        pix=kwargs.pop('pix',list(np.argwhere(self.monopix.PIXEL_CONF["EnPre"][:,:])))
        debug_flag=False

        # Set a hard-coded limit on the maximum  number of pixels injected simultaneously.
        n_mask_pix_limit = 170

        # Enable pixels.
        self.monopix.set_preamp_en(pix)

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

        # Make a useful copy of the original enabled pixel mask.
        en_org = np.copy(self.monopix.PIXEL_CONF["EnPre"])

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

            cnt=0
            # Go through the masks.
            for mask_i in range(mask_n):
                self.monopix.set_preamp_en("none")
                self.logger.info('Injecting: Mask {0}, from {1:.3f} to {2:.3f} V'.format(scan_param_id,injlist[0], injlist[-1]))
                # Choose the current mask, and enable the corresponding pixels.
                mask_pix=[]
                pix_frommask=list_of_masks[mask_i]
                for i in range(len(pix)):
                    if pix_frommask[pix[i][0], pix[i][1]]==1:
                        mask_pix.append(pix[i])
                self.monopix.set_inj_en(mask_pix)
                if disable_noninjected_pixel:
                    self.monopix.set_preamp_en(mask_pix)
                if with_mon:
                    self.monopix.set_mon_en(mask_pix[0])
                #mask_pix_tmp=mask_pix
                #for i in range(n_mask_pix-len(mask_pix)):
                #    mask_pix_tmp.append([-1,-1])
                # Reset and clear trash hits before injecting.
                for _ in range(10):
                    self.monopix["fifo"]["RESET"] 
                    time.sleep(0.002)
                # Inject pixels in the mask with the current injection value.
                with self.readout(scan_param_id=scan_param_id,fill_buffer=False,clear_buffer=True, readout_interval=0.001, timeout=0):
                    self.monopix.start_inj()
                    time.sleep(0.05)
                    pre_cnt=cnt

            if debug_flag:
                self.logger.info('mask=%d pix=%s data=%d'%(mask_i,str(mask_pix),cnt-pre_cnt))
            
            # Increase scan parameter ID counter.
            scan_param_id=scan_param_id+1

            # Stop read-out.
            #self.monopix.stop_monoread()  
            #time.sleep(0.1)
            pre_cnt=cnt
            cnt=self.fifo_readout.get_record_count()

        # Stop read-out and timestamps.
        self.monopix.stop_all_data() 
        
        # Enable all originally enabled pixels.
        self.monopix.set_preamp_en(en_org)

    def analyze(self, data_file=None, cluster_hits=False, build_events=False, build_events_simple=False):
        if data_file is None:
            data_file = self.output_filename + '.h5'

        with analysis_dataproc.Analysis(raw_data_file=data_file, cluster_hits=cluster_hits, build_events=build_events, build_events_simple=build_events_simple) as a:
            a.analyze_data()
            self.analyzed_data_file = a.analyzed_data_file
        return self.analyzed_data_file

    def plot(self, analyzed_data_file=None, **kwargs):        
        with_calibration = kwargs.pop('with_calibration', False)
        c_inj = kwargs.pop('c_inj', 2.76e-15)

        if analyzed_data_file is None:
            analyzed_data_file = self.analyzed_data_file

        with plotting.Plotting(analyzed_data_file=analyzed_data_file, cal_factor=(c_inj/1.602E-19)) as p:
            p.create_config_table()
            p.create_scurves_plot()
            p.create_threshold_map(electron_axis = with_calibration)
            p.create_noise_map(electron_axis = with_calibration)
            p.create_threshold_plot(scan_parameter_name = "Injection [V]", electron_axis=with_calibration)
            p.create_noise_plot(scan_parameter_name = "Injection [V]", electron_axis=with_calibration)
            p.create_pixel_conf_maps()
            #p.create_single_scurves(scan_parameter_name="Injection [V]", electron_axis = with_calibration)

if __name__ == "__main__":
    from monopix2_daq import monopix2
    import argparse
    
    parser = argparse.ArgumentParser(usage="python scan_threshold.py -t1 0.8 -t2 0.8 -t3 0.8 -f 0:44 -p -time 50",
             formatter_class=argparse.RawTextHelpFormatter)
    parser.add_argument("-conf", "--config_file", type=str, default=None)
    parser.add_argument('-t1',"--th1", type=float, default=None)
    parser.add_argument('-t2',"--th2", type=float, default=None)
    parser.add_argument('-t3',"--th3", type=float, default=None)
    parser.add_argument("-f","--flavor", type=str, default=None)
    parser.add_argument("-p","--power_reset", action='store_const', const=1, default=0) # Default = True: Skip power reset.
    parser.add_argument('-ib',"--inj_start", type=float, 
         default=local_configuration["injlist_param"][0])
    parser.add_argument('-ie',"--inj_stop", type=float, 
         default=local_configuration["injlist_param"][1])
    parser.add_argument('-is',"--inj_step", type=float, 
         default=local_configuration["injlist_param"][2])
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
        scan = ScanThreshold(m, fout=args.output_dir, online_monitor_addr="tcp://127.0.0.1:6500")
    else:        
        scan = ScanThreshold(m,online_monitor_addr="tcp://127.0.0.1:6500")
    
    scan.start(**local_configuration)
    scan.analyze()
    scan.plot(**local_configuration)
