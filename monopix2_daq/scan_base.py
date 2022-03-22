import os,sys,time
import numpy as np
from numpy.core.defchararray import array
import bitarray
import tables as tb
import yaml
import basil
import logging
import zmq

from monopix2_daq import monopix2
from monopix2_daq.fifo_readout import FifoReadout
from contextlib import contextmanager
from monopix2_daq.analysis import analysis_utils as au

import online_monitor
from online_monitor.utils import utils as ou

PROJECT_FOLDER = os.path.dirname(__file__)
TESTBENCH_DEFAULT_FILE = os.path.join(PROJECT_FOLDER, 'testbench.yaml')


def send_data(socket, data, scan_par_id, index_start, index_stop, data_length, name='ReadoutData'):
    '''
    Sends the data of every read out (raw data and meta data) via ZeroMQ to a specified socket.
    Uses a serialization provided by the online_monitor package
    '''
    data_meta_data = dict(
        index_start=index_start,
        index_stop=index_stop,
        data_length=data_length,
        timestamp_start=data[1],
        timestamp_stop=data[2],
        scan_par_id=scan_par_id,
        error=data[3]
    )

    try:
        data_ser = ou.simple_enc(data[0], meta=data_meta_data)
        socket.send(data_ser, flags=zmq.NOBLOCK)
    except zmq.Again:
        pass

class MetaTable(tb.IsDescription):
    index_start = tb.UInt32Col(pos=0)
    index_stop = tb.UInt32Col(pos=1)
    data_length = tb.UInt32Col(pos=2)
    timestamp_start = tb.Float64Col(pos=3)
    timestamp_stop = tb.Float64Col(pos=4)
    scan_param_id = tb.UInt16Col(pos=5)
    error = tb.UInt32Col(pos=6)

class ScanBase(object):
    """
    A class that represents the fundamentals of any scan in LF-Monopix2
    """

    def __init__(self, monopix=None, no_power_reset=True, **_):
        """
        Initialization of the scan.

        Parameters
        ----------
        monopix: string OR Monopix2 
            string: It should be the full path to the chip's yaml file used for configuration. 
                If this type or argument is given, the initialization will use the "no_power_reset" argument in this scan class.
            Monopix2: A Monopix2 instantiation. 
                If this type or argument is given, the initialization will use the "no_power_reset" argument in the Monopix2 class.
        fout: string or None
            A path to the working directory where the output of the scan should be placed.
        no_power_reset: boolean
            This conditional will enable or disable the power cycling of the GPAC, IF the "monopix" argument is "None" or a "yaml" file.  
            (If no_power_reset=True: The GPAC will NOT power cycle when the chip is initialized ---> Default for chip safety when high voltage is applied.)
        """

        # # Initialize MIO3 board
        self.monopix=monopix2.Monopix2(conf=monopix, no_power_reset=no_power_reset)
        self.monopix.init()

        self.configuration = self._load_testbench_cfg(bench_config=None)

        # Initialize chip configuration
        self._init_chip_config(**_)

        # Set working directory and file name
        if self.configuration['bench']['general']['output_directory'] is not None:
            self.working_dir = os.path.realpath(self.configuration['bench']['general']['output_directory'])
            self.run_name = time.strftime("%Y%m%d_%H%M%S_") + self.scan_id
        else:
            self.working_dir = os.path.join(os.getcwd(),"output_data")
            self.run_name = time.strftime("%Y%m%d_%H%M%S_") + self.scan_id
        if not os.path.exists(self.working_dir):
            os.makedirs(self.working_dir)
        self.output_filename = os.path.join(self.working_dir, self.run_name)
        
        # Initialize logger
        self.logger = logging.getLogger()
        for l in self.logger.handlers:
            if isinstance(l, logging.FileHandler):
               dut_logger_filename=l.baseFilename
               self.logger.removeHandler(l)
        logFormatter = logging.Formatter("%(asctime)s [%(levelname)-5.5s] [%(threadName)-10s] [%(filename)-15s] [%(funcName)-15s] %(message)s")
        fileHandler = logging.FileHandler(self.output_filename + '.log')
        fileHandler.setFormatter(logFormatter)
        self.logger.addHandler(fileHandler)
        open(fileHandler.baseFilename, "w").writelines([l for l in open(dut_logger_filename).readlines()])
        self.logger.info('Initializing %s', self.__class__.__name__)
        self.logger.info("Scan start time: "+time.strftime("%Y-%m-%d_%H:%M:%S"))
        self.scan_start_time=time.localtime()

        # Assign the socket where the data will be sent (For online monitoring)
        self.socket = self.configuration['bench']['module']['chip']['send_data']
        self.context = zmq.Context.instance()
            
        # Define filters for table output data
        self.filter_raw_data = tb.Filters(complib='blosc', complevel=5, fletcher32=False)
        self.filter_tables = tb.Filters(complib='zlib', complevel=5, fletcher32=False)
        
    def get_basil_dir(self):
        """
        Returns the path to the basil currently used by the scan.

        Returns
        ----------
        basil_dir: string 
            A string with the path to the basil currently used by the scan.
        """
        basil_dir = str(os.path.dirname(os.path.dirname(basil.__file__)))
        return basil_dir

    def start(self, **kwargs):
        """
        Initialization of the scan.
        
        Returns
        ----------
        out_fname: string 
            A string with the output file name.
        """
        self._first_read = False
        self.scan_param_id = 0
        
        # Create the table file for output.
        filename = self.output_filename +'.h5'
        self.h5_file = tb.open_file(filename, mode='w', title=self.scan_id)
        self.raw_data_earray = self.h5_file.create_earray (self.h5_file.root, name='raw_data', atom=tb.UIntAtom(), shape=(0,), title='raw_data', filters=self.filter_raw_data)
        self.meta_data_table = self.h5_file.create_table(self.h5_file.root, name='meta_data', description=MetaTable, title='meta_data', filters=self.filter_tables)
        self.kwargs = self.h5_file.create_vlarray(self.h5_file.root, 'kwargs', tb.VLStringAtom(), 'kwargs', filters=self.filter_tables)

        # Save args and chip configurations.
        self.kwargs.append(yaml.dump(kwargs))
        self.meta_data_table.attrs.scan_id = self.scan_id
        self.meta_data_table.attrs.chip_props = yaml.dump(self.monopix.chip_props)
        self.meta_data_table.attrs.power_status_before = yaml.dump(self.monopix.power_status())
        self.meta_data_table.attrs.dac_status_before = yaml.dump(self.monopix.dac_status())
        self.pixel_masks_before=self.h5_file.create_group(self.h5_file.root, 'pixel_conf_before', 'Pixel configuration before the scan')
        for name, value in self.monopix.PIXEL_CONF.items():
            self.h5_file.create_carray(self.pixel_masks_before, name=name, title=name, obj=value, filters=self.filter_raw_data)
        self.meta_data_table.attrs.firmware_before = yaml.dump(self.monopix.get_configuration())
        
        # Open socket for the online monitor.
        if (self.socket==""): 
            self.socket=None
        else:
            try:
                socket_addr = self.socket
                self.socket = self.context.socket(zmq.PUB) # publisher socket
                self.socket.setsockopt(zmq.LINGER, 0)
                self.socket.bind(socket_addr)
                # self.log.debug('Sending data to server %s', socket_addr)
            except zmq.error.ZMQError:
                self.logger.warn('ScanBase.start:sender.init failed addr=%s'%self.socket)
                self.socket=None
        
        # Execute scan
        self.fifo_readout = FifoReadout(self.monopix)
        self.logger.info('Power Status: %s', str(self.monopix.power_status()))
        self.logger.info('DAC Status: %s', str(self.monopix.dac_status()))
        self.monopix.show("none")
        self.scan(**kwargs) 
        self.fifo_readout.print_readout_status()
        self.monopix.show("none")
        self.logger.info('Power Status: %s', str(self.monopix.power_status()))
        self.logger.info('DAC Status: %s', str(self.monopix.dac_status()))
        
        # Save chip configurations
        self.meta_data_table.attrs.power_status = yaml.dump(self.monopix.power_status())
        self.meta_data_table.attrs.dac_status = yaml.dump(self.monopix.dac_status())
        self.pixel_masks=self.h5_file.create_group(self.h5_file.root, 'pixel_conf', 'Pixel configuration at the end of the scan')
        for name, value in self.monopix.PIXEL_CONF.items():
            self.h5_file.create_carray(self.pixel_masks, name=name, title=name, obj=value, filters=self.filter_raw_data)
        self.meta_data_table.attrs.firmware = yaml.dump(self.monopix.get_configuration())

        # Close file
        self.h5_file.close()
        self.logger.info("Scan end time: "+time.strftime("%Y-%m-%d_%H:%M:%S"))
        self.scan_end_time=time.localtime()
        self.scan_total_time=time.mktime(self.scan_end_time) - time.mktime(self.scan_start_time)
        self.logger.info("Total scan time: %i seconds", self.scan_total_time)
        self.logger.info('Data Output Filename: %s', filename)

        # Close socket
        if self.socket!=None:
           try:
               online_monitor.sender.close(self.socket)
           except:
               pass

        return filename

    def analyze(self):
        raise NotImplementedError('ScanBase.analyze() not implemented')

    def scan(self, **kwargs):
        raise NotImplementedError('ScanBase.scan() not implemented')
        
    def plot(self, **kwargs):
        raise NotImplementedError('ScanBase.plot() not implemented')

    @contextmanager
    def readout(self, *args, **kwargs):
        """
        Instantiation of the readout.
        """
        timeout = kwargs.pop('timeout', 10.0)
        self.fifo_readout.readout_interval=kwargs.pop('readout_interval', 0.003)
        if not self._first_read:
            time.sleep(0.1)
            self.fifo_readout.print_readout_status()
            self._first_read = True
            
        self.start_readout(*args, **kwargs)
        yield
        self.fifo_readout.stop(timeout=timeout)

    def start_readout(self, scan_param_id = 0, *args, **kwargs):
        """
        Initialization of the readout, with a particular scan parameter ID and arguments for the readout.

        Parameters
        ----------
        scan_param_id: int
            An integer to be associated with a particular parameter within the scan.
        kwargs:
            Parameters for the readout.
        """
        # Pop parameters for fifo_readout.start
        callback = kwargs.pop('callback', self.handle_data)
        clear_buffer = kwargs.pop('clear_buffer', False)
        fill_buffer = kwargs.pop('fill_buffer', False)
        reset_sram_fifo = kwargs.pop('reset_sram_fifo', False)
        errback = kwargs.pop('errback', self.handle_err)
        no_data_timeout = kwargs.pop('no_data_timeout', None)
        self.scan_param_id = scan_param_id
        self.fifo_readout.start(reset_sram_fifo=reset_sram_fifo, fill_buffer=fill_buffer, clear_buffer=clear_buffer, 
                                callback=callback, errback=errback, no_data_timeout=no_data_timeout)

    def handle_data(self, data_tuple):
        '''
        Data handling.
        '''
        total_words = self.raw_data_earray.nrows
        
        self.raw_data_earray.append(data_tuple[0])
        self.raw_data_earray.flush()
        
        len_raw_data = data_tuple[0].shape[0]
        self.meta_data_table.row['timestamp_start'] = data_tuple[1]
        self.meta_data_table.row['timestamp_stop'] = data_tuple[2]
        self.meta_data_table.row['error'] = data_tuple[3]
        self.meta_data_table.row['data_length'] = len_raw_data
        self.meta_data_table.row['index_start'] = total_words
        temp_index=total_words
        total_words += len_raw_data
        self.meta_data_table.row['index_stop'] = total_words
        self.meta_data_table.row['scan_param_id'] = self.scan_param_id
        self.meta_data_table.row.append()
        self.meta_data_table.flush()
        
        if self.socket:
            send_data(self.socket, data=data_tuple, scan_par_id=self.scan_param_id,index_start=temp_index, index_stop=total_words, data_length=len_raw_data)

    def handle_err(self, exc):
        '''
        Readout error handling.
        '''
        msg='%s' % exc[1]
        if msg:
            self.logger.error('%s%s Aborting run...', msg, msg[-1] )
        else:
            self.logger.error('Aborting run...')

    def _load_testbench_cfg(self, bench_config):
        ''' Load the bench config into the scan

            Parameters:
            ----------
            bench_config : str or dict
                    Testbench configuration (configuration as dict or its filename as string)
        '''
        conf = au.ConfigDict()
        try:
            if bench_config is None:
                bench_config = TESTBENCH_DEFAULT_FILE
            with open(bench_config) as f:
                conf['bench'] = yaml.full_load(f)
        except TypeError:
            conf['bench'] = bench_config

        return conf

    def _init_chip_config(self, config_file=None, th1=None, th2=None, th3=None, flavor=None, **_):
        ''' Initialize and configure chip, parameters given (mostly) as parser arguments
        '''
        if config_file is not None:
            self.monopix.load_config(config_file)
        elif self.configuration['bench']['module']['chip']['chip_config'] is not None:
            self.monopix.load_config(self.configuration['bench']['module']['chip']['chip_config'])

        self.monopix.set_inj_en(pix="none")

        if th1 is not None:
            self.monopix.set_th(1, th1)
        if th2 is not None:
            self.monopix.set_th(2, th2)
        if th3 is not None:
            self.monopix.set_th(3, th3)

        if flavor is not None:
            if flavor=="all":
                collist=range(0, self.monopix.chip_props["COL_SIZE"])
                self.monopix.logger.info("Enabled: Full matrix")
            else:
                tmp=flavor.split(":")
                collist=range(int(tmp[0]), int(tmp[1]))
                self.monopix.logger.info("Enabled: Columns {0:s} to {1:s}".format(tmp[0], tmp[1]))

            self.pix=[]
            for i in collist:
                for j in range(0, self.monopix.chip_props["ROW_SIZE"]):
                    self.pix.append([i,j])
        else:
            self.pix=[]
            self.monopix.set_preamp_en(self.monopix.PIXEL_CONF["EnPre"])
            self.monopix.set_tdac(self.monopix.PIXEL_CONF["Trim"], overwrite=True)
            
            for i in range(0, self.monopix.chip_props["COL_SIZE"]):
                for j in range(0, self.monopix.chip_props["ROW_SIZE"]):
                    if self.monopix.PIXEL_CONF["EnPre"][i,j]!=0:
                        self.pix.append([i,j])
                    else:
                        pass

    def close(self):
        '''
        Stop readout of the chip.
        '''
        try:
            self.fifo_readout.stop(timeout=0)
        except RuntimeError:
            self.logger.info("Fifo has been already closed")
        self._close_sockets()

    def _close_sockets(self):
        if self.context:
            try:
                if self.socket:
                    # self.log.debug('Closing socket connection')
                    self.socket.close()
                    self.socket = None
            except AttributeError:
                pass
        self.context.term()
        self.context = None
