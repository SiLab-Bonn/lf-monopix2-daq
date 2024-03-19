import yaml
import tables as tb
import numpy as np

from monopix2_daq.analysis import scan_utils
from monopix2_daq.scans.scan_minGlobalTH import ScanMinGlobalTH
from monopix2_daq.scans.scan_threshold import ScanThreshold
from monopix2_daq.scans.tune_threshold_inj import TuneTHinj

DIRECTORY = "/media/lars/4TB/202303_DESY/W02-01_unirr/"

meta_configuration={
    ### MinGlobalTH Scan
    "exp_time": 1.0,                    # Time that the readout is enabled for data acquisition
    "cnt_th": 4,                        # Number of counts in "exp_time" to consider a pixel noisy
    "mask_factor": 0.00,               # Limit percentage of noisy pixels to be masked (per CSA)
    "th_start": [1.0, 1.0, 1.0],        # Initial global threshold values for every CSA implementation
    "th_stop": [0.7, 0.7, 0.7],         # Minimum global threshold values for every CSA implementation
    "th_step": [-0.01, -0.01, -0.01],   # Telescopic steps to reach the minimum global threshold
    "trim_mask": None,                  # TRIM mask (None: Go with TRIM limit, 'middle': Middle TRIM)
    "trim_limit": False,                # TRIM limit (True: High, False: Lowest, "unbiased": Unbiased)

    ### Threshold Scan
    "inj_lo": 0.2,                          # Fixed value on LF-Monopix2 board for VLo
    "injlist_param": [0.2, 0.65, 0.01],      # List of injection values to scan [start,end,step]
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

def _get_inj_target(config_file):
    with tb.open_file(config_file) as f:
        ThresholdMap = f.root.ThresholdMap[:, :]
        Chi2Map = f.root.Chi2Map[:, :]

    mask = np.full((56, 340), False)
    sel = np.logical_and(Chi2Map > 0., ThresholdMap > 0)  # Mask not converged fits (chi2 = 0)
    mask[~sel] = True
    data = np.ma.masked_array(ThresholdMap, mask)

    return float(np.nanmean(data))

with ScanMinGlobalTH(**meta_configuration) as scan:
    scan.start(**meta_configuration)
    scan.analyze()
    scan.plot()

meta_configuration['config_file'] = scan_utils.get_latest_config_node_from_files(DIRECTORY)
meta_configuration['trim_limit'] = None
meta_configuration['trim_mask'] = 'middle'

if meta_configuration['start_col'] in range(16, 48, 1):
    meta_configuration['start_col'] = 36
    meta_configuration['stop_col'] = 44

with ScanThreshold(**meta_configuration) as scan:
    scan.start(**meta_configuration)
    scan.analyze()
    scan.plot(**meta_configuration)

if meta_configuration['start_col'] in range(16, 48, 1):
    meta_configuration['start_col'] = 16
    meta_configuration['stop_col'] = 48

interpreted_threshold_file = scan_utils.get_latest_config_node_from_files(DIRECTORY)[:-3] + '_interpreted.h5'
inj_target = _get_inj_target(interpreted_threshold_file)
meta_configuration['inj_target'] = inj_target
print(interpreted_threshold_file, meta_configuration['inj_target'])

with TuneTHinj(**meta_configuration) as scan:
    scan.start(**meta_configuration)
    scan.analyze()
    scan.plot(**meta_configuration)

meta_configuration['config_file'] = scan_utils.get_latest_config_node_from_files(DIRECTORY)
meta_configuration['trim_limit'] = None
meta_configuration['trim_mask'] = None
meta_configuration['mask_factor'] = 0.005

# meta_configuration['injlist_param'] = [inj_target - 0.15, inj_target + 0.15, 0.005]

# with ScanThreshold(**meta_configuration) as scan:
#     scan.start(**meta_configuration)
#     scan.analyze()
#     scan.plot(**meta_configuration)

with ScanMinGlobalTH(**meta_configuration) as scan:
    scan.start(**meta_configuration)
    scan.analyze()
    scan.plot()

meta_configuration['config_file'] = scan_utils.get_latest_config_node_from_files(DIRECTORY)
meta_configuration['injlist_param'] = [0.0, 0.5, 0.01]

if meta_configuration['start_col'] in range(16, 48, 1):
    meta_configuration['start_col'] = 36
    meta_configuration['stop_col'] = 44

with ScanThreshold(**meta_configuration) as scan:
    scan.start(**meta_configuration)
    scan.analyze()
    scan.plot(**meta_configuration)

if meta_configuration['start_col'] in range(16, 48, 1):
    meta_configuration['start_col'] = 16
    meta_configuration['stop_col'] = 48

interpreted_threshold_file = scan_utils.get_latest_config_node_from_files(DIRECTORY)[:-3] + '_interpreted.h5'
inj_target = _get_inj_target(interpreted_threshold_file)
meta_configuration['inj_target'] = inj_target
print(interpreted_threshold_file, meta_configuration['inj_target'])

with TuneTHinj(**meta_configuration) as scan:
    scan.start(**meta_configuration)
    scan.analyze()
    scan.plot(**meta_configuration)


if meta_configuration['start_col'] in range(16, 48, 1):
    meta_configuration['start_col'] = 36
    meta_configuration['stop_col'] = 44

meta_configuration['config_file'] = scan_utils.get_latest_config_node_from_files(DIRECTORY)
if inj_target - 0.2 > 0:
    meta_configuration['injlist_param'] = [inj_target - 0.2, inj_target + 0.2, 0.005]
else:
    meta_configuration['injlist_param'] = [0.0, inj_target + 0.2, 0.005]

with ScanThreshold(**meta_configuration) as scan:
    scan.start(**meta_configuration)
    scan.analyze()
    scan.plot(**meta_configuration)
