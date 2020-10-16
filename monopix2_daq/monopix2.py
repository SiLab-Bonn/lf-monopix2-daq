from __future__ import print_function
import sys,time,os
import numpy as np
import logging
import warnings
import yaml
import bitarray
import tables
import yaml
import socket

sys.path = [os.path.dirname(os.path.abspath(__file__))] + sys.path 
OUTPUT_DIR=os.path.join(os.path.dirname(os.path.abspath(__file__)),"output_data")

from basil.dut import Dut
import basil.RL.StdRegister

def mk_fname(ext="data.npy",dirname=None):
    if dirname==None:
        prefix=ext.split(".")[0]
        dirname=os.path.join(OUTPUT_DIR,prefix)
    if not os.path.exists(dirname):
        os.system("mkdir -p %s"%dirname)
    return os.path.join(dirname,time.strftime("%Y%m%d_%H%M%S0_")+ext)

class Monopix2(Dut):
    default_yaml=os.path.dirname(os.path.abspath(__file__)) + os.sep + "monopix2_spi.yaml"
    def __init__(self,conf=None,no_power_reset=True):
        ## set logger
        self.logger = logging.getLogger()
        logFormatter = logging.Formatter("%(asctime)s [%(levelname)-5.5s] (%(threadName)-10s) %(message)s")
        fname=mk_fname(ext="log.log")
        fileHandler = logging.FileHandler(fname)
        fileHandler.setFormatter(logFormatter) 
        self.logger.addHandler(fileHandler)

        self.COL = 56
        self.ROW = 340

        if conf is None:
            conf = self.default_yaml

        if isinstance(conf,str):
            with open(conf) as f:
                conf=yaml.load(f)
        for i,e in enumerate(conf["hw_drivers"]):
            if e["type"]=="GPAC":
                conf["hw_drivers"][i]["init"]["no_power_reset"]=no_power_reset
                break
        super(Monopix2, self).__init__(conf)

        self.PIXEL_CONF = {'EnPre': np.full([self.COL,self.ROW], False, dtype = np.bool),
                       'EnInj'   : np.full([self.COL,self.ROW], False, dtype = np.bool),
                       'EnMonitor'   : np.full([self.COL,self.ROW], False, dtype = np.bool),
                       'Trim'  : np.full([self.COL,self.ROW], 0, dtype = np.uint8),
                       }
        self.SET={}

    def init(self):
        super(Monopix2, self).init()
        fw_version=self.get_fw_version()
        logging.info("Firmware version: {0}".format(fw_version))
        self['CONF_SR'].set_size(self["CONF_SR"]._conf['size'])
        self['CONF_DC'].set_size(self["CONF_DC"]._conf['size'])

    def get_fw_version(self):
        return self['intf'].read(0x10000,1)[0]
       
    def set_inj_all(self,inj_high=0.6,inj_low=0.2,
                    inj_n=100,inj_width=5000,inj_delay=5000,inj_phase=-1,
                    delay=700,ext=False):
        self["inj"].reset()
        self["inj"]["REPEAT"]=inj_n
        self["inj"]["DELAY"]=inj_delay
        self["inj"]["WIDTH"]=inj_width
        if inj_phase<0:
            inj_phase_des=-1
        else:
            self["inj"].set_phase(int(inj_phase))
            inj_phase_des=self["inj"]["PHASE_DES"]
            if self["inj"].get_phase()!=inj_phase:
                    self.logger.error("inj:set_inj_phase=%d PHASE_DES=%x"%(inj_phase,self["inj"]["PHASE_DES"]))
        self["inj"]["EN"]=ext
        
        self.logger.info("inj:%.4f,%.4f inj_width:%d inj_delay:%d inj_phase:%x inj_n:%d delay:%d ext:%d"%(
            inj_high,inj_low,inj_width,inj_delay,inj_phase,inj_n,delay,int(ext)))

    def start_inj(self,inj_low=None,wait=False):
        if inj_low is not None:
            self.set_inj_high(inj_high)
            self.logger.info("start_inj:%.4f,%.4f"%(self.SET["INJ_LO"],self["INJ_HI"]))
        self["inj"].start()
        while self["inj"].is_done()!=1 and wait:
             time.sleep(0.001)

############################################        
#### Configure the Shift Register
    def _write_global_conf(self):        
        self['CONF']['Ld_DAC'] = 1
        self['CONF'].write()

        self['CONF_SR']["EnPreLd"] = 1 ## active low
        self['CONF_SR']["EnMonitorLd"] = 1
        self['CONF_SR']["EnInjLd"] = 1
        self['CONF_SR']["TrimLd"].setall(True)
        self['CONF_SR'].write()
        while not self['CONF_SR'].is_ready:
            time.sleep(0.001)

        self['CONF']['Ld_DAC'] = 0
        self['CONF'].write()

    def set_global(self,**kwarg):
        """ kwarg must be like
         BLRes=32, VAmp=32, VPFB=32, VPFoll=12, VPLoad=11, Vfs=32, TDAC_LSB=32
        """
        for k in kwarg.keys():
            self["CONF_SR"][k]=kwarg[k]
        self._write_global_conf()
        s="set_global:"
        for k in kwarg.keys():
            s=s+"{0}={1:d}".format(k,kwarg[k])
        self.logger.info(s)

    def _write_pixel_mask(self, mask,Ld_Cnfg=1):
        #ClkOut=self['CONF']['ClkOut'].tovalue()
        #ClkBX=self['CONF']['ClkBX'].tovalue()
        rev_mask = np.copy(mask)
        rev_mask[1::2,:] = np.fliplr(mask[1::2,:]) #reverse every 2nd column
        mask_1d =  np.ravel(rev_mask)
        lmask = mask_1d.tolist()
        bv_mask = bitarray.bitarray(lmask)
        self['CONF_SR']['Pixels'][:] = bv_mask
        self['CONF']['Ld_Cnfg'] = Ld_Cnfg
        self['CONF']['Ld_DAC'] = 1
        #self['CONF']['ClkOut'] = 0
        #self['CONF']['ClkBX'] = 0
        self['CONF'].write()
        self['CONF_SR'].write()
        while not self['CONF_SR'].is_ready:
            time.sleep(0.001)
        
        self['CONF']['Ld_Cnfg'] = 0
        self['CONF']['Ld_DAC'] = 0
        #self['CONF']['ClkOut'] = ClkOut
        #self['CONF']['ClkBX'] = ClkBX
        self['CONF'].write()

    def _cal_pix(self,pix_bit,pix):
        if isinstance(pix,str):
            if pix=="all":
                self.PIXEL_CONF[pix_bit].fill(1)
            elif pix=="none":
                self.PIXEL_CONF[pix_bit].fill(0)
        elif isinstance(pix[0],int):
            self.PIXEL_CONF[pix_bit].fill(0)
            self.PIXEL_CONF[pix_bit][pix[0],pix[1]]=1
        elif len(pix)==self.COL and len(pix[0])==self.ROW:
            self.PIXEL_CONF[pix_bit][:,:]=np.array(pix,np.bool)
        else:
            self.PIXEL_CONF[pix_bit].fill(0)
            for p in pix:
               self.PIXEL_CONF[pix_bit][p[0],p[1]]=1

    def set_preamp_en(self,pix="all",EnColRO="auto",Out='autoCMOS'):
        self._cal_pix("EnPre",pix)
        if EnColRO=="auto":
            self['CONF_SR']['EnColRO'].setall(False)
            for i in range(self.COL):
                self['CONF_SR']['EnColRO'][i] = bool(np.any(self.PIXEL_CONF["EnPre"][i,:]))
        elif EnColRO=="all":
            self['CONF_SR']['EnColRO'].setall(True)
        elif EnColRO=="none":
            self['CONF_SR']['EnColRO'].setall(False)
        elif ":" in EnColRO:
            cols=np.zeros(self.COL,int)
            tmp=EnColRO.split(":")
            cols[int(tmp[0]):int(tmp[1])]=1
            for i in range(self.COL):
                self['CONF_SR']['EnColRO'][i] = bool(cols[i])
        elif len(EnColRO)==self.COL:
            self['CONF_SR']['EnColRO'] = EnColRO
        else:
            pass ## if "keep" then keep the value

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

        self['CONF_SR']["EnPreLd"] = 0 # active low 
        self._write_pixel_mask(self.PIXEL_CONF["EnPre"])
        self['CONF_SR']["EnPreLd"] = 1

    def set_mon_en(self,pix="none"):
        self._cal_pix("EnMonitor",pix)
        self['CONF_SR']['EnMonitorCol'].setall(False)
        for i in range(self.COL):
            self['CONF_SR']['EnMonitorCol'][i] = bool(np.any(self.PIXEL_CONF["EnMonitor"][i,:]))
        self['CONF_SR']["EnMonitorLd"] = 0 # active low
        self._write_pixel_mask(self.PIXEL_CONF["EnMonitor"])
        self['CONF_SR']["EnMonitorLd"] = 1
      
        arg=np.argwhere(self.PIXEL_CONF["EnMonitor"][:,:])
        self.logger.info("set_mon_en pix: %d %s"%(len(arg),str(arg).replace("\n"," ")))

    def set_inj_en(self,pix="none"):
        self._cal_pix("EnInj",pix)
        self['CONF_SR']['InjEnCol'].setall(True)  ## active low
        for i in range(self.COL):
            self['CONF_SR']['InjEnCol'][i] = bool(np.any(self.PIXEL_CONF["EnInj"][i,:]))
        self['CONF_SR']["EnInjLd"] = 0 # active low 
        self._write_pixel_mask(self.PIXEL_CONF["EnInj"])
        self['CONF_SR']["EnInjLd"] = 1
        
        arg=np.argwhere(self.PIXEL_CONF["EnInj"][:,:])
        self.logger.info("set_inj_en pix: %d %s"%(len(arg),str(arg).replace("\n"," ")))
        
    def set_tdac(self,tdac):
        if isinstance(tdac,int):
            self.PIXEL_CONF["Trim"].fill(tdac)
            self.logger.info("set_tdac all: %d"%tdac)
        elif len(tdac)==len(self.PIXEL_CONF["Trim"]) and \
             len(tdac[0])== len(self.PIXEL_CONF["Trim"][0]):
            self.logger.info("set_tdac: matrix")
            self.PIXEL_CONF["Trim"]=np.array(tdac,dtype = np.uint8)
        else:
            self.logger.info("ERROR: wrong instance. tdac must be int or [36,129]")
            return 

        trim_bits = np.unpackbits(self.PIXEL_CONF['Trim'])
        trim_bits_array = np.reshape(trim_bits, (self.COL,self.ROW,8)).astype(np.bool)
        for bit in range(4):
            trim_bits_sel_mask = trim_bits_array[:,:,7-bit]
            self['CONF_SR']['TrimLd'][bit] = 0
            self._write_pixel_mask(trim_bits_sel_mask,Ld_Cnfg=0)
            self['CONF_SR']['TrimLd'][bit] = 1

    def get_conf_sr(self,mode='mwr'):
        """ mode:'w' get values in FPGA write register (output to SI_CONF)
                 'r' get values in FPGA read register (input from SO_CONF)
                 'm' get values in cpu memory (data in self['CONF_SR'])
                 'mrw' get all
        """
        if "c" in mode:
            spi="CONF_DC"
        else:
            spi="CONF_SR"
        size=self[spi]._conf['size']
        hw=self[spi]._conf['hw_driver']
        byte_size=self[hw]._mem_bytes
        data={"size":size}
        if "w" in mode:
            w = bitarray.bitarray(endian='big')
            w.frombytes(self[spi].get_data(size=byte_size,addr=0).tostring())
            data["write_reg"]=basil.RL.StdRegister.StdRegister(None, self[spi]._conf)
            data["write_reg"][:]=w[size-1::-1]
        if "r" in mode:
            r = bitarray.bitarray(endian='big')
            r.frombytes(self[spi].get_data(size=byte_size).tostring())
            data["read_reg"]=basil.RL.StdRegister.StdRegister(None, self[spi]._conf)
            data["read_reg"][:]=r[size-1::-1]
        if "m" in mode:
            data["memory"]=basil.RL.StdRegister.StdRegister(None, self[spi]._conf)
            data["memory"][:]=self[spi][:].copy()
        return data

    def set_gate(self,gate_width=1000,gate_delay=100,gate_n=1):
        self['CONF']['EN_GATE'] = 1
        self['CONF'].write()
        self["gate"].reset()
        self["gate"]["REPEAT"]=gate_n
        self["gate"]["DELAY"]=gate_delay
        self["gate"]["WIDTH"]=gate_width 

    def start_gate(self,wait=False):
        self['CONF']['EN_GATE'] = 1
        self['CONF'].write()
        self["gate"].start()
        while self["gate"].is_done()!=1 and wait:
             time.sleep(0.001) 

    def stop_gate(self):
        self['CONF']['EN_GATE'] = 0
        self['CONF'].write()
        self["gate"].reset()
############################################        
#### Get data from FIFO
    def get_data_now(self):
        return self['fifo'].get_data()

    def get_data(self,wait=0.2):
        self["inj"].start()
        i=0
        raw=np.empty(0,dtype='uint32')
        while self["inj"].is_done()!=1:
            time.sleep(0.001)
            raw=np.append(raw,self['fifo'].get_data())
            i=i+1
            if i>10000:
                break
        time.sleep(wait)
        raw=np.append(raw,self['fifo'].get_data())
        if i>10000:
            self.logger.info("get_data: error timeout len=%d"%len(raw))
        lost_cnt=self["data_rx"]["LOST_COUNT"]
        if self["data_rx"]["LOST_COUNT"]!=0:
            self.logger.warn("get_data: error cnt=%d"%lost_cnt)      
        return raw

    def reset_monoread(self,wait=0.001,sync_timestamp=True,bcid_only=True):
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

        self['intf'].read_str(0x10010+1,size=2)
        self['intf'].read_str(0x10010+1,size=2)
        self['intf'].read_str(0x10010+1,size=2)
        self['CONF']['ResetBcid'] = 0
        self['CONF'].write()
        self['intf'].read_str(0x10010+1,size=2)
        self['intf'].read_str(0x10010+1,size=2)
        self['intf'].read_str(0x10010+1,size=2)

    def set_monoread(self,start_freeze=252,start_read=252+8,stop_read=252+8+8,
                     stop_freeze=252+8+8+(27+4-1)+8,stop=252+8+8+(27+4-1)+16,
                     sync_timestamp=False,read_shift=(27+4-1)*2+1,decode=True):
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
        self['data_rx'].DISSABLE_GRAY_DECODER= not decode
        self['data_rx'].FORCE_READ= 0
        ## set switches
        self['CONF']['ClkBX'] = 1
        self['CONF']['ClkOut'] = 1
        self.reset_monoread(wait=0.001,sync_timestamp=sync_timestamp,bcid_only=False)
        # set th low, reset fifo, set rx on,wait for th, reset fifo to delete trash data
        #self["TH"].set_voltage(th,unit="V")
        #self.SET_VALUE["TH"]=th
        #self['fifo'].reset()
        self['data_rx'].set_en(True) ##readout trash data from chip
        time.sleep(0.3)
        self.logger.info('set_monoread: start_freeze=%d start_read=%d stop_read=%d stop_freeze=%d stop=%d reset fifo=%d'%(
                     start_freeze,start_read,stop_read,stop_freeze,stop, self['fifo'].get_FIFO_SIZE()))
        self['fifo'].reset() ## discard trash
        
    def stop_monoread(self):
        self['data_rx'].set_en(False)
        lost_cnt=self["data_rx"]["LOST_COUNT"]
        if lost_cnt!=0:
            self.logger.warn("stop_monoread: error cnt=%d"%lost_cnt)
        #exp=self["data_rx"]["EXPOSURE_TIME"]
        self.logger.info("stop_monoread:lost_cnt=%d"%lost_cnt)
        self['CONF']['Rst'] = 1
        self['CONF']['ResetBcid'] = 1
        self['CONF']['EN_OUT_CLK'] = 0
        self['CONF']['EN_BX_CLK'] = 0
        self['CONF'].write()
        return lost_cnt

    def set_timestamp640(self,src="tlu"):
       self["timestamp_%s"%src].reset()
       self["timestamp_%s"%src]["EXT_TIMESTAMP"]=True
       if src=="tlu":
            self["timestamp_tlu"]["INVERT"]=0
            self["timestamp_tlu"]["ENABLE_TRAILING"]=0
            self["timestamp_tlu"]["ENABLE"]=0
            self["timestamp_tlu"]["ENABLE_EXTERN"]=1
       elif src=="inj":
            self["timestamp_inj"]["ENABLE_EXTERN"]=0 ##although this is connected to gate
            self["timestamp_inj"]["INVERT"]=0
            self["timestamp_inj"]["ENABLE_TRAILING"]=0
            self["timestamp_inj"]["ENABLE"]=1
       elif src=="rx1":
            self["timestamp_tlu"]["INVERT"]=0
            self["timestamp_inj"]["ENABLE_EXTERN"]=0 ## connected to 1'b1
            self["timestamp_inj"]["ENABLE_TRAILING"]=0
            self["timestamp_inj"]["ENABLE"]=1
       else: #"mon"
            self["timestamp_mon"]["INVERT"]=1
            self["timestamp_mon"]["ENABLE_TRAILING"]=1
            self["timestamp_mon"]["ENABLE_EXTERN"]=0
            self["timestamp_mon"]["ENABLE"]=1
       self.logger.info("set_timestamp640:src=%s"%src)
        
    def stop_timestamp640(self,src="tlu"):
        self["timestamp_%s"%src]["ENABLE_EXTERN"]=0
        self["timestamp_%s"%src]["ENABLE"]=0
        lost_cnt=self["timestamp_%s"%src]["LOST_COUNT"]
        self.logger.info("stop_timestamp640:src=%s lost_cnt=%d"%(src,lost_cnt))

    def stop_all_data(self):
        #self.stop_tlu()
        self.stop_monoread()
        #self.stop_timestamp640("tlu")
        self.stop_timestamp640("inj")
        #self.stop_timestamp640("rx1")
        self.stop_timestamp640("mon")