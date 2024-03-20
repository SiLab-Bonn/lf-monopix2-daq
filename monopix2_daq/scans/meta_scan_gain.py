import yaml
import tables as tb

from monopix2_daq.analysis import scan_utils
from monopix2_daq.scans.scan_minGlobalTH import ScanMinGlobalTH
from monopix2_daq.scans.scan_threshold import ScanThreshold

DIRECTORY = "/home/lars/git/lf-monopix2-daq/monopix2_daq/scans/output_data/tune_debug"

meta_configuration={
    ### MinGlobalTH Scan
    "exp_time": 1.0,                    # Time that the readout is enabled for data acquisition
    "cnt_th": 4,                        # Number of counts in "exp_time" to consider a pixel noisy
    "mask_factor": 0.005,               # Limit percentage of noisy pixels to be masked (per CSA)
    "th_start": [1.0, 1.0, 1.0],        # Initial global threshold values for every CSA implementation
    "th_stop": [0.7, 0.7, 0.7],         # Minimum global threshold values for every CSA implementation
    "th_step": [-0.01,-0.01,-0.01],     # Telescopic steps to reach the minimum global threshold
    "trim_mask": None,                  # TRIM mask (None: Go with TRIM limit, 'middle': Middle TRIM)
    "trim_limit": False,                # TRIM limit (True: High, False: Lowest, "unbiased": Unbiased)
    "lsb_dac": None,                    # LSB_DAC value set in scan

    ### Threshold Scan
    "inj_lo": 0.2,                          # Fixed value on LF-Monopix2 board for VLo
    "injlist_param": [0.10, 0.7, 0.005],       # List of injection values to scan [start,end,step]
    "n_mask_pix": 170,                      # Maximum number of enabled pixels on every injection/TH step
    "inj_n_param": 100,                     # Number of injection pulses per pixel and step
    "c_inj": 2.76e-15,                      # Injection capacitance value in F

    "start_col": 48,
    "stop_col": 52,
    "start_row": 0,
    "stop_row": 340,
}

def _get_and_increase_thlist(config_file, factor):
    with tb.open_file(config_file) as f:
        pwr_tmp=yaml.full_load(f.root.meta_data.attrs.power_status)
    thlist = [pwr_tmp['TH1_set'], pwr_tmp['TH2_set'], pwr_tmp['TH3_set']]
    for i in range(len(thlist)):
        if not thlist[i] + factor > 1.5:
            thlist[i] = thlist[i] + factor
    return thlist

matrices_dic = {
    'matrix11': {'start_col': 52, 'stop_col': 56},
    'matrix12': {'start_col': 48, 'stop_col': 52},
    'matrix134': {'start_col': 36, 'stop_col': 44},  # 4 Columns per matrix are enough statistics
    'matrix2': {'start_col': 8, 'stop_col': 16},
    'matrix3': {'start_col': 0, 'stop_col': 8},
}

for key in matrices_dic:
    meta_configuration['trim_mask'] = None
    meta_configuration['trim_limit'] = False
    meta_configuration['config_file'] = None
    meta_configuration.update(matrices_dic[key])
    with ScanMinGlobalTH(**meta_configuration) as scan:
        scan.start(**meta_configuration)
        scan.analyze()
        scan.plot()

    meta_configuration['trim_limit'] = 'unbiased'
    meta_configuration['config_file'] = scan_utils.get_latest_config_node_from_files(DIRECTORY)
    meta_configuration['thlist'] = _get_and_increase_thlist(meta_configuration['config_file'], 0.005)

    with ScanThreshold(**meta_configuration) as scan:
        scan.start(**meta_configuration)
        scan.analyze()
        scan.plot(**meta_configuration)

    # Needed to measure reference current of chip - 1 matrix is sufficient
    if key in ['matrix134', 'matrix2', 'matrix3']:
        meta_configuration['trim_mask'] = 15
        meta_configuration['trim_limit'] = None
        with ScanThreshold(**meta_configuration) as scan:
            scan.start(**meta_configuration)
            scan.analyze()
            scan.plot(**meta_configuration)

        if key in ['matrix2', 'matrix3']:
            meta_configuration['trim_mask'] = 0
            with ScanThreshold(**meta_configuration) as scan:
                scan.start(**meta_configuration)
                scan.analyze()
                scan.plot(**meta_configuration)

    meta_configuration['trim_mask'] = None
    meta_configuration['trim_limit'] = 'unbiased'
    meta_configuration['config_file'] = scan_utils.get_latest_config_node_from_files(DIRECTORY)
    meta_configuration['thlist'] = _get_and_increase_thlist(meta_configuration['config_file'], 0.015)

    with ScanThreshold(**meta_configuration) as scan:
        scan.start(**meta_configuration)
        scan.analyze()
        scan.plot(**meta_configuration)
