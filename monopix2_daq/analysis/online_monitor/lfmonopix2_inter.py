import numpy as np
from numba import njit

from online_monitor.converter.transceiver import Transceiver
from online_monitor.utils import utils

from monopix2_daq.analysis.interpreter import RawDataInterpreter
from monopix2_daq.analysis import analysis_utils as au

# copied from interpreter.py
hit_dtype = [
    ('col', 'u1'),
    ('row', '<u2'),
    ('le', 'u1'),
    ('te', 'u1'),
    ('cnt', '<u4'),
    ('timestamp', '<i8'),
    ('scan_param_id', '<i4'),
]


#@njit(cache=True)
def hist_occupancy(occ, tot, hits):
    for hit_i in range(hits.shape[0]):
        if hits[hit_i]["col"] < occ.shape[0] and hits[hit_i]["row"] < occ.shape[1]:
            occ[hits[hit_i]["col"], hits[hit_i]["row"]] += 1
            tot[hits[hit_i]["col"], hits[hit_i]["row"], (hits[hit_i]["te"] - hits[hit_i]["le"]) & 0x3F] += 1

        # if pix[0] == 0xFFFF and pix[1] == 0xFFFF:
        #     tot[hits[hit_i]["tot"]] += 1
        # if pix[0] == hits[hit_i]["col"] and pix[1] == hits[hit_i]["row"]:
            # tot[hits[hit_i]["tot"]] += 1


class LFMonopix2(Transceiver):

    def setup_transceiver(self):
        ''' Called at the beginning

            We want to be able to change the histogrammmer settings
            thus bidirectional communication needed
        '''
        self.set_bidirectional_communication()

    def setup_interpretation(self):
        ''' Objects defined here are available in interpretation process '''
        utils.setup_logging(self.loglevel)

        # self.chunk_size = self.config.get('chunk_size', 1000000)
        self.chunk_size = 200000
        # self.analyze_tdc = self.config.get('analyze_tdc', False)
        # self.rx_id = int(self.config.get('rx', 'rx0')[2])
        # Mask pixels that have a higher occupancy than 3 * the median of all firering pixels
        self.noisy_threshold = self.config.get('noisy_threshold', 3)

        self.mask_noisy_pixel = False
        self.pix_col = None
        self.pix_row = None

        # Init result hists
        self.reset_hists()

        # Number of readouts to integrate
        self.int_readouts = 0

        # Variables for meta data time calculations
        self.ts_last_readout = 0.  # Time stamp last readout
        self.hits_last_readout = 0.  # Number of hits
        self.fps = 0.  # Readouts per second
        self.hps = 0.  # Hits per second
        # self.trigger_id = -1  # Last chunk trigger id
        # self.ext_trg_num = -1  # external trigger number
        self.last_rawdata = None  # Leftover from last chunk

        self.interpreter = RawDataInterpreter()

    def deserialize_data(self, data):
        ''' Inverse of LF-Monopix2 serialization '''
        return utils.simple_dec(data)

    def _add_to_meta_data(self, meta_data):
        ''' Meta data interpratation is deducing timings '''

        ts_now = float(meta_data['timestamp_stop'])

        # Calculate readout per second with smoothing
        if ts_now != self.ts_last_readout:
            recent_fps = 1.0 / (ts_now - self.ts_last_readout)
            self.fps = self.fps * 0.95 + recent_fps * 0.05

            # Calulate hits per second with smoothing
            recent_hps = self.hits_last_readout * recent_fps
            self.hps = self.hps * 0.95 + recent_hps * 0.05

        self.ts_last_readout = ts_now

        # Add info to meta data
        meta_data.update(
            {'fps': self.fps,
             'hps': self.hps,
             'total_hits': self.total_hits})
        return meta_data
    
    def interpret_data(self, data):
        ''' Called for every chunk received '''
        raw_data, meta_data = data[0][1]
        meta_data = self._add_to_meta_data(meta_data)

        # hit_buffer = np.zeros(4 * len(raw_data), dtype=au.hit_dtype)
        hit_buffer = np.zeros(shape=self.chunk_size, dtype=hit_dtype)
        hits = self.interpreter.interpret(raw_data, None, hit_buffer) # No meta_data needed for online_monitor

        self.hits_last_readout = len(hits)
        self.total_hits += len(hits)
        self.readout += 1

        hist_occupancy(self.hist_occ, self.hist_tot, hits)
        occupancy_hist = self.hist_occ[:, :]
        # Mask Noisy pixels
        if self.mask_noisy_pixel:
            sel = occupancy_hist > self.noisy_threshold * np.median(occupancy_hist[occupancy_hist > 0])
            occupancy_hist[sel] = 0

        # Select individual pixel for ToT plotting
        if self.pix_col == None or self.pix_row == None:
            tot_hist = self.hist_tot.sum(axis=(0, 1))
        else:
            tot_hist = self.hist_tot[int(self.pix_col), int(self.pix_row), :]

        interpreted_data = {
            'meta_data': meta_data,
            'occupancy': occupancy_hist,
            'tot_hist': tot_hist, # self.hist_tot.sum(axis=(0, 1)),
        }

        if self.int_readouts != 0:  # = 0 for infinite integration
            if self.readout % self.int_readouts == 0:
                self.reset_hists()

        return [interpreted_data]

    def serialize_data(self, data):
        ''' Serialize data from interpretation '''
        return utils.simple_enc(None, data)

    def handle_command(self, command):
        ''' Received commands from GUI receiver '''
        if command[0] == 'RESET':
            self.reset_hists()
            self.last_event = -1
            self.trigger_id = -1
        elif 'MASK' in command[0]:
            if '0' in command[0]:
                self.mask_noisy_pixel = False
            else:
                self.mask_noisy_pixel = True
        elif 'COL' in command[0]:
            if '-1' in command[0]:
                self.pix_col = None
            else:
                self.pix_col = command[0][4:]
        elif 'ROW' in command[0]:
            if '-1' in command[0]:
                self.pix_row = None
            else:
                self.pix_row = command[0][4:]
        else:
            self.int_readouts = int(command[0])

    def reset_hists(self):
        ''' Reset the histograms '''
        self.total_hits = 0
        # Readout number
        self.readout = 0

        self.hist_tot = np.zeros((56, 340, 64), dtype=np.int64)
        self.hist_occ = np.zeros((56, 340), dtype=np.int64)
