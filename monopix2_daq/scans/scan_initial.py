import os,sys,time
import numpy as np
import bitarray
import tables as tb
import yaml

import monopix2_daq.scan_base as scan_base
import monopix2_daq.analysis.interpreter as interpreter
from monopix2_daq.analysis import plotting

"""
    This scan tries to find the lowest achievable global thresholds at certain initial TRIM settings for every enabled CSA. 
"""

local_configuration={
                     "exp_time": 1.0,
                     "cnt_th": 4,                       # Number of counts in "exp_time" to consider a pixel noisy
                     "mask_factor": 0.005,              # Limit percentage of noisy pixels to be masked
                     "th_start": [0.9, 0.9, 0.9],       # Initial global threshold values for every CSA implementation
                     "th_stop": [0.7, 0.7, 0.7],        # Minimum global threshold values for every CSA implementation
                     "th_step": [-0.01,-0.01,-0.01],    # Telescopic steps to reach the minimum global threshold
                     "trim_mask": None,                 # TRIM mask
                     "pix": [28,25],                    # Initial enabled pixels
                     "trim_limit": True                 # TRIM limit (True: High, False: Lowest, None: Unbiased)
}

class ScanLowestTH(scan_base.ScanBase):
    scan_id = "scan_lowestTH"
            
    def scan(self,**kwargs): 
        """
            Execute a lowest global threshold scan.
            This scan tries to find the lowest achievable global thresholds at certain initial TRIM settings for every enabled CSA. 
        """
        exp_time = kwargs.pop('exp_time', 1.0)
        cnt_th = kwargs.pop('cnt_th', 4)
        mask_factor = kwargs.pop('mask_factor', 0.01)
        th = kwargs.pop('th_start', [0.9, 0.9, 0.9])
        th_stop = kwargs.pop('th_stop', [0.7, 0.7, 0.7])
        th_step = kwargs.pop('th_step', [-0.01,-0.01,-0.01])
        trim_mask = kwargs.pop('trim_mask', None)
        trim_limit = kwargs.pop('trim_limit', True)

        th_step_minimum= [-0.001,-0.001,-0.001]

        if trim_mask is None:
            if trim_limit is not None and isinstance(trim_limit, bool):
                tdac_mask = self.monopix.default_TDAC_mask(limit=trim_limit)
            else:
                tdac_mask = self.monopix.default_TDAC_mask(unbiased=True)
            self.monopix.set_tdac(tdac_mask)
        else:
            self.monopix.set_tdac(trim_mask)

        en_org = np.copy(self.monopix.PIXEL_CONF["EnPre"])
        en_current = np.copy(self.monopix.PIXEL_CONF["EnPre"])
        en_ref = np.ones_like(self.monopix.PIXEL_CONF["EnPre"])

        orig_pix_n = np.array([0, 0, 0])
        for col_id, cols in enumerate(en_org):
            for rows in cols[:]:
                if rows==1:
                    if col_id in self.monopix.chip_props["COLS_M1"]:
                        orig_pix_n[0] += 1
                    elif col_id in self.monopix.chip_props["COLS_M2"]:
                        orig_pix_n[1] += 1
                    elif col_id in self.monopix.chip_props["COLS_M3"]:
                        orig_pix_n[2] += 1
                    else:
                        pass
                    
        masked_pixel_limit = (orig_pix_n * mask_factor).astype(int)

        # Initialize the flag that indicates if a CSA has reached its minimum global threshold. Set to "True" immediatly if no pixel from a CSA is enabled.
        lowestTH_flag = np.array([False,False,False])
        for i, n in enumerate(orig_pix_n):
            if n==0:
                self.logger.warning("There are no pixels enabled with CSA {0}".format(i+1))
                lowestTH_flag[i]=True

        current_noisy = np.array([0, 0, 0])
        
        while (lowestTH_flag.all() == False):
            self.logger.info("----- Shifting global thresholds and checking for noisy pixels -----")
            self.logger.info("Current global thresholds: CSA 1 ({0:.4f} V, Lowest: {1}) | CSA 2 ({2:.4f} V, Lowest: {3}) | CSA 3 ({4:.4f} V, Lowest: {5})".format(
                th[0], lowestTH_flag[0], 
                th[1], lowestTH_flag[1], 
                th[2], lowestTH_flag[2]))
            self.logger.info("Noisy pixels in: CSA 1 ({0} / {1}) | CSA 2 ({2} / {3}) | CSA 3 ({4} / {5})".format(
                current_noisy[0],masked_pixel_limit[0],
                current_noisy[1],masked_pixel_limit[1],
                current_noisy[2],masked_pixel_limit[2]))
            self.logger.info("Current global threshold steps for: CSA 1 ({0} V) | CSA 2 ({1} V) | CSA 3 ({2} V)".format(
                th_step[0],
                th_step[1],
                th_step[2]))

            self.monopix.set_preamp_en(en_current)
            for i, n in enumerate(th):
                if (lowestTH_flag[i] == False):
                    th[i] += th_step[i]
                    self.monopix.set_th(th_id = i+1, th_value = th[i])
                elif (n <= th_stop[i]):
                    lowestTH_flag[i] == True
                else:    
                    pass

            self.monopix.set_monoread()
            time.sleep(exp_time)
            buf = self.monopix.get_data_now()
            self.monopix.stop_monoread()

            fast_interpreter=interpreter.Interpreter()
            int_data, _=fast_interpreter.interpret_data(raw_data=buf, meta_data=None)
            int_cleardata = int_data[np.bitwise_and(int_data["cnt"]<2, int_data["col"]<257)]
            plot2d = np.histogram2d(int_cleardata["col"],int_cleardata["row"], bins=[np.arange(0,self.monopix.chip_props["COL_SIZE"]+1,1),np.arange(0,self.monopix.chip_props["ROW_SIZE"]+1,1)])[0]
            arg=np.argwhere(plot2d > cnt_th)

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

            en_ref = np.bitwise_and(en_ref, plot2d <= cnt_th)

            for i, n in enumerate(th):
                if lowestTH_flag[i] == False:
                    if (current_noisy[i]>masked_pixel_limit[i]):
                        if ( (abs(th_step[i])/2.0) > abs(th_step_minimum[i]) ):
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
                        else:
                            self.logger.info("Pixels from CSA {0:s} have reached the lowest global TH ({1:.4f} V)".format(str(i+1), th[i]))
                            th[i] -= th_step[i]*2
                            lowestTH_flag[i] = True
                            self.logger.info("Increasing the final lowest global TH of CSA {0:s} by {1:.4f} V".format(str(i+1), -th_step[i]*2))
                            self.monopix.set_th(th_id = i+1, th_value = th[i])
                    else:
                        pass
                else:
                    pass

            en_current = np.bitwise_and(en_current, en_ref)

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
    
    parser = argparse.ArgumentParser(usage="python scan_source.py -t1 0.8 -t2 0.8 -t3 0.8 -f 0:44 -p -time 50",
             formatter_class=argparse.RawTextHelpFormatter)
    parser.add_argument("--config_file", type=str, default=None)
    parser.add_argument('-t1',"--th1", type=float, default=None)
    parser.add_argument('-t2',"--th2", type=float, default=None)
    parser.add_argument('-t3',"--th3", type=float, default=None)
    parser.add_argument("-f","--flavor", type=str, default=None)
    parser.add_argument("-p","--power_reset", action='store_const', const=1, default=0) # Default = True: Skip power reset.
    parser.add_argument("-time",'--scan_time', type=int, default=None,
                        help="Scan time in seconds.")
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
               pix.append([i,j])
    else:
        pix=[]
        m._write_pixel_mask(m.PIXEL_CONF["EnPre"])
        m._write_pixel_mask(m.PIXEL_CONF["Trim"])
        m._write_global_conf()
        
        for i in range(0,m.chip_props["COL_SIZE"]):
           for j in range(0,m.chip_props["ROW_SIZE"]):
               if m.PIXEL_CONF["EnPre"][i,j]!=0:
                   pix.append([i,j])
               else:
                   pass

    local_configuration["pix"]=pix
    m.set_preamp_en(pix)
    
    if args.scan_time is not None:
        local_configuration["scan_time"]=args.scan_time
    
    
    if args.output_dir is not None:
        scan = ScanLowestTH(m, fout=args.output_dir, online_monitor_addr="tcp://127.0.0.1:6500")
    else:        
        scan = ScanLowestTH(m,online_monitor_addr="tcp://127.0.0.1:6500")
    
    scan.start(**local_configuration)
    scan.analyze()
    scan.plot()