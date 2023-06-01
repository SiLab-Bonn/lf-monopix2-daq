import numpy as np
import tables as tb
import scipy.stats as stats
import yaml
import h5py
import matplotlib.pyplot as plt
from scipy.optimize import curve_fit
from numba import njit
from numba.typed import List

# gauss Funktion definieren
def _gauss(x, *p):
    amplitude, mu, sigma = p
    return amplitude * np.exp(- (x - mu)**2.0 / (2.0 * sigma**2.0))


# Daten einlesen
with tb.open_file('/home/koray/git/lf-monopix2-daq/monopix2_daq/scans/output_data/16-39/molybdän/20230510_131540_scan_source_interpreted.h5') as scan_data_file:
    HitData_mo = scan_data_file.root.Dut[:]
with tb.open_file('/home/koray/git/lf-monopix2-daq/monopix2_daq/scans/output_data/16-39/kupfer/20230515_124225_scan_source_interpreted.h5') as scan_data_file:
    HitData_cu = scan_data_file.root.Dut[:]
with tb.open_file('/home/koray/git/lf-monopix2-daq/monopix2_daq/scans/output_data/16-39/Rubidium/20230510_160012_scan_source_interpreted.h5') as scan_data_file:
    HitData_rb = scan_data_file.root.Dut[:]
with tb.open_file('/home/koray/git/lf-monopix2-daq/monopix2_daq/scans/output_data/16-39/Silber/20230510_145128_scan_source_interpreted.h5') as scan_data_file:
    HitData_ag = scan_data_file.root.Dut[:]
with tb.open_file('/home/koray/git/lf-monopix2-daq/monopix2_daq/scans/output_data/8-15/molybdän/20230515_164416_scan_source_interpreted.h5') as scan_data_file:
    HitData_mo_2 = scan_data_file.root.Dut[:]

with tb.open_file('/home/koray/git/lf-monopix2-daq/monopix2_daq/scans/output_data/16-39/20230510_222457_scan_threshold_interpreted.h5') as threshold_data_file:
    Tot_code = threshold_data_file.root.ToTAve[:]
    scan_kwargs = yaml.full_load(threshold_data_file.root.kwargs[0])
# with tb.open_file('/home/koray/git/lf-monopix2-daq/monopix2_daq/scans/output_data/8-15/20230511_115528_scan_threshold_interpreted.h5') as threshold_data_file:
#     Tot_code = threshold_data_file.root.ToTAve[:]
#     scan_kwargs = yaml.full_load(threshold_data_file.root.kwargs[0])

    
@njit 
def get_inj_cap(HitData, Tot_code, injections, energy_xray):
    # x = np.argwhere(np.logical_and(HitData['cnt'] < 2, HitData['col'] < 60)).ravel()
    all_inj_cap=np.zeros(len(HitData))
    # for i in x:
    #     ToT_value = np.array([(HitData['te'][i] - HitData['le'][i]) & 0x3F])
    #     ToT_code_pixel = Tot_code[HitData['col'][i], HitData['row'][i]]             
    for idx, hit in enumerate(HitData):
        if hit['cnt'] < 2 and hit['col'] < 60:
            ToT_value = int((hit['te'] - hit['le']) & 0x3F)
            ToT_code_pixel = Tot_code[hit['col'], hit['row']]     
            inj_voltage = injections[np.argmin(np.absolute(ToT_code_pixel-ToT_value))]
            if inj_voltage > 0:
                capacity = (energy_xray*1.602176634e-19)/(3.6*inj_voltage)
                all_inj_cap[idx] = capacity
        else:
            all_inj_cap[idx] = -1

    return all_inj_cap

def gauss_fit(all_inj_cap):
    # Gauss fitten
    hist, bin_edges = np.histogram(all_inj_cap[all_inj_cap > 0], 64)
    bin_centers = (bin_edges[:-1] + bin_edges[1:]) / 2
    bin_centers = bin_centers *1e15


    p0 = (np.max(hist), bin_centers[np.argmax(hist)],
                        (max(bin_centers) - min(bin_centers)) / 3)

    coeff, _ = curve_fit(_gauss, bin_centers, hist, p0=p0)
    points = np.linspace(min(bin_centers), max(bin_centers), 500)
    gau = _gauss(points, *coeff)

    mu_fit = coeff[1]
    sigma_fit = coeff[2]

    plt.bar(x=bin_edges[:-1] * 1e15, height=hist, width=np.diff(bin_edges[:] * 1e15)[0], align='edge', label='Berechnete Kapazität')

    plt.xlabel("Kapazität / fF")
    plt.ylabel("Häufigkeit")
    plt.plot(points, gau, "r-", label='Normalverteilung')
    plt.grid()
    plt.legend()
    plt.show()
    
    print(mu_fit,sigma_fit)
    return mu_fit, sigma_fit


injections = np.arange(scan_kwargs['injlist_param'][0], scan_kwargs['injlist_param'][1], scan_kwargs['injlist_param'][2])
Tot_code[np.isnan(Tot_code)] = 0


# all_inj_cap_mo = get_inj_cap(HitData_mo,Tot_code,injections,17440)
# gauss_fit(all_inj_cap_mo)

# all_inj_cap_cu = get_inj_cap(HitData_cu,Tot_code,injections,8040)
# gauss_fit(all_inj_cap_cu)

# all_inj_cap_rb = get_inj_cap(HitData_rb,Tot_code,injections,13370)
# gauss_fit(all_inj_cap_rb)

all_inj_cap_ag = get_inj_cap(HitData_ag,Tot_code,injections,22100)
gauss_fit(all_inj_cap_ag)

# all_inj_cap_mo_2 = get_inj_cap(HitData_mo_2,Tot_code,injections,17440)
# gauss_fit(all_inj_cap_mo_2)