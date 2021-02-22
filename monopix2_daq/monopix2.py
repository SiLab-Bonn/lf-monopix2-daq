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

    # Default pad for Monopix2 yaml file
    default_yaml = os.path.dirname(os.path.abspath(__file__)) + os.sep + "monopix2.yaml"

    def __init__(self, conf=None, no_power_reset=True):
        """
        Automatic initialization of the chip

        Parameters
        ----------
        conf: string 
            .yaml file used for configuration. If none is provided, then "default_yaml" is used.
        no_power_reset: boolean
            This conditional will enable or disable the power cycling of the GPAC. 
            (If no_power_reset=True: The GPAC will NOT power cycle when the chip is initialized ---> Default for chip safety)
        """

        # Initialize logger.
        self.logger = logging.getLogger()
        logFormatter = logging.Formatter("%(asctime)s [%(levelname)-5.5s] (%(threadName)-10s) %(message)s")
        fname = mk_fname(ext="log.log")
        fileHandler = logging.FileHandler(fname)
        fileHandler.setFormatter(logFormatter) 
        self.logger.addHandler(fileHandler)
        self.logger.info("LF-Monopix2 initialized at "+time.strftime("%Y-%m-%d_%H:%M:%S"))

        # Define chip dimensions.
        self.COL_SIZE = 56 
        self.ROW_SIZE = 340

        # Load configuration from yaml file and initialize taking into account the power reset instructions.
        if conf is None:
            conf = self.default_yaml
        if isinstance(conf, str):
            with open(conf) as f:
                conf = yaml.load(f, Loader=yaml.SafeLoader)
            for i, e in enumerate(conf["hw_drivers"]):
                if e["type"]=="GPAC":
                    conf["hw_drivers"][i]["init"]["no_power_reset"] = no_power_reset
                    break
        super(Monopix2, self).__init__(conf)

        # Initialize relevant dictionaries for masks of pixel bit arrays.
        self.PIXEL_CONF = {'EnPre': np.full([self.COL_SIZE,self.ROW_SIZE], False, dtype = np.bool),
                       'EnInj'   : np.full([self.COL_SIZE,self.ROW_SIZE], False, dtype = np.bool),
                       'EnMonitor'   : np.full([self.COL_SIZE,self.ROW_SIZE], False, dtype = np.bool),
                       'Trim'  : np.full([self.COL_SIZE,self.ROW_SIZE], 0, dtype = np.uint8),
                       }
        self.SET_VALUE = {}

    def init(self):
        """
        Initialization of the chip.
        """
        super(Monopix2, self).init()

        # Get firmware version and log it.
        fw_version = self.get_fw_version()
        logging.info("Firmware version: {}".format(fw_version))

        # Load default configuration.
        self['CONF_SR'].set_size(self["CONF_SR"]._conf['size'])
        self['CONF']['Def_Conf'] = 1
        self['CONF'].write()

        # Power on the chip
        self.power_on()

        # Program the global configuration registers (Si driven by ClkSR, and then valid Ld).  
        # Internally, the function will also disable the default configuration.
        self._write_global_conf()

        # Creates a mask of zeroes and loads it to the corresponding preamplifier, injection and monitoring bit arrays. 
        initial_mask=self._cal_mask(pix="none")
        self._write_pixel_mask(bit="EnPre", mask=initial_mask, over_write=True)
        self._write_pixel_mask(bit="EnInj", mask=initial_mask, over_write=True)
        self._write_pixel_mask(bit="EnMonitor", mask=initial_mask, over_write=True)
        
        # Disable the default configuration.
        # (Maybe this is not necessary as it was done already in write_global_conf, but doesn't hurt)
        self['CONF']['Def_Conf'] = 0
        self['CONF'].write()

    def get_fw_version(self):
        """
        Get firmware version.

        Returns
        ----------
        fw_version: int 
            Integer of the current MIO3 + LF-Monopix2 firmware version.
        """
        fw_version = self['intf'].read(0x10000, 1)[0]
        return fw_version

    def power_on(self, 
                VPC=1.8, VDD_EOC=1.8, VDDD=1.8, VDDA=1.8, #POWER SOURCES (VDD_EOC and VDD_IO are powered together)
                BL=0.75, TH1=1.5, TH2=1.5, TH3=1.5, #VOLTAGE SOURCES (Depending on the jumper configuration TH2 and TH3 can be used for VCasc1 or VCasc2)
                NTC=5, Idac_TDAC_LSB=0, Iref=-8, # CURRENT SOURCES
                VHi= 0.2): #A value for the voltages of the GPAC injection line. INJ_HI must be the same as INJ_LO, and both igual to the expected VHi on the chip.
        """
        Powers on the chip. 

        Parameters
        ----------
        VPC: double
            Precharge voltage.
        VDD_EOC: double
            Digital periphery voltage. (in the Silab-Bonn PCB, VDD_IO is also powered through this line. So, it also supplies the chip's IO.)
        VDDD: double
            Digital matrix voltage.
        VDDA: double
            Analog voltage.
        BL: double
            Discriminator baseline
        TH1:
            Global threshold for matrix sub-arrays with CSA 1.
        TH2:
            Global threshold for matrix sub-arrays with CSA 2.
        TH3:
            Global threshold for matrix sub-arrays with CSA 3.  
        NTC:
            NTC for temperature measurement. 
        Idac_TDAC_LSB:
            Current to overwrite the LSB of TDAC.
        Iref:
            Reference current of the Biasing DAC. (Out: Negative)      
        VHi:
            High voltage level of the digital injection. (Both INJ_HI and INJ_LO of the GPAC should be set to the SAME value)
            The difference of VHi (This value) and VLo (set with a Poti on the chip card) defines the amplitude of the injection pulse.
        """

        # POWER SOURCES
        self['VPC'].set_voltage(VPC, unit='V')
        self['VPC'].set_enable(True)
        self.SET_VALUE['VPC']=VPC  
        self['VDD_EOC'].set_voltage(VDD_EOC, unit='V')
        self['VDD_EOC'].set_enable(True)
        self.SET_VALUE['VDD_EOC']=VDD_EOC
        self['VDDD'].set_current_limit(200, unit='mA')
        self['VDDD'].set_voltage(VDDD, unit='V')
        self['VDDD'].set_enable(True)
        self.SET_VALUE['VDDD']=VDDD
        self['VDDA'].set_voltage(VDDA, unit='V')
        self['VDDA'].set_enable(True)
        self.SET_VALUE['VDDA']=VDDA

        # VOLTAGE SOURCES        
        self['BL'].set_voltage(BL, unit='V')
        self.SET_VALUE['BL']=BL
        self['TH1'].set_voltage(TH1, unit='V')
        self.SET_VALUE['TH1']=TH1
        self['TH2'].set_voltage(TH2, unit='V')  #Depending on jumper placement, might control VCasc1
        self.SET_VALUE['TH2']=TH2
        self['TH3'].set_voltage(TH3, unit='V')  #Depending on jumper placement, might control VCasc2
        self.SET_VALUE['TH3']=TH3
        
        # CURRENT SOURCES         
        self["NTC"].set_current(NTC,unit="uA")
        self.SET_VALUE['NTC']=NTC
        self['Idac_TDAC_LSB'].set_current(Idac_TDAC_LSB, unit='uA')
        self.SET_VALUE['Idac_TDAC_LSB']=Idac_TDAC_LSB
        self['Iref'].set_current(Iref, unit='uA')
        self.SET_VALUE['Iref']=Iref

        # GPAC ANALOG INJECTION (Both values have to be equal to the expected VHi for the digital injection)
        self['INJ_HI'].set_voltage(VHi, unit='V')
        self.SET_VALUE['INJ_HI']=VHi
        self['INJ_LO'].set_voltage(VHi, unit='V')
        self.SET_VALUE['INJ_LO']=VHi
    
    def power_off(self):
        """
        Disables power suplies for the chip.
        """
        for pwr in ['VPC', 'VDD_EOC', 'VDDD', 'VDDA']:
            self[pwr].set_enable(False)

    def power_status(self):
        """
        Returns a dictionary with the overall power status of the chip. 

        Returns
        ----------
        pw_status: dict
            Dictionary with the voltage and current values (Read & Set) of all Power, Voltage and Current sources.
        """
        pw_status = {}       
        for pwr_id in ['VPC', 'VDD_EOC', 'VDDD', 'VDDA', 
                    'BL', 'TH1', 'TH2', 'TH3', 'NTC',
                    'Idac_TDAC_LSB', 'Iref']:
            pw_status[pwr_id+'[V]'] =  self[pwr_id].get_voltage(unit='V')
            pw_status[pwr_id+'[mA]'] = self[pwr_id].get_current(unit='mA')
            pw_status[pwr_id+"_set"] = self.SET_VALUE[pwr_id]
        for pwr_id in ['INJ_LO', 'INJ_HI']:
            pw_status[pwr_id+"_set"] = self.SET_VALUE[pwr_id]
        return pw_status

    def dac_status(self):
        """
        Returns a dictionary with the overall status of the DACs of the chip. 

        Returns
        ----------
        dac_status: dict
            Dictionary with the DAC values currently set for the configuration of the chip.
            Note: All converted from binary to decimal, except 'EnSRDCol', 'EnMonitorCol', 'InjEnCol' and 'EnColRO'.
        """
        dac_status = {}       
        for dac_id in ['EnPreLd', 'EnMonitorLd', 'EnInjLd', 'TrimLd', 'EnSoDCol', 'EnAnaBuffer', 'DelayROConf',
                    'EnTestPattern', 'EnDataCMOS', 'EnDataLVDS', 'Mon_BLRes', 'Mon_VAmp1', 'Mon_VAmp2',
                    'Mon_VPFB', 'Mon_VPFoll', 'Mon_VNFoll', 'Mon_VNLoad', 'Mon_VPLoad',
                    'Mon_Vsf', 'Mon_TDAC_LSB', 'Mon_Driver', 
                    'BLRes', 'VAmp1', 'VAmp2', 'VPFB', 'VPFoll', 'VNFoll',
                    'VNLoad', 'VPLoad', 'Vsf', 'TDAC_LSB', 'Driver'
                    ]:
            dac_status[dac_id] = int(str(self['CONF_SR'][dac_id]), 2)
        for dac_id in ['EnSRDCol', 'EnMonitorCol', 'InjEnCol', 'EnColRO']:
            dac_status[dac_id] = self['CONF_SR'][dac_id]
        return dac_status

    def inj_status(self):
        """
        Returns a dictionary with the overall status of the injection settings of the chip. 

        Returns
        ----------
        inj_status: dict
            Dictionary with the values currently set for the configuration of the injection circuit.
        """
        inj_status = {}       
        for injparam_id in ['EN', 'DELAY', 'WIDTH', 'REPEAT']:
            inj_status[injparam_id] = self['inj'][injparam_id]
        return inj_status

    def set_Vhigh(self, VHi=0.2):
        """
        A function that sets a given VHi value to both 'INJ_HI' and 'INJ_LO' on the GPAC.
        """
        self['INJ_HI'].set_voltage(VHi, unit='V')
        self.SET_VALUE['INJ_HI']=VHi
        self['INJ_LO'].set_voltage(VHi, unit='V')
        self.SET_VALUE['INJ_LO']=VHi

    def set_inj_all(self, inj_high=0.6,
                    inj_n=100, inj_width=3000, inj_delay=6000, 
                    inj_phase=-1, ext_trigger=False):
        """
        Sets the global parameters for injection pulses.

        Parameters
        ----------
        inj_high: double
            Value set to both INJ_HI and INJ_LOW in the GPAC, corresponding to VHi for the actual injection in LF-Monopix2
        inj_n: int
            Number of pulses to be injected (0: Permanent injection)
        inj_width: int
            Width of the injection pulse. In clocks. 
        inj_delay: int
            Time period between injection pulses. In clocks. 
        inj_phase: int
            640 MHz delay of the injection within a 40 MHz clock. Values 0 to 15.
            Note: Only functional with the pulsegen640 module (in MIO3). Otherwise, set to -1.
        ext_trigger: boolean
            Defines if the pulse comes with a fixed delay respect to an external trigger signal EXT_START (True) or only at software start (False).
        """

        # Sets the value for VHi.
        self.set_Vhigh(VHi=inj_high)

        # Reset the injection module and set values given as parameters.
        self["inj"].reset()
        self["inj"]["REPEAT"] = inj_n
        self["inj"]["DELAY"] = inj_delay
        self["inj"]["WIDTH"] = inj_width

        # TODO Double-check the logic of the phase setting. 
        if inj_phase < 0:
            inj_phase_des = -1
        else:
            self["inj"].set_phase(int(inj_phase))
            inj_phase_des = self["inj"]["PHASE_DES"]
            if self["inj"].get_phase() != inj_phase:
                self.logger.error("inj:set_inj_phase={0:d} PHASE_DES={1:x}".format(inj_phase, self["inj"]["PHASE_DES"]))
        self["inj"]["EN"] = ext_trigger
        
        # Logs the corresponding injection values.
        self.logger.info("Parameters set for injection: VHi:{0:.4f}, VLo:{1:s}, REPEAT:{2:d}, DELAY:{3:d}, WIDTH:{4:d}, PHASE:{5:d}, External Trigger:{6:d}".format(
        self.SET_VALUE['INJ_HI'], "Set on board", self["inj"]["REPEAT"], self["inj"]["DELAY"], self["inj"]["WIDTH"], inj_phase_des, self["inj"]["EN"]))

    def start_inj(self):
        """
        Starts injection into the chip.
        """
        # Starts injection into the chip.
        self.logger.info("Starting with injection: VHi:{0:.4f}, VLo:{1:s}".format(self.SET_VALUE['INJ_HI'], "Set on board"))
        self["inj"].start()
        while self["inj"].is_done() != 1:
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
            #Data going to the global configuration
            self['CONF']['En_Cnfg_Pix'] = 0
            self['CONF'].write()
            self['CONF_SR'].write()
            while not self['CONF_SR'].is_ready:
                time.sleep(0.001)
            # Data going to the matrix
            self['CONF']['En_Cnfg_Pix'] = 1
            self['CONF'].write()
            self['CONF_DC'].write()
            while not self['CONF_DC'].is_ready:
                time.sleep(0.001)
            #Data going to the global configuration    
            self['CONF']['En_Cnfg_Pix'] = 0
            arg = np.argwhere(mask != defval)
        else:
            arg = np.argwhere(self.PIXEL_CONF[bit] != mask)
        # Calculate the double column indexes from the pixels that want to be changed. 
        uni = np.unique(arg[:, 0]//2)
        print("=====sim=====uni", bit, uni)
        # set individual double col
        for dcol in uni:
            self['CONF_SR']['EnSRDCol'].setall(False)
            ##############print("=====sim=====dcol", type(dcol), dcol, type(self['CONF_SR']['EnSRDCol'][0]))
            self['CONF_SR']['EnSRDCol'][dcol] = '1'
            #Data going to the global configuration
            self['CONF']['En_Cnfg_Pix'] = 0
            self['CONF'].write()
            #############print("=====sim=====InjEnCol in write", self['CONF_SR']['InjEnCol'])
            self['CONF_SR'].write()
            while not self['CONF_SR'].is_ready:
                time.sleep(0.001)
            # Index the double column as 2 columns
            self['CONF_DC']['Col0'] = bitarray.bitarray(list(mask[dcol*2+1, :]))
            self['CONF_DC']['Col1'] = bitarray.bitarray(list(mask[dcol*2, ::-1]))
            # Data going to the matrix
            self['CONF']['En_Cnfg_Pix'] = 1
            self['CONF'].write()
            self['CONF_DC'].write()
            #############print("=====sim=====",dcol, self['CONF_DC'])
            while not self['CONF_DC'].is_ready:
                time.sleep(0.001)
            self['CONF']['En_Cnfg_Pix'] = 0
        # Disable the in-pixel configuration
        self['CONF_SR']["{0:s}Ld".format(bit)] = 1 #Active Low
        self['CONF_SR'].write()
        while not self['CONF_SR'].is_ready:
            time.sleep(0.001)
        # Enable read-out clocks
        if ro_off:
            self['CONF']['ClkOut'] = ClkOut  # Readout OFF
            self['CONF']['ClkBX'] = ClkBX
        self['CONF'].write()
        self.PIXEL_CONF[bit] = mask

    def _cal_mask(self, pix):
        mask = np.zeros([self.COL_SIZE, self.ROW_SIZE])
        if isinstance(pix, str):
            if pix == "all":
                mask.fill(1)
            elif pix == "none":
                pass
        elif isinstance(pix[0], int):
            mask[pix[0], pix[1]] = 1
        elif len(pix) == self.COL_SIZE and len(pix[0]) == self.ROW_SIZE:
            mask[:, :] = np.array(pix, np.bool)
        else:
            for p in pix:
                mask[p[0], p[1]] = 1
        return mask

    def set_preamp_en(self, pix="all", EnColRO="auto", Out='autoCMOS'):
        mask = self._cal_mask(pix)
        if EnColRO == "auto":
            self['CONF_SR']['EnColRO'].setall(False)
            for i in range(self.COL_SIZE):
                self['CONF_SR']['EnColRO'][i] = bool(np.any(mask[i,:]))
        elif EnColRO == "all":
            self['CONF_SR']['EnColRO'].setall(True)
        elif EnColRO == "none":
            self['CONF_SR']['EnColRO'].setall(False)
        elif ":" in EnColRO:
            cols = np.zeros(self.COL_SIZE, int)
            tmp = EnColRO.split(":")
            cols[int(tmp[0]):int(tmp[1])] = 1
            for i in range(self.COL_SIZE):
                self['CONF_SR']['EnColRO'][i] = bool(cols[i])
        elif len(EnColRO) == self.COL_SIZE:
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

        self._write_pixel_mask(bit="EnPre", mask=mask)

    def set_mon_en(self, pix="none"):
        mask = self._cal_mask(pix)
        self['CONF_SR']['EnMonitorCol'].setall(False)
        for i in range(self.COL_SIZE):
            self['CONF_SR']['EnMonitorCol'][i] = bool(np.any(mask[i,:]))
        self._write_pixel_mask("EnMonitor", mask)
      
        arg = np.argwhere(self.PIXEL_CONF["EnMonitor"][:, :])
        self.logger.info("set_mon_en pix: {0:d} {1:s}".format(len(arg), str(arg).replace("\n", " ")))

    def set_inj_en(self, pix="none"):
        mask = self._cal_mask(pix)
        self['CONF_SR']['InjEnCol'].setall(True)
        for i in range(self.COL_SIZE):
            if np.any(mask[i, :]):
                val='0'
            else:
                val='1'
            print("=====sim=====InjEnCol", i, np.any(mask[i, :]), mask[i, :], val)
            self['CONF_SR']['InjEnCol'][i] = val
        print("=====sim=====InjEnCol", self['CONF_SR']['InjEnCol'])
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
            self.logger.info("ERROR: wrong instance. tdac must be int or [{0:d},{1:d}]".format(self.COL_SIZE, self.ROW_SIZE))
            return 

        trim_bits = np.unpackbits(mask)
        trim_bits_array = np.reshape(trim_bits, (self.COL_SIZE, self.ROW_SIZE, 8)).astype(np.bool)
        for bit in range(4):
            trim_bits_sel_mask = trim_bits_array[:, :, 7-bit]
            self._write_pixel_mask('TrimLd{0:d}'.format(bit), trim_bits_sel_mask)

    def get_conf_sr(self, mode='mwr'):
        """ mode:'w' get values in FPGA write register (output to SI_CONF)
                 'r' get values in FPGA read register (input from SO_CONF)
                 'm' get values in cpu memory (data in self['CONF_SR'])
                 'mrw' get allmask
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
            print("=====sim===== get_data len",len(raw),self["inj"].is_done())
            i = i+1
            if i > 10000:
                break
        for i in range(10):
            print("=====sim===== get_data len", i, len(raw),self["inj"].is_done())
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

        #self['intf'].read_str(0x10010+1, size=2)
        #self['intf'].read_str(0x10010+1, size=2)
        #self['intf'].read_str(0x10010+1, size=2)
        self['CONF']['ResetBcid'] = 0
        self['CONF'].write()
        #self['intf'].read_str(0x10010+1, size=2)
        #self['intf'].read_str(0x10010+1, size=2)
        #self['intf'].read_str(0x10010+1, size=2)

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
        self['data_rx'].FORCE_READ = 1 #0
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
        #self['fifo'].reset()  # discard trash
        
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

    def get_temperature(self):
        """
        Returns the temperature as measured (in C) at the NTC near the chip.

        Returns
        ----------
        temp_mean: double
            Mean measurement of the temperature on the chip in Celsius.
        """
        vol=self["NTC"].get_voltage()
        if not (vol>0.5 and vol<1.5):
          for i in np.arange(200,-200,-2):
            self["NTC"].set_current(i,unit="uA")
            self.SET_VALUE["NTC"]=i
            time.sleep(0.1)
            vol=self["NTC"].get_voltage()
            if vol>0.7 and vol<1.3:
                break
          if abs(i)>190:
            self.logger.info("temperature() NTC error")
        temp=np.empty(10)
        for i in range(len(temp)):
            temp[i]=self["NTC"].get_temperature("C")
        temp_mean=np.average(temp[temp!=float("nan")])
        return temp_mean
