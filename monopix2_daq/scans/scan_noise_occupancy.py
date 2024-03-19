import time
import numpy as np
from tqdm import tqdm

import monopix2_daq.scan_base as scan_base
import monopix2_daq.analysis.interpreter as interpreter
from monopix2_daq.analysis import plotting

"""
    This scan finds noisy pixels.
"""

local_configuration={
    "with_mon": False,                  # Enable Mon/Hit-Or timestamping (640 MHz) in data
    "monitor_pixel": None,  	        # Pixel to be monitored. Format: [COL,ROW]
    "exp_time": 1.0,                    # Time that the readout is enabled for data acquisition
    "cnt_th": 4,                        # Number of counts in "exp_time" to consider a pixel noisy

    "start_col": None,
    "stop_col": None,
    "start_row": None,
    "stop_row": None,
}

class ScanNoiseOcc(scan_base.ScanBase):
    scan_id = "scan_noise_occ"
            
    def scan(self, with_mon=False, monitor_pixel=None, exp_time=1.0, cnt_th=4, mask_factor=0.005, th_start=[1.0, 1.0, 1.0], th_stop=[0.7, 0.7, 0.7], th_step=[-0.01, -0.01, -0.01], trim_mask=None, trim_limit=False, lsb_dac=None, **kwargs):
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

        # Make useful copies of the original enabled pixel mask.
        en_current = np.copy(self.monopix.PIXEL_CONF["EnPre"])
        en_ref = np.ones_like(self.monopix.PIXEL_CONF["EnPre"])
        en_where = np.full_like(en_current, True, dtype=bool)

        # Initialize a counter of the number of noisy pixels.
        current_noisy = np.array([0, 0, 0])

        self.monopix.set_preamp_en(en_current, overwrite=True)

        # Enable read-out for the corresponding exposure time.
        self.monopix.set_monoread()
        for _ in range(10):
            self.monopix["fifo"]["RESET"] 
            time.sleep(0.002)
        time.sleep(exp_time)
        buf = self.monopix.get_data_now()
        self.monopix.stop_monoread()
        self.monopix.stop_all_data()

        # Interpret data, count pixels with hits and identify if they have reached the limit occupancy.
        fast_interpreter=interpreter.Interpreter()
        int_data, _=fast_interpreter.interpret_data(raw_data=buf, meta_data=None)
        int_cleardata = int_data[np.bitwise_and(int_data["cnt"] < 2, int_data["col"] <= self.monopix.chip_props["COL_SIZE"])]
        plot2d = np.histogram2d(int_cleardata["col"], int_cleardata["row"], bins=[np.arange(0, self.monopix.chip_props["COL_SIZE"] + 1, 1), np.arange(0, self.monopix.chip_props["ROW_SIZE"] + 1, 1)])[0]
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

        # Update the current enabled pixel mask with the reference one. 
        en_current = np.bitwise_and(en_current, en_ref, where=en_where)
        self.monopix.set_preamp_en(en_current, overwrite=True)

        # Log final results. 
        self.logger.info("Found and disabled {0} noisy pixels.".format(np.sum(current_noisy)))
            

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
    
    parser = argparse.ArgumentParser(usage="python scan_noise_occupancy.py -f 0:44 -p",
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
    
    scan = ScanNoiseOcc(**local_configuration)
    scan.start(**local_configuration)
    scan.analyze()
    scan.plot()
