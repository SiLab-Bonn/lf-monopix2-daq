import os
import numpy as np
import tables
from numba import njit
from matplotlib import colors, cm
import matplotlib.pyplot as plt
from matplotlib.backends.backend_pdf import PdfPages
import logging
from scipy.optimize import curve_fit
from scipy.special import erf
import event_builder_utils as mono_ev_utils
import event_builder_plotting as mono_ev_plot
import analysis_utils as au

INJCAP=2.76E-15
ECHARGE=1.602E-19
cal_factor=INJCAP/ECHARGE

RX640_TAG = 0xFA #250
TLU640_TAG = 0xFB #251
INJ640_TAG = 0xFC #252
HITOR640_TAG = 0xFD #253
TLU_TAG = 0xFF #255

MONO_COL_SIZE = 56
MONO_ROW_SIZE = 340

FE_COL_SIZE = 80
FE_ROW_SIZE = 336

TS640_MAX = 0xFFFFFFFFFFFFFE
TLU_TS_MAX = 0x7FFE0
TLU_TRIGGERNUMBER_MAX = 0xFFFF # Trigger Number starts at 1
MONO_TOKEN_TS_MAX = 0xFFFFFFFFFFFE0
MONO_TOT_MAX = 0x3F #63, since TOT starts at 0

MAX_64BIT_TAG = 0x7FFFFFFFFFFFFFFF
WORD_SEARCH_DISTANCE = 20 # Search distance for associated word matching 

def load_interpreted_data(fin, fref):
    dat, ref = None, None
    try:
        with tables.open_file(fin) as f:
            dat=f.root.Dut[:]
    except:
        print ("{0} is not a valid Monopix input file.".format(fin))
        raise
    try:
        with tables.open_file(fref) as f:
            ref=f.root.Hits[:]
    except:
        print ("{0} is not a valid FE-I4 input file.".format(fref))    
        raise
    return dat, ref

def create_mono_masks(dat):
    monopix_masks = {"mono":(dat["col"]<=MONO_COL_SIZE),
                    "rx1":(dat["col"]==RX640_TAG),
                    "tlu_hr":(dat["col"]==TLU640_TAG),
                    "inj":(dat["col"]==INJ640_TAG),
                    "hitor_le":np.logical_and(dat["col"]==HITOR640_TAG,dat["row"]==0),
                    "hitor_te":np.logical_and(dat["col"]==HITOR640_TAG,dat["row"]==1),
                    "tlu":(dat["col"]==TLU_TAG)
                    }
    return monopix_masks

def create_masked_mono_data(monopix_masks, dat):
    # All the timestamp masked  data
    masked_data = {mono_key: np.int64(dat[mono_mask]["timestamp"]) for mono_key, mono_mask in monopix_masks.items()}
    # Make extra trigger number field
    masked_data["tlu_trigger_n"] = np.int64(dat[monopix_masks["tlu"]]["cnt"])
    
    return masked_data

def align_tlu_trigger_number(tlu_mask, tlu_triggerN, dat):
    tlu_triggerN[1:]=np.add.accumulate(np.diff(tlu_triggerN) & TLU_TRIGGERNUMBER_MAX) + tlu_triggerN[0]
    dat["cnt"][tlu_mask] = tlu_triggerN
    if np.count_nonzero(np.diff(dat["cnt"][tlu_mask])<=0):
        raise ValueError("Trigger number not increasing monothonically. Check your data.")

def align_tlu_timestamp(tlu_mask, tlu_timestamp, dat):
    tlu_timestamp[1:]=np.add.accumulate(np.diff(tlu_timestamp) & TLU_TS_MAX) + tlu_timestamp[0]
    dat["timestamp"][tlu_mask] = tlu_timestamp
    if np.count_nonzero(np.diff(dat["timestamp"][tlu_mask])<0):
        raise ValueError("TLU timestamp not increasing monothonically. Check your data.")

def cut_mono_before_reset(mono_mask, dat):
    print("Cutting Monopix data before Token timestamp reset...")
    mono_cut_mask = np.diff(dat[mono_mask]["timestamp"]) < 0
    cut_index = np.argwhere(mono_cut_mask)
    if len(cut_index) > 1: # Token timestamp reset more than once during the scan
        raise RuntimeError("Token timestamp reset more than once during the scan. Indeces: {0}".format(cut_index))
    elif len(cut_index) == 1:
        dat = dat[cut_index[0]:]
        print("Token timestamp was reset once during data taking, at data index: {0}".format(cut_index[0]))
    else:
        print("Token timestamp was never reset during data taking.")

def build_events(fin, fref, fout, fcal, plot_flag=False):
    """
    Build events using timestamp information from Monopix hits, scintillator (RX1) 
    and TLU (both the standard 15-bit @ 40MHz one, and the 56-bit @640 MHz one).
    """

    if plot_flag:
        evBuilderPlot = mono_ev_plot.event_Builder_Plotting(fout=fout, save_png=True, save_single_pdf=False)

    # Load Interpreted Monopix and FE-I4 data
    dat, ref = load_interpreted_data(fin, fref)
    # Load Pixel Calibration (if any)
    if fcal is not None:
        #TODO: Implement load of pixel calibration
        pass
    else:
        pix_calibration = None 
    # Define the name of a modified FE-I4 data file, that will take into account the filters and additional data provided by this event builder
    fref_valid=fref[:-3]+"_valid.h5"
    # Initialize masks of the different types of data within the whole input data set from the chip
    monopix_masks = create_mono_masks(dat)
    monopix_masked_data = create_masked_mono_data(monopix_masks=monopix_masks, dat=dat)

    # Check for Monopix data that comes up before the Monopix timestamp is reset
    cut_mono_before_reset(mono_mask=monopix_masks["mono"], dat=dat)

    # Align TLU trigger numbers in the input TLU data
    align_tlu_trigger_number(tlu_mask=monopix_masks["tlu"], tlu_triggerN=monopix_masked_data["tlu_trigger_n"], dat=dat)

    # Create an empty array of the size of the TLU data, where all TLU and data from related timestamps will be condensed 
    tlu_match_table = np.empty(len(monopix_masked_data["tlu"]),
                                dtype=[("trigger_number","<i8"),("tlu_timestamp","<i8"),("rx1_timestamp","<i8"),("tlu_HR_timestamp","<i8")])
    # Assign nearby timestamps to TLU640/HR data
    tlu_to_timestamps_match_index = mono_ev_utils.assign_timestamps_to_tlu_hr(dat=dat, tlu_match_table=tlu_match_table, search_distance=WORD_SEARCH_DISTANCE)
    # Filter the TLU640/HR words that could not find a Scintillator (RX) Word within the word search distance
    tlu_match_table = tlu_match_table[tlu_match_table["rx1_timestamp"]!=MAX_64BIT_TAG]
    print ("# of TLU words {0:d} / {1:d} ({2:.6f}% are assigned -properly or not- to a rx1_timestamp word)".format(len(tlu_match_table), tlu_to_timestamps_match_index, 100.0*len(tlu_match_table)/float(tlu_to_timestamps_match_index)))
    #TODO: Plot Timestamps and Trigger Number after overflow correction 
    # Filter TLU data words according to the difference between TLU and RX timestamps
    tlu_match_table, TLU_RX_hist, TLU_RX_box_params, TLU_RX_offset, TLU_RX_lowlim, TLU_RX_highlim = mono_ev_utils.hist_and_fit_TLUvsRXdistance(tlu_match_table, fout)
    if plot_flag:
        evBuilderPlot.plot_TLUvsRX1(hist=TLU_RX_hist, boxfit_params=TLU_RX_box_params, diff_offset=TLU_RX_offset, lower_lim=TLU_RX_lowlim, upper_lim=TLU_RX_highlim)
    # Write the filtered TLU match table to a node of the output file
    mono_ev_utils.create_data_node(file=fout, data=tlu_match_table, name="TLU", description=tlu_match_table.dtype, title='TLU with RX1 timestamp')

    # Create an empty array of the size of the Monopix data, where data from all hits will be condensed and associated with the TLU data
    monopix_match_table = np.empty(len(monopix_masked_data["mono"]), 
                                dtype=[("col","u1"),("row","<u8"),("le","u1"),("te","u1"),("tlu_timestamp","<u8"),
                                ("trigger_number","<i8"), ("token_timestamp","<u8"), ("le_timestamp","<u8"),
                                ("rx1_timestamp","<u8"),("tlu_HR_timestamp","<u8"),("flg","u1")])
    # Assign TLU timestamps to Monopix hits.
    monopix_to_tlu_match_index = mono_ev_utils.assign_tlu_to_monopix(dat=dat, monopix_match_table=monopix_match_table, search_distance=WORD_SEARCH_DISTANCE)
    # Filter the Monopix words that could not find TLU words within the search distance
    monopix_match_table = monopix_match_table[monopix_match_table["trigger_number"]!=MAX_64BIT_TAG]
    print ("# of Monopix data {0:d} / {1:d} ({2:.6f}% were assigned a TLU word)".format(len(monopix_match_table), monopix_to_tlu_match_index, 100.0*len(monopix_match_table)/float(monopix_to_tlu_match_index)))
    # Calculate the LE timestamp of every hit based on the token timestamp caused by the hit with the shortest ToT in a cluster (defined by Token Timestamp)
    mono_ev_utils.calculate_le_timestamp(monopix_match_table=monopix_match_table)

    # Assign RX1 timestamps -based on their trigger number in the TLU match table- to the Monopix data
    monopix_to_rx_match_index = mono_ev_utils.assign_rx1(monopix_match_table=monopix_match_table, tlu_match_table=tlu_match_table)
    # Filter the Monopix words that could not find reliable RX1 words in the TLU data based on Trigger Numbers
    monopix_match_table = monopix_match_table[monopix_match_table["trigger_number"]!=MAX_64BIT_TAG]
    print ("# of Monopix data {0:d} / {1:d} ({2:.6f}% were assigned a RX1 timestamp)".format(len(monopix_match_table), monopix_to_rx_match_index, 100.0*len(monopix_match_table)/float(monopix_to_rx_match_index)))

    # Create an empty array of the size of the FE-I4 data, where the filtered FE data will be located
    ref_valid_table = np.empty(len(ref), 
                                dtype=ref.dtype)
    # Filter FE-I4 events based on the selection done through timestamp comparison in the TLU data (TLU-RX distance)
    ref_to_filtered_tlu_match_index = mono_ev_utils.del_invalid_tlu_in_FE(ref=ref, tlu_match_table=tlu_match_table, ref_valid_table=ref_valid_table)
    # Write the filtered valid FE table (up to the maximum index reached) to a node of the modified FE-I4 interpreted file
    ref_valid_table=ref_valid_table[:ref_to_filtered_tlu_match_index]
    mono_ev_utils.create_data_node(file=fref_valid, data=ref_valid_table, name="Hits", description=ref_valid_table.dtype, title='Hits with valid TLU trigger number', mode="w")
    print ("# of FE data {0:d} / {1:d} ({2:.6f}% of the original FE data has a valid TLU trigger number)".format(len(ref_valid_table), len(ref), 100.0*len(ref_valid_table)/float(len(ref))))
    # Assign RX1 timestamps -based on their trigger number in the TLU match table- to the FE data
    ref_with_rx1_match_index = mono_ev_utils.assign_rx1_to_FE(ref_valid_table=ref_valid_table, tlu_match_table=tlu_match_table)
    # Filter the FE-I4 words that could not find reliable RX1 words in the TLU data based on Trigger Numbers
    ref_valid_table = ref_valid_table[ref_valid_table["trigger_number"]!=MAX_64BIT_TAG]
    # Write the valid FE table with RX1 (up to the maximum index reached) to a node of the modified FE-I4 interpreted file
    mono_ev_utils.create_data_node(file=fref_valid, data=ref_valid_table, name="Hits", description=ref_valid_table.dtype, title='Hits with valid TLU trigger number')
    print ("# of FE data {0:d} / {1:d} ({2:.6f}% were assigned a RX1 timestamp)".format(len(ref_valid_table), ref_with_rx1_match_index, 100.0*len(ref_valid_table)/float(ref_with_rx1_match_index)))
    
    # Create an empty array of the size of the Monopix data, where data specifically related to correlation will be recorded
    correlation_table = np.empty(len(monopix_masked_data["mono"]),
                                dtype=[("event_number","<i8"),("dut_col","u1"),("dut_row","u2"),("ref_col","u1"),("ref_row","u2")])
    # Correlate events between the Monopix and FE-I4
    matched_monopix_index, correlation_match_index = mono_ev_utils.correlate_ev(monopix_match_table=monopix_match_table, correlation_table=correlation_table, ref_valid_table=ref_valid_table)
    # Filter the Monopix words that could not be correlated to the FE-I4
    monopix_match_table = monopix_match_table[monopix_match_table["trigger_number"]!=MAX_64BIT_TAG]
    print ("# of Monopix data {0:d} / {1:d} ({2:.6f}% correlated to an event in the FE)".format(len(monopix_match_table), matched_monopix_index, 100.0*len(monopix_match_table)/float(matched_monopix_index)))
    # Write the filtered correlation table (up to the maximum index reached) to a node of the output file
    correlation_table=correlation_table[:correlation_match_index]
    mono_ev_utils.create_data_node(file=fout, data=correlation_table, name="Correlation", description=correlation_table.dtype, title='Correlation between Monopix and Reference FE-I4')                                            
    # Plot correlation in rows and columns
    if plot_flag:
        evBuilderPlot.plot_correlation(corr_str_orientation="Vertical", 
                                        corr_dut=correlation_table["dut_col"], corr_ref=correlation_table["ref_col"], 
                                        dim_str_dut="Column", dim_str_ref="Column", 
                                        dim_size_dut=MONO_COL_SIZE,  dim_size_ref=FE_COL_SIZE)
        evBuilderPlot.plot_correlation(corr_str_orientation="Horizontal", 
                                        corr_dut=correlation_table["dut_row"], corr_ref=correlation_table["ref_row"], 
                                        dim_str_dut="Row", dim_str_ref="Row", 
                                        dim_size_dut=MONO_ROW_SIZE,  dim_size_ref=FE_ROW_SIZE)

    # Calculate the quality of the phase (delay of the RX1 in 640MHz Clocks, with respect to the start of every 40MHz Clock)
    monopix_phase_quality, monopix_phase_fraction=mono_ev_utils.calculate_phase_quality(fout=fout, monopix_match_table=monopix_match_table)
    if plot_flag:
        evBuilderPlot.plot_phase_fraction(monopix_phase_fraction=monopix_phase_fraction)
    # Calculate the phase and assign quality in the FE-I4 data
    ref_with_phase_quality_index=mono_ev_utils.calculate_phase_in_FE(ref_valid_table=ref_valid_table,monopix_phase_quality=monopix_phase_quality)
    # Write the modified FE-I4 data to to a node of the modified FE-I4 interpreted file
    mono_ev_utils.create_data_node(file=fref_valid, data=ref_valid_table, name="Hits", description=ref_valid_table.dtype, title='Hits with valid TLU trigger number')
    
    # Create an empty array of the size of the matched Monopix data, where all valid events are recorded
    event_table = np.empty(len(monopix_match_table),
                                dtype=[("event_number","<i8"),("column","<u2"),("row","<u2"),("frame","<u2"),("charge","<f4"),
                                ("tot","<f4"),("phase","u1"),("phase_quality","u1"),("veto_flg","u1")])
    # Fill the table of events
    mono_ev_utils.fill_event_table(event_table=event_table, monopix_match_table=monopix_match_table, monopix_phase_quality=monopix_phase_quality, pix_calibration=pix_calibration)
    # Filter events according to a reasonable difference between LE and RX timestamps (Time-walk)
    event_table, LE_RX_hist, LE_RX_box_params, LE_RX_offset, LE_RX_lowlim, LE_RX_highlim = mono_ev_utils.hist_and_fit_LEvsRXdistance(monopix_match_table=monopix_match_table, event_table=event_table, fout=fout, add_safety_offset=32)
    if plot_flag:
        evBuilderPlot.plot_LEvsRX1(hist=LE_RX_hist, boxfit_params=LE_RX_box_params, diff_offset=LE_RX_offset, lower_lim=LE_RX_lowlim, upper_lim=LE_RX_highlim)
    
    # Store events to a node of the output file
    mono_ev_utils.create_data_node(file=fout, data=event_table, name="Hits", description=event_table.dtype, title='Events built with time-walk and phase')
    # Plot the time-walk, ToT and phase distribution of all built events
    if plot_flag:
        evBuilderPlot.plot_built_events(event_table=event_table, pix_calibration=pix_calibration)

    if plot_flag:
        evBuilderPlot._close_pdf()

if __name__=="__main__":  
    import argparse  
    parser = argparse.ArgumentParser(usage="python event_builder.py -fin /PATH_TO_FILE/..._scan_source_interpreted.h5 -fref /PATH_TO_FILE/..._module_0_ext_trigger_scan_interpreted.h5 -fcal /PATH_TO_FILE/..._scan_threshold_interpreted.h5",
             formatter_class=argparse.RawTextHelpFormatter)
    parser.add_argument("-fin", "--fin", type=str, default=None)
    parser.add_argument('-fref',"--fref", type=str, default=None)
    parser.add_argument('-fcal',"--fcal", type=str, default=None)
    
    args=parser.parse_args()

    if args.fin is not None:
        fin=args.fin
    else:
        fin=""
    if args.fref is not None:
        fref=args.fref
    else:
        fref=""
    if args.fcal is not None:
        fin=args.fcal
    else:
        fcal=None

    base_path=os.path.split(fin)[0]
    fin_filename=os.path.split(fin)[1]

    output_folder=os.path.join(base_path, fin_filename[:-15])
    if not os.path.exists(output_folder):
        os.makedirs(output_folder)
    fout=os.path.join(output_folder, fin_filename[:-14]+"ev.h5")

    build_events(fin, fref, fout, fcal, plot_flag=True)
