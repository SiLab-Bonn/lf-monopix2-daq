import numpy as np
from numba import njit
from numba.typed import List
import event_builder as mono_evBuilder
import analysis_utils as mono_utils
from matplotlib import colors, cm
import matplotlib.pyplot as plt
import tables


def create_data_node(file, data, name, description, title, mode="a"):
    """
    This function creates a node in a specific table file and appends the input data to it 
    """
    with tables.open_file(file, mode) as f:
        try:  ##TODO how to get existance of table?
            f.remove_node(f.root, name)
        except:
            pass
        hit_table=f.create_table(f.root, name=name, description=description, title=title)
        hit_table.append(data)

@njit
def assign_timestamps_to_tlu_hr(dat, tlu_match_table, search_distance):
    """
    This function tries to search and assign TLU and RX1 words to recorded TLU words in 640 MHz 
    """
    # Initialize a counter to keep track of found TLU640 words.
    t_i=0
    # Go through the data and look for TLU words sampled in 640 MHz.
    for d_i,d in enumerate(dat):
        # Check if the word is a TLU word.
        if d["col"]==mono_evBuilder.TLU640_TAG:
            tlu_match_table[t_i]['tlu_HR_timestamp']=d["timestamp"]
            # Initialize standard TLU and RX1 timestamps with a very large value.
            tlu_match_table[t_i]['tlu_timestamp']=mono_evBuilder.MAX_64BIT_TAG
            tlu_match_table[t_i]['rx1_timestamp']=mono_evBuilder.MAX_64BIT_TAG    
            # Search for the closest (LATER) TLU_timestamp word. IF AVAILABLE.
            for i in range(d_i+1,d_i+search_distance,1):
                if dat[i]["col"]==mono_evBuilder.TLU_TAG:
                    tlu_match_table[t_i]['tlu_timestamp']=dat[i]["timestamp"]
                    tlu_match_table[t_i]["trigger_number"]=dat[i]['cnt']                           
                    break
            # Search for the closest (EARLIER) RX1_timestamp word. IF AVAILABLE.
            for i in range(d_i-1,max(-1, d_i-search_distance),-1):
                if dat[i]["col"]==mono_evBuilder.RX640_TAG:
                    tlu_match_table[t_i]['rx1_timestamp']=dat[i]["timestamp"]
                    break
            # Increase the TLU word counter.
            t_i=t_i+1
    # Return the index of the highest TLU word
    return t_i

def hist_and_fit_TLUvsRXdistance(tlu_match_table, fout):
    """
    This function histograms and fits a box function to the distance between two input timestamps.
    It plots such distribution and the corresponding fit parameters. 
    It returns the data within a valid selection range, parameters of the box fit and low and high limit of the selection range.
    """

    # Calculate the difference between TLU_HR and RX input, and histogram it
    diff=np.int64(tlu_match_table["tlu_HR_timestamp"]-tlu_match_table["rx1_timestamp"])
    hist=np.histogram(diff, bins=np.arange(-0x80000,0x80000,1) )
    x=hist[1][:-1]
    y=hist[0]

    print("Fitting a box function to TLU-RX1 distribution...")
    boxfit_params=mono_utils.fit_boxfc(x, y)
    print ("Values found: Amp=%.2E, Mean=%.2E, Width=%.2f, Sigma_Box=%.2f"%(boxfit_params[0],boxfit_params[1],boxfit_params[2],boxfit_params[3]))

    width=boxfit_params[2]
    sigma=boxfit_params[3]

    diff_offset=boxfit_params[1]-np.abs(width)/2.0
    lower_lim=round(diff_offset-1*np.abs(width)-5*np.abs(sigma),0)
    upper_lim=round(diff_offset+2*np.abs(width)+5*np.abs(sigma),0)
    print("Rising edge of the main peak (TLU-RX1 offset @ 640MHz Clocks) located at %s"%str(diff_offset))

    print ("Filtering TLU_timestamp-Rx1_timestamp by upper_lim of ",upper_lim," and lower_lim of",lower_lim)
    diff_selection_mask=tlu_match_table[np.bitwise_and(diff<=upper_lim, diff>=lower_lim)]
    print ("# of TLU words: {0:d} / {1:d} ({2:.2f}% are discarded based on their TLU-RX1 distance)".format(len(diff_selection_mask), len(tlu_match_table), 100.0-100.0*len(diff_selection_mask)/len(tlu_match_table)))

    return diff_selection_mask, hist, boxfit_params, diff_offset, lower_lim, upper_lim

@njit
def assign_tlu_to_monopix(dat, monopix_match_table, search_distance):
    """
    This function tries to search and assign TLU_HR and TLU words to recorded Monopix words
    """
    # Initialize counters to keep track of the current position in data.
    m_i=0
    # Go through all the data set, find Monopix words and look for the closest (EARLIER) TLU_HR data word.
    for d_i,d in enumerate(dat):
        if d["col"] < mono_evBuilder.MONO_COL_SIZE:
            # Initialize Trigger number and TLU timestamps with a very large value. 
            monopix_match_table[m_i]["trigger_number"] = mono_evBuilder.MAX_64BIT_TAG
            monopix_match_table[m_i]["tlu_timestamp"] = mono_evBuilder.MAX_64BIT_TAG
            monopix_match_table[m_i]["tlu_HR_timestamp"] = mono_evBuilder.MAX_64BIT_TAG
            # Assign hit pixel information and timestamp as token timestamp.
            monopix_match_table[m_i]["col"] = d['col']
            monopix_match_table[m_i]["row"] = d['row']
            monopix_match_table[m_i]["le"] = d['le']
            monopix_match_table[m_i]["te"] = d['te']
            monopix_match_table[m_i]["flg"] = d['cnt']
            monopix_match_table[m_i]["token_timestamp"] = d['timestamp']
            # Look for the first TLU_HR words a few words behind the Monopix data, "assuming" the TLU_HR word comes always BEFORE the Monopix one. 
            for i in range(d_i-1,max(-1, d_i-search_distance),-1):
                # Check if the word is a TLU_HR word. 
                if dat[i]['col'] == mono_evBuilder.TLU640_TAG:
                    #Assign the TLU_HR word to the Monopix hit
                    monopix_match_table[m_i]["tlu_HR_timestamp"] = dat[i]['timestamp']
                    # Look for the first TLU_HR words a few words after the Monopix data, "assuming" the TLU word comes always AFTER the TLU_HR one. 
                    for j in range(i+1,i+search_distance,1):
                        if dat[j]['col'] == mono_evBuilder.TLU_TAG:
                            # Assign the TLU trigger timestamp to the hit 
                            monopix_match_table[m_i]["tlu_timestamp"] = dat[j]['timestamp']
                            # Assign the TLU trigger number to the hit
                            monopix_match_table[m_i]["trigger_number"] = np.int64(dat[j]['cnt'])
                            break
                    break
            # Increase the matched Monopix word counter.
            m_i=m_i+1
    # Return the index of the highest matched Monopix word.
    return m_i

@njit
def calculate_le_timestamp(monopix_match_table):
    """
    This function calculates the timestamp of the Leading Edge of every hit in a cluster, based on the timestamp of the token associated
    to that cluster. Note that the token goes high and is time-stamped right after the Falling Edge of the shortest hit in the cluster.
    """
    #Initialize a counter to determine the position of the first hit in a set of hits with the same timestamp
    m_i0=0
    latest_timestamp = monopix_match_table[m_i0]['token_timestamp']
    cluster_tmp = monopix_match_table[m_i0:1]
    # Go through the Monopix data set
    for m_i,m in enumerate(monopix_match_table):
        # Find the first Token Timestamp which is different than the current one
        if m['token_timestamp'] == latest_timestamp:
            cluster_tmp = monopix_match_table[m_i0:m_i+1]
        elif m['token_timestamp'] != latest_timestamp:                 
            # Calculate the ToT for all hits in the cluster
            tot = (cluster_tmp["te"]-cluster_tmp['le']) & mono_evBuilder.MONO_TOT_MAX
            # Look for the shortest ToT (The Token goes high with the TE of the shortest HitOr in the cluster)
            arg_min_tot = np.argmin(tot)
            # Calculate the offset between the token timestamp and TE of the shortest HitOr
            off = (np.int64(cluster_tmp[arg_min_tot]['token_timestamp'])-((cluster_tmp[arg_min_tot]["te"])<<4)) & 0x3FF
            # Extrapolate the timestamp of the trailing edge of the shortest hit, based on the Token Timestamp
            te_640 = cluster_tmp[arg_min_tot]['token_timestamp']-off
            # Calculate an overall distance between the LE of EVERY hit with respect to the TE of the shortest one
            le_off = (cluster_tmp["te"][arg_min_tot]-cluster_tmp['le']) & mono_evBuilder.MONO_TOT_MAX
            # Calculate and assign the LE timestamps for all hits in the cluster
            monopix_match_table['le_timestamp'][m_i0:m_i] = te_640-(le_off<<4)
            # Assign the current Monopix word as the first hit in the next cluster, and update "latest timestamp"
            m_i0 = m_i
            latest_timestamp = monopix_match_table[m_i0]['token_timestamp']
            cluster_tmp = monopix_match_table[m_i0:m_i0+1]
        else:
            pass

        # One additional step for the last cluster in data
        if m_i == (len(monopix_match_table)-1):
            # Calculate the ToT for all hits in the cluster
            tot = (cluster_tmp["te"]-cluster_tmp['le']) & mono_evBuilder.MONO_TOT_MAX
            # The Token goes high with the TE of the shortest HitOr in the cluster: 
            # Look for the shortest ToT
            arg_min_tot = np.argmin(tot)
            # Calculate the offset between the token timestamp and TE of the shortest HitOr
            off = (np.int64(cluster_tmp[arg_min_tot]['token_timestamp'])-((cluster_tmp[arg_min_tot]["te"])<<4)) & 0x3FF
            # Extrapolate the timestamp of the trailing edge of the shortest hit, based on the Token Timestamp
            te_640 = cluster_tmp[arg_min_tot]['token_timestamp']-off
            # Calculate an overall distance between the LE of EVERY hit with respect to the TE of the shortest one
            le_off = (cluster_tmp["te"][arg_min_tot]-cluster_tmp['le']) & mono_evBuilder.MONO_TOT_MAX
            # Calculate and assign the LE timestamps for all hits in the cluster
            monopix_match_table['le_timestamp'][m_i0:] = te_640-(le_off<<4)
        else:
            pass
    # Return the total number of matched Monopix words.
    return m_i+1

@njit
def assign_rx1(monopix_match_table, tlu_match_table):
    """
    Assign the RX1_timestamp (scintillator) from events in the TLU match table to events in the Monopix match table,
    based on matching trigger numbers. 
    """
    # Initialize a counter to determine the current position within the TLU array
    tlu_idx=0
    # Go through the list of Monopix hits and compare to the list of TLU words
    for m_i,m in enumerate(monopix_match_table):
        for t_i,t in enumerate(tlu_match_table[tlu_idx:]):
            # If the Monopix and TLU words have the same Trigger Number, assign the RX1 signal from the TLU word to the Monopix one
            if m["trigger_number"] == t["trigger_number"]: 
                monopix_match_table[m_i]["rx1_timestamp"] = t["rx1_timestamp"]
                tlu_idx=tlu_idx+t_i
                break
            # Else, if the TLU trigger number surpasses the one in the Monopix word, flag the trigger number to be filtered later
            # (i.e. There was not an event in the TLU table that matched the Monopix one)
            elif (m["trigger_number"]-t["trigger_number"])<0:
                monopix_match_table[m_i]["trigger_number"]=mono_evBuilder.MAX_64BIT_TAG
                #mono[m_i]["flg"]=1
                tlu_idx= max(0,tlu_idx+t_i-1)
                break
    # Return the total number of matched Monopix words.
    return m_i+1

@njit
def del_invalid_tlu_in_FE(ref, tlu_match_table, ref_valid_table):
    """
    Delete invalid TLU words in the FE-I4 data 
    (Invalid: without a reasonable scintillator timestamp assigned to the TLU word)
    """
    # Initialize counters for both TLU and filtered reference tables
    t_idx=0
    b_i=0
    # Go through the reference plane data
    for r in ref:
        # Get to the latest TLU index
        t_i=t_idx
        # Get the current FE-I4 trigger number, go to the latest TLU and compare its trigger number to the FE one 
        r_trig=np.uint(r["trigger_number"] & mono_evBuilder.TLU_TRIGGERNUMBER_MAX)
        while t_i < len(tlu_match_table):
            t_trig=np.uint(tlu_match_table[t_i]["trigger_number"] & mono_evBuilder.TLU_TRIGGERNUMBER_MAX)
            # If the trigger exists in the filtered TLU data, pass it to the filtered FE data
            if r_trig==t_trig:
                ref_valid_table[b_i] = r
                b_i = b_i + 1
                break
            # If the trigger number of the event in the TLU is larger than the front-end one, move to the next TLU event
            elif  (r_trig-t_trig) & mono_evBuilder.TLU_TRIGGERNUMBER_MAX < 0x8000:
                t_i=t_i+1
            else:
                break
        # Update the TLU index
        t_idx=t_i
    # Return the index of the highest FE-I4 word after filter.
    return b_i

@njit
def assign_rx1_to_FE(ref_valid_table, tlu_match_table):
    """
    This function writes the RX1_timestamp to corresponding events in the FE-I4 (Based on their matching trigger numbers)
    (This information is necessary in the FE data, in order to filter in-time data during test beam analysis)
    """
    # Initialize a counter to determine the current position within the TLU array
    tlu_idx=0
    # Go through the FE data, and compare its event number to the TLU trigger number (Assuming the overflow of the TLU trigger number is already taken care of)
    for f_i,f in enumerate(ref_valid_table):
        for t_i,t in enumerate(tlu_match_table[tlu_idx:]):
            # If the TLU trigger_number matches the FE event_number, assign rx1_timestamp to the TDC column
            if f["event_number"] == t["trigger_number"]:
                ref_valid_table[f_i]["TDC"] = t["rx1_timestamp"]
                tlu_idx=tlu_idx+t_i
                break
            # If the TLU trigger_number is larger than the FE event_number, flag the FE trigger number to be filtered later
            # (i.e. There was not an event in the TLU table that matched the FE one)
            elif (f["event_number"]-t["trigger_number"]) < 0:
                ref_valid_table[f_i]["trigger_number"]=mono_evBuilder.MAX_64BIT_TAG
                tlu_idx= max(0,tlu_idx+t_i-1)
                break
    # Return the total number of FE-I4 words with a matching RX1.
    return f_i+1

@njit
def correlate_ev(monopix_match_table, correlation_table, ref_valid_table):
    """
    This function correlates events in Monopix with events in the FE-I4, according to matching Trigger Numbers
    (It assumes that the overflow of Trigger Numbers in Monopix data has already been corrected)
    """
    # Initialize counters for the FE-I4 data and correlated events
    fe_idx=0
    c_i=0
    # Go through the Monopix hits and find hits in the FE with the same event number (Assuming the overflow of the TLU trigger number is already taken care of)
    for m_i,m in enumerate(monopix_match_table):
        for f_i,f in enumerate(ref_valid_table[fe_idx:]):
            # If they match, fill the correlation table
            if m["trigger_number"] == f["event_number"]:
                correlation_table[c_i]["event_number"]=f["event_number"]
                correlation_table[c_i]["dut_col"]=m["col"]
                correlation_table[c_i]["ref_row"]=f["row"]
                correlation_table[c_i]["dut_row"]=m["row"]
                correlation_table[c_i]["ref_col"]=f["column"]
                c_i=c_i+1
                fe_idx=fe_idx+f_i
                break
            # If the FE trigger_number is larger than the Monopix trigger_number, flag the Monopix trigger number to be filtered later
            # (i.e. There was not an event in the FE table that matched the Monopix one)
            elif (m["trigger_number"]-f["event_number"]) < 0:
                monopix_match_table[m_i]["trigger_number"]=mono_evBuilder.MAX_64BIT_TAG
                fe_idx=max(0,fe_idx+f_i-1)
                break
    return m_i+1, c_i

def calculate_phase_quality(fout, monopix_match_table):    
    """
    It calculates the quality of the 640 MHz phase of a Monopix hits
    (The smaller the quality, the more hits within a single bin, i.e. closer to the start of the 40 MHz clock)
    """
    # Segment the RX1 timestamp of the chip in 16 values ("phases")
    phase_ref=np.int64(monopix_match_table["rx1_timestamp"])&0xF
    # Initialize the best phase and ratio-between-bins counters
    best_phase=0
    ratio=0
    # Histogram the Time-walk (LE-RX1) 
    phase_hist=np.histogram( np.int64( monopix_match_table['le_timestamp']-monopix_match_table['rx1_timestamp'])
                        ,bins=np.arange(-0x10000,0x10000,0x1))
    # Find the rising edge of the largest peak
    tw_mainpeak=np.argwhere(phase_hist[0]> (phase_hist[0][np.argmax(phase_hist[0])])/2 )
    # Pass the rising edge of the largest peak as offset
    tw_offset_ns=phase_hist[1][tw_mainpeak[0]]
    #print (tw_offset_ns)
    #plt.step(phase_hist[1][:-1], phase_hist[0])
    #plt.yscale("log")
    phase_fraction=[]
    phase_id=np.arange(0,16)
    # Goes through all the phases until it finds the phase where most of the hits are within one bin 
    # (compared to the sum of hits in that bin, and the ones before and after)
    for ph in np.arange(0,16):
        #print (ph)
        curr_phase_data=monopix_match_table[phase_ref==ph]
        #fig, ax1 = plt.subplots()
        phase_hist=np.histogram( np.int64( curr_phase_data['le_timestamp']-curr_phase_data['rx1_timestamp'])
                            ,bins=np.arange(-0x10000,0x10000,0x1))
        #plt.step(phase_hist[1][:-1], phase_hist[0])
        #plt.yscale("log")
        window=[tw_offset_ns-32,tw_offset_ns+32]
        max_i=np.argmax(phase_hist[0])
        #print max_i
        max1, max2, max3= phase_hist[0][max_i], phase_hist[0][max_i-16], phase_hist[0][max_i+16]
        #print (max1, max2, max3)
        rat= float(max1)/float(max1+max2+max3)
        phase_fraction.append(rat)
        #print (rat, ratio)
        if rat>=ratio:
            best_phase=ph
            ratio=rat
        #ax1.set_xlim(window[0],window[1])
        #ax1.set_xlabel("Time [ns]")
        #ax1.set_title("Phase %s"%str(ph))
    print ("Best phase value: %s"%str(best_phase))
    #print phase_id
    #print phase_fraction

    # Generate a list that classifies the phase values according to their fraction (0: Best, 15: Worse) 
    phase_quality=[x for y, x in sorted(zip(phase_fraction, phase_id), reverse=True)]

    # The list has to be casted into a numba-valid typed-list in order to be able to use it as parameter for other jitted functions
    phase_quality=List(phase_quality)
    #phase_quality=np.asarray(phase_quality)

    return phase_quality, phase_fraction

@njit
def calculate_phase_in_FE(ref_valid_table,monopix_phase_quality):
    """
    This function calculates the phase in the Front-End and assigns to "TDC_trigger_distance" the corresponding quality index
    """
    for f_i,f in enumerate(ref_valid_table):
        # Calculate phase in the FE
        ref_valid_table[f_i]["TDC_time_stamp"]=np.int64(ref_valid_table[f_i]["TDC"])&0xF
        # Assign the corresponding phase quality
        ref_valid_table[f_i]["TDC_trigger_distance"]=monopix_phase_quality.index(np.int64(ref_valid_table[f_i]["TDC"])&0xF)
    return f_i

@njit
def fill_event_table(event_table, monopix_match_table, monopix_phase_quality, pix_calibration):
    """
    This function fills an event table with Monopix hits matched to TLU words and available timestamps
    """
    for m_i,m in enumerate(monopix_match_table):
        event_table[m_i]["event_number"]=m["trigger_number"]
        event_table[m_i]["column"]=m["col"]+1
        event_table[m_i]["row"]=m["row"]+1
        if pix_calibration is not None:
            try:
                # TODO: Implement calibration with ToT
                event_table[m_i]["charge"]= calibrate_tot((m["te"]-m['le']) & 0x3F, pix_calibration, m['col'], m['row'])
                event_table[m_i]["tot"]= np.float32((m["te"]-m["le"]) & 0x3F)
            except:
                print ("A calibration file was given but does not have the proper format. ToT will be assigned to charge too.")
                event_table[m_i]["charge"]= np.float32((m["te"]-m["le"]) & 0x3F)
                event_table[m_i]["tot"]= np.float32((m["te"]-m["le"]) & 0x3F)
        else:
            event_table[m_i]["charge"]= np.float32((m["te"]-m["le"]) & 0x3F)
            event_table[m_i]["tot"]= np.float32((m["te"]-m["le"]) & 0x3F)
        event_table[m_i]["phase"]=np.int64(m["rx1_timestamp"])&0xF
        event_table[m_i]["phase_quality"]=monopix_phase_quality.index(np.int64(m["rx1_timestamp"])&0xF)
        event_table[m_i]["veto_flg"]=m["flg"]

def hist_and_fit_LEvsRXdistance(monopix_match_table, event_table, fout, add_safety_offset):
    """
    This function histograms and fits a box function to the distance between two input timestamps (LE and RX/Scintillator).
    It plots such distribution and the corresponding fit parameters. 
    The whole data set is shifted by an offset (safety_offset) and filtered to include only positive values (as required by Test-Beam Analysis)
    It returns the data within a valid selection range, parameters of the box fit and low and high limit of the selection range.
    """
    # Calculate the difference between TLU_HR and RX input, and histogram it
    diff=np.int64(monopix_match_table["le_timestamp"]-monopix_match_table["rx1_timestamp"])
    hist=np.histogram(diff, bins=np.arange(-0x10000,0x10000,0x1))
    x=hist[1][:-1]
    y=hist[0]

    print("Fitting a box function to LE-RX1 distribution...")
    boxfit_params=mono_utils.fit_boxfc(x, y)
    print ("Values found: Amp=%.2E, Mean=%.2E, Width=%.2f, Sigma_Box=%.2f"%(boxfit_params[0],boxfit_params[1],boxfit_params[2],boxfit_params[3]))

    width=boxfit_params[2]
    sigma=boxfit_params[3]

    diff_offset=boxfit_params[1]-np.abs(width)/2.0
    lower_lim=round(diff_offset-1*np.abs(width)-5*np.abs(sigma),0)
    upper_lim=round(diff_offset+10*np.abs(width)+5*np.abs(sigma),0)
    print("Rising edge of the main peak (TLU-RX1 offset @ 640MHz Clocks) located at %s"%str(diff_offset))


    frame=diff-diff_offset+add_safety_offset
    #frame[frame<0]=0
    #frame[frame>0xFFFFFFFF]=0xFFFFFFFF  
    event_table["frame"]=np.uint16(frame)
    #valid=np.argwhere(np.bitwise_and(frame!=0,frame!=0xFFFFFFFF))[:,0]
    #print ("# of data with valid frame",len(valid),100.0*len(valid)/len(frame))

    print ("Filtering LE_timestamp-RX1_timestamp by upper_lim of ",upper_lim," and lower_lim of",lower_lim)
    #diff_selection_mask=frame[np.bitwise_and(frame<=upper_lim+0x8000-diff_offset, frame>=lower_lim+0x8000-diff_offset)]
    diff_selection_mask=event_table[np.bitwise_and(frame<=upper_lim-diff_offset+add_safety_offset, frame>=lower_lim-diff_offset+add_safety_offset)]
    print ("# of Events: {0:d} / {1:d} ({2:.2f}% are discarded based on their LE-RX1 distance)".format(len(diff_selection_mask), len(monopix_match_table), 100.0-100.0*len(diff_selection_mask)/len(monopix_match_table)))

    return diff_selection_mask, hist, boxfit_params, diff_offset, lower_lim, upper_lim

