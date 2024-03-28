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
    "th_start": [1.0, 1.0, 1.0],        # Initial global threshold values for every CSA implementation
    "trim_mask": None,                  # TRIM mask (None: Go with TRIM limit, 'middle': Middle TRIM)
    "trim_limit": 'unbiased',                # TRIM limit (True: High, False: Lowest, "unbiased": Unbiased)
}

class scan_busyRO(scan_base.ScanBase):
    scan_id = "scan_busyRO"
            
    def scan(self, th_start=[1.0, 1.0, 1.0], trim_mask=None, trim_limit=False,**kwargs):
        """
            Keep readout busy while irradiating sensor
        """
        # Enable pixels.
        self.monopix.set_preamp_en(pix='all')
        
        for i, th in enumerate(th_start):
            self.monopix.set_th(th_id=i + 1, th_value=th)

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


        self.logger('Enabling readout')
        # Enable read-out for the corresponding exposure time.
        self.monopix.set_monoread()
        for _ in range(10):
            self.monopix["fifo"]["RESET"] 
            time.sleep(0.002)

        try:
            self.logger('Press Ctrl + C *once* to quit the scan.')
            while True:
                continue
        except KeyboardInterrupt:
            self.logger('Irradiation finished. Stopping readout.')

        self.monopix.stop_monoread()
        self.monopix.stop_all_data()

    def analyze(self):
        pass

    def plot(self):
        pass


if __name__ == "__main__":
    scan = scan_busyRO(**local_configuration)
    scan.start(**local_configuration)
