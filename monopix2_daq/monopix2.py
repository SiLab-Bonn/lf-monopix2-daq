import sys
import time
import os
import numpy as np
import logging
import warnings
import yaml
import bitarray
import tables
import yaml
import socket

sys.path = [os.path.dirname(os.path.abspath(__file__))] + sys.path 
OUTPUT_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "output_data")

from basil.dut import Dut
import basil.RL.StdRegister

def mk_fname(ext="data.npy",dirname=None):
    if dirname == None:
        prefix = ext.split(".")[0]
        dirname = os.path.join(OUTPUT_DIR, prefix)
    if not os.path.exists(dirname):
        os.system("mkdir -p {0:s}".format(dirname))
    return os.path.join(dirname, time.strftime("%Y%m%d_%H%M%S0_")+ext)


class Monopix2(Dut):

    default_yaml = os.path.dirname(os.path.abspath(__file__)) + os.sep + "monopix2.yaml"

    def __init__(self, conf=None, no_power_reset=True):
        ## set logger
        self.logger = logging.getLogger()
        logFormatter = logging.Formatter("%(asctime)s [%(levelname)-5.5s] (%(threadName)-10s) %(message)s")
        fname = mk_fname(ext="log.log")
        fileHandler = logging.FileHandler(fname)
        fileHandler.setFormatter(logFormatter) 
        self.logger.addHandler(fileHandler)

        self.COL = 56  ##TODO this will be used in scans... maybe not here
        self.ROW = 340

        if conf is None:
            conf = self.default_yaml

        if isinstance(conf, str):
            with open(conf) as f:
                conf = yaml.load(f)
            for i, e in enumerate(conf["hw_drivers"]):
                if e["type"]=="GPAC":
                    conf["hw_drivers"][i]["init"]["no_power_reset"] = no_power_reset
                    break
        super(Monopix2, self).__init__(conf)

        self.PIXEL_CONF = {'EnPre': np.full([self.COL,self.ROW], False, dtype = np.bool),
                       'EnInj'   : np.full([self.COL,self.ROW], False, dtype = np.bool),
                       'EnMonitor'   : np.full([self.COL,self.ROW], False, dtype = np.bool),
                       'Trim'  : np.full([self.COL,self.ROW], 0, dtype = np.uint8),
                       }
        self.SET = {}

    def init(self):
        super(Monopix2, self).init()
        fw_version = self.get_fw_version()
        logging.info("Firmware version: {0}".format(fw_version))
        self['CONF_SR'].set_size(self["CONF_SR"]._conf['size'])
        self['CONF']['Def_Conf'] = 1 
        self['CONF'].write()
        self.power_on()
        self._write_global_conf()
        mask=self._cal_mask("all")
        self._write_pixel_mask("EnPre", mask, over_write=True)
        mask[20,20]=1
        self._write_pixel_mask("EnInj", mask, over_write=True)
        self._write_pixel_mask("EnMonitor", mask, over_write=True)

    def get_fw_version(self):
        return self['intf'].read(0x10000, 1)[0]

    def power_on(self):
        pass

    def set_inj_all(self, inj_high=0.6, inj_low=0.2,
                    inj_n=100, inj_width=5000, inj_delay=5000, inj_phase=-1,
                    delay=700, ext=False):

        self["inj"].reset()
        self["inj"]["REPEAT"] = inj_n
        self["inj"]["DELAY"] = inj_delay
        self["inj"]["WIDTH"] = inj_width
        if inj_phase < 0:
            inj_phase_des = -1
        else:
            self["inj"].set_phase(int(inj_phase))
            inj_phase_des = self["inj"]["PHASE_DES"]
            if self["inj"].get_phase() != inj_phase:
                self.logger.error("inj:set_inj_phase={0:d} PHASE_DES={1:x}".format(inj_phase, self["inj"]["PHASE_DES"]))
        self["inj"]["EN"] = ext
        
        self.logger.info("inj:{0:.4f},{1:.4f} inj_width:{2:d} inj_delay:{3:d} inj_phase:{4:d},{5:x} inj_n:{6:d} delay:{7:d} ext:{8:d}".format(
            inj_high, inj_low, inj_width, inj_delay, inj_phase, inj_phase_des, inj_n, delay, int(ext)))

    def start_inj(self, inj_low=None, wait=False):
        self.logger.info("start_inj:{0:.4f},{1:.4f}".format(self["SR_CONF"]["VH"], self["SR_CONF"]["VH"]))
        self["inj"].start()
        while self["inj"].is_done() != 1 and wait:
            time.sleep(0.001)

# ###########################################     
# ### Configure the Shift Register
    def _write_global_conf(self):
        self['CONF']['En_Cnfg_Pix'] = 0
        self['CONF'].write()
        self['CONF_SR'].write() 
        while not self['CONF_SR'].is_ready:
            time.sleep(0.001)
        self['CONF']['Def_Conf'] = 0
        self['CONF'].write()

    def set_global(self,**kwarg):
        """ kwarg must be like
         BLRes=32, VAmp1=32, VPFB=32, VPFoll=12, VPLoad=11, Vfs=32, TDAC_LSB=32
        """
        for k in kwarg.keys():
            self["CONF_SR"][k] = kwarg[k]
        self._write_global_conf()
        s="set_global:"
        for k in kwarg.keys():
            s=s+"{0}={1:d}".format(k,kwarg[k])
        self.logger.info(s)

    def _write_pixel_mask(self, bit, mask, ro_off=False, over_write=False):
        if ro_off:
            # Readout off
            ClkBX = self['CONF']['ClkBX'].tovalue()
            ClkOut = self['CONF']['ClkOut'].tovalue()
            self['CONF']['ClkOut'] = 0
            self['CONF']['ClkBX'] = 0
        self['CONF_SR']["{0:s}Ld".format(bit)] = 0  # active low
        if over_write:
            defval = np.all(mask)
            self['CONF_DC'].setall(defval)
            self['CONF_SR']['EnSRDCol'].setall(True)
            self['CONF']['En_Cnfg_Pix'] = 0
            self['CONF'].write()
            self['CONF_SR'].write()
            while not self['CONF_SR'].is_ready:
                time.sleep(0.001)
            self['CONF']['En_Cnfg_Pix'] = 1
            self['CONF'].write()
            self['CONF_DC'].write()
            while not self['CONF_DC'].is_ready:
                time.sleep(0.001)
            self['CONF']['En_Cnfg_Pix'] = 0
            arg = np.argwhere(mask == defval)
        else:
            arg = np.argwhere(self.PIXEL_CONF[bit] != mask)
        uni = np.unique(arg[:, 0]//2)
        #print("=====sim=====uni",uni)
        # set individual double col
        for dcol in uni:
            self['CONF_SR']['EnSRDCol'].setall(False)
            #print("=====sim=====dcol", type(dcol), dcol, type(self['CONF_SR']['EnSRDCol'][0]))
            self['CONF_SR']['EnSRDCol'][dcol] = '1'
            self['CONF']['En_Cnfg_Pix'] = 0
            self['CONF'].write()
            self['CONF_SR'].write()
            while not self['CONF_SR'].is_ready:
                time.sleep(0.001)
            # set pix_config
            self['CONF_DC']['Col0'] = bitarray.bitarray(list(mask[dcol*2+1, :]))
            self['CONF_DC']['Col1'] = bitarray.bitarray(list(mask[dcol*2, ::-1]))
            self['CONF']['En_Cnfg_Pix'] = 1
            self['CONF'].write()
            self['CONF_DC'].write()
            while not self['CONF_DC'].is_ready:
                time.sleep(0.001)
            self['CONF']['En_Cnfg_Pix'] = 0
        self['CONF_SR']["{0:s}Ld".format(bit)] = 1
        if ro_off:
            self['CONF']['ClkOut'] = ClkOut  # Readout OFF
            self['CONF']['ClkBX'] = ClkBX
        self['CONF'].write()
        self.PIXEL_CONF[bit] = mask

    def _cal_mask(self, pix):
        mask = np.zeros([self.COL, self.ROW])
        if isinstance(pix, str):
            if pix == "all":
                mask.fill(1)
            elif pix == "none":
                pass
        elif isinstance(pix[0], int):
            mask[pix[0], pix[1]] = 1
        elif len(pix) == self.COL and len(pix[0]) == self.ROW:
            mask[:, :] = np.array(pix, np.bool)
        else:
            for p in pix:
                mask[p[0], p[1]] = 1
        return mask

    def set_preamp_en(self, pix="all", EnColRO="auto", Out='autoCMOS'):
        mask = self._cal_mask(pix)
        if EnColRO == "auto":
            self['CONF_SR']['EnColRO'].setall(False)
            for i in range(self.COL):
                self['CONF_SR']['EnColRO'][i] = bool(np.any(mask[i,:]))
        elif EnColRO == "all":
            self['CONF_SR']['EnColRO'].setall(True)
        elif EnColRO == "none":
            self['CONF_SR']['EnColRO'].setall(False)
        elif ":" in EnColRO:
            cols = np.zeros(self.COL, int)
            tmp = EnColRO.split(":")
            cols[int(tmp[0]):int(tmp[1])] = 1
            for i in range(self.COL):
                self['CONF_SR']['EnColRO'][i] = bool(cols[i])
        elif len(EnColRO) == self.COL:
            self['CONF_SR']['EnColRO'] = EnColRO
        else:
            pass  # if "keep" then keep the value

        self['CONF_SR']['EnDataCMOS'] = 0
        self['CONF_SR']['EnDataLVDS'] = 0
        if 'CMOS' in Out:
            if ('auto' in Out) and self['CONF_SR']['EnColRO'].any():
                self['CONF_SR']['EnDataCMOS'] = 1
            elif ('auto' not in Out):
                self['CONF_SR']['EnDataCMOS'] = 1
        if 'LVDS' in Out:
            if ('auto' in Out) and self['CONF_SR']['EnColRO'].any():
                self['CONF_SR']['EnDataLVDS'] = 1
            elif ('auto' not in Out):
                self['CONF_SR']['EnDataLVDS'] = 1

        self._write_pixel_mask("EnPre", mask)

    def set_mon_en(self, pix="none"):
        mask = self._cal_mask(pix)
        self['CONF_SR']['EnMonitorCol'].setall(False)
        for i in range(self.COL):
            self['CONF_SR']['EnMonitorCol'][i] = bool(np.any(mask[i,:]))
        self._write_pixel_mask("EnMonitor", mask)
      
        arg = np.argwhere(self.PIXEL_CONF["EnMonitor"][:, :])
        self.logger.info("set_mon_en pix: {0:d} {1:s}".format(len(arg), str(arg).replace("\n", " ")))

    def set_inj_en(self, pix="none"):
        mask = self._cal_mask(pix)
        self['CONF_SR']['InjEnCol'].setall(False)
        for i in range(self.COL):
            self['CONF_SR']['InjEnCol'][i] = bool(np.any(mask[i, :]))
        self._write_pixel_mask("EnInj", mask)
        
        arg = np.argwhere(self.PIXEL_CONF["EnInj"][:,:])
        self.logger.info("set_inj_en pix: {0:d} {1:s}".format(len(arg), str(arg).replace("\n", " ")))
        
    def set_tdac(self, tdac):
        mask = np.copy(self.PIXEL_CONF["Trim"])
        if isinstance(tdac, int):
            mask.fill(tdac)
            self.logger.info("set_tdac all: {0:d}".format(tdac))
        elif np.shape(tdac) == np.shape(mask):
            self.logger.info("set_tdac: matrix")
            mask = np.array(tdac, dtype=np.uint8)
        else:
            self.logger.info("ERROR: wrong instance. tdac must be int or [{0:d},{1:d}]".format(self.COL, self.ROW))
            return 

        trim_bits = np.unpackbits(mask)
        trim_bits_array = np.reshape(trim_bits, (self.COL, self.ROW, 8)).astype(np.bool)
        for bit in range(4):
            trim_bits_sel_mask = trim_bits_array[:, :, 7-bit]
            self._write_pixel_mask('TrimLd{0:d}'.format(bit), trim_bits_sel_mask)

    def get_conf_sr(self, mode='mwr'):
        """ mode:'w' get values in FPGA write register (output to SI_CONF)
                 'r' get values in FPGA read register (input from SO_CONF)
                 'm' get values in cpu memory (data in self['CONF_SR'])
                 'mrw' get all
        """
        size = self['CONF_SR'].get_size()
        r = size % 8
        hw = self["CONF_SR"]._conf['hw_driver']
        byte_size = self[hw]._mem_bytes
        data = {"size":size}
        if "w" in mode:
            w = bitarray.bitarray(endian='big')
            w.frombytes(self["CONF_SR"].get_data(size=byte_size, addr=0).tostring())
            data["write_reg"] = basil.RL.StdRegister.StdRegister(None, self["CONF_SR"]._conf)
            data["write_reg"][:] = w[size-1::-1]
        if "r" in mode:
            r = bitarray.bitarray(endian='big')
            r.frombytes(self["CONF_SR"].get_data(size=byte_size).tostring())
            data["write_reg"] = basil.RL.StdRegister.StdRegister(None, self["CONF_SR"]._conf)
            data["read_reg"][:] = r[size-1::-1]
        if "m" in mode:
           data["memory"] = basil.RL.StdRegister.StdRegister(None, self["CONF_SR"]._conf)
           data["memory"][:] = self["CONF_SR"][:].copy()
        return data

# ###########################################        
# ### Get data from FIFO
    def get_data_now(self):
        return self['fifo'].get_data()

    def get_data(self, wait=0.2):
        self["inj"].start()
        i = 0
        raw = np.empty(0,dtype='uint32')
        while self["inj"].is_done() != 1:
            time.sleep(0.001)
            raw = np.append(raw, self['fifo'].get_data())
            i = i+1
            if i > 10000:
                break
        time.sleep(wait)
        raw = np.append(raw, self['fifo'].get_data())
        if i > 10000:
            self.logger.info("get_data: error timeout len={0:d}".format(len(raw)))
        lost_cnt = self["data_rx"]["LOST_COUNT"]
        if self["data_rx"]["LOST_COUNT"]!=0:
            self.logger.warn("get_data: error cnt={0:d}".format(lost_cnt))      
        return raw

    def reset_monoread(self, wait=0.001, sync_timestamp=True, bcid_only=True):
        self['CONF']['ResetBcid_WITH_TIMESTAMP'] = sync_timestamp
        if bcid_only:
            self['CONF']['Rst'] = 0
        else:
            self['CONF']['Rst'] = 1
        self['CONF']['ResetBcid'] = 1
        self['CONF'].write()
        if not bcid_only:
            time.sleep(wait)
            self['CONF']['Rst'] = 0
            self['CONF'].write()
        time.sleep(wait)

        self['intf'].read_str(0x10010+1, size=2)
        self['intf'].read_str(0x10010+1, size=2)
        self['intf'].read_str(0x10010+1, size=2)
        self['CONF']['ResetBcid'] = 0
        self['CONF'].write()
        self['intf'].read_str(0x10010+1, size=2)
        self['intf'].read_str(0x10010+1, size=2)
        self['intf'].read_str(0x10010+1, size=2)

    def set_monoread(self, start_freeze=90, start_read=90+2, stop_read=90+2+2,
                     stop_freeze=90+37, stop=90+37+10,
                     sync_timestamp=True, read_shift=(27-1)*2, decode=True):
        """
        another option: start_freeze=50,start_read=52,stop_read=52+2,stop_freeze=52+36,stop=52+36+10
        """
        # th=self.SET_VALUE["TH"]
        # self["TH"].set_voltage(1.5,unit="V")
        # self.SET_VALUE["TH"]=1.5
        ## reaset readout module of FPGA
        self['data_rx'].reset()
        self['data_rx'].READ_SHIFT = read_shift
        self['data_rx'].CONF_START_FREEZE = start_freeze
        self['data_rx'].CONF_START_READ = start_read
        self['data_rx'].CONF_STOP_FREEZE = stop_freeze
        self['data_rx'].CONF_STOP_READ = stop_read
        self['data_rx'].CONF_STOP = stop
        self['data_rx'].DISSABLE_GRAY_DECODER = not decode
        self['data_rx'].FORCE_READ = 0
        ## set switches
        self['CONF']['ClkBX'] = 1
        self['CONF']['ClkOut'] = 1
        self.reset_monoread(wait=0.001, sync_timestamp=sync_timestamp, bcid_only=False)
        # set th low, reset fifo, set rx on,wait for th, reset fifo to delete trash data
        #self["TH"].set_voltage(th,unit="V")
        #self.SET_VALUE["TH"]=th
        #self['fifo'].reset()
        self['data_rx'].set_en(True) ##readout trash data from chip
        time.sleep(0.3)
        self.logger.info('set_monoread: start_freeze={0:d} start_read={1:d} stop_read={2:0} stop_freeze={3:0} stop={4:0} reset fifo={5:0}'.format(
                     start_freeze, start_read, stop_read, stop_freeze, stop, self['fifo'].get_FIFO_SIZE()))
        self['fifo'].reset()  # discard trash
        
    def stop_monoread(self):
        self['data_rx'].set_en(False)
        lost_cnt=self["data_rx"]["LOST_COUNT"]
        if lost_cnt != 0:
            self.logger.warn("stop_monoread: error cnt={0:d}".format(lost_cnt))
        #exp=self["data_rx"]["EXPOSURE_TIME"]
        self.logger.info("stop_monoread:lost_cnt={0:d}".format(lost_cnt))
        self['CONF']['Rst'] = 1
        self['CONF']['ResetBcid'] = 1
        self['CONF']['EN_OUT_CLK'] = 0
        self['CONF']['EN_BX_CLK'] = 0
        self['CONF'].write()
        return lost_cnt

    def set_timestamp640(self, src="tlu"):
       self["timestamp_{0:s}".format(src)].reset()
       self["timestamp_{0:s}".format(src)]["EXT_TIMESTAMP"] = True
       if src == "tlu":
            self["timestamp_tlu"]["INVERT"] = 0
            self["timestamp_tlu"]["ENABLE_TRAILING"] = 0
            self["timestamp_tlu"]["ENABLE"] = 0
            self["timestamp_tlu"]["ENABLE_EXTERN"] = 1
       elif src == "inj":
            self["timestamp_inj"]["ENABLE_EXTERN"] = 0  # although this is connected to gate
            self["timestamp_inj"]["INVERT"] = 0
            self["timestamp_inj"]["ENABLE_TRAILING"] = 0
            self["timestamp_inj"]["ENABLE"] = 1
       elif src == "rx1":
            self["timestamp_tlu"]["INVERT"] = 0
            self["timestamp_inj"]["ENABLE_EXTERN"] = 0  # connected to 1'b1
            self["timestamp_inj"]["ENABLE_TRAILING"] = 0
            self["timestamp_inj"]["ENABLE"] = 1
       else:  # "mon"
            self["timestamp_mon"]["INVERT"] = 1
            self["timestamp_mon"]["ENABLE_TRAILING"] = 1
            self["timestamp_mon"]["ENABLE_EXTERN"] = 0
            self["timestamp_mon"]["ENABLE"] = 1
       self.logger.info("set_timestamp640:src={0:s}".format(src))
        
    def stop_timestamp640(self, src="tlu"):
        self["timestamp_{0:s}".format(src)]["ENABLE_EXTERN"] = 0
        self["timestamp_{0:s}".format(src)]["ENABLE"]=0
        lost_cnt=self["timestamp_{0:s}".format(src)]["LOST_COUNT"]
        self.logger.info("stop_timestamp640:src={0:s} lost_cnt={1:d}".format(src, lost_cnt))

    def stop_all_data(self):
        #self.stop_tlu()
        self.stop_monoread()
        #self.stop_timestamp640("tlu")
        self.stop_timestamp640("inj")
        #self.stop_timestamp640("rx1")
        self.stop_timestamp640("mon")
