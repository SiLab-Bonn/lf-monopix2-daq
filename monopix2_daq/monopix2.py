import sys
import time
import os
import numpy as np
import logging
import bitarray
import tables
import yaml
import socket

from basil.dut import Dut
import basil.RL.StdRegister

sys.path = [os.path.dirname(os.path.abspath(__file__))] + sys.path 
OUTPUT_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "output_data")

def mk_fname(ext="data.npy",dirname=None):
    if dirname == None:
        prefix = ext.split(".")[0]
        dirname = os.path.join(OUTPUT_DIR, prefix)
    if not os.path.exists(dirname):
        os.system("mkdir -p {0:s}".format(dirname))
    return os.path.join(dirname, time.strftime("%Y%m%d_%H%M%S0_")+ext)

class Monopix2(Dut):

    # Default path for Monopix2 yaml file
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
            (If no_power_reset=True: The GPAC will NOT power cycle when the chip is initialized ---> Default for chip safety when high voltage is applied.)
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

        # Define reference lists to differentiate keys from power, voltage and current 
        #TODO: Check if these lists can replace "SET_VALUE" as independent dictionaries, to avoid double configuration confusions.
        self.PWR_CONF=['VPC', 'VDD_EOC', 'VDDD', 'VDDA']
        self.VLT_CONF=['BL', 'TH1', 'TH2', 'TH3']
        self.CRR_CONF=['NTC', 'Idac_TDAC_LSB', 'Iref']
        self.REG_CONF={}
        for field in self["CONF_SR"]._conf['fields']:
            self.REG_CONF[field['name']]=self["CONF_SR"][field['name']]

        # Initialize relevant dictionaries for masks of pixel bit arrays.
        # self.PIXEL_CONF = {'EnPre': np.full([self.COL_SIZE,self.ROW_SIZE], False, dtype = np.bool),
        #                'EnInj'   : np.full([self.COL_SIZE,self.ROW_SIZE], False, dtype = np.bool),
        #                'EnMonitor'   : np.full([self.COL_SIZE,self.ROW_SIZE], False, dtype = np.bool),
        self.PIXEL_CONF = {'EnPre': np.full([self.COL_SIZE,self.ROW_SIZE], 0, dtype = np.uint8),
                       'EnInj'   : np.full([self.COL_SIZE,self.ROW_SIZE], 0, dtype = np.uint8),
                       'EnMonitor'   : np.full([self.COL_SIZE,self.ROW_SIZE], 0, dtype = np.uint8),
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
        
        #Wait time between GPAC initialization and actual 
        time.sleep(0.1)

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
        initial_mask=self._create_mask(pix="none")
        self._write_pixel_mask(bit="EnPre", mask=initial_mask, overwrite=True)
        self._write_pixel_mask(bit="EnInj", mask=initial_mask, overwrite=True)
        self._write_pixel_mask(bit="EnMonitor", mask=initial_mask, overwrite=True)
        #self.set_tdac(0)
        
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

    """
    POWER AND DAC SETTINGS
    """
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

        self.logger.info("Powering LF-Monopix2...")

        # POWER SOURCES
        self['VDDA'].set_current_limit(200, unit='mA')
        self['VDDA'].set_voltage(VDDA, unit='V')
        self['VDDA'].set_enable(True)
        self.SET_VALUE['VDDA']=VDDA
        self['VDDD'].set_current_limit(200, unit='mA')
        self['VDDD'].set_voltage(VDDD, unit='V')
        self['VDDD'].set_enable(True)
        self.SET_VALUE['VDDD']=VDDD
        self['VDD_EOC'].set_voltage(VDD_EOC, unit='V')
        self['VDD_EOC'].set_enable(True)
        self.SET_VALUE['VDD_EOC']=VDD_EOC
        self['VPC'].set_voltage(VPC, unit='V')
        self['VPC'].set_enable(True)
        self.SET_VALUE['VPC']=VPC  

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

        time.sleep(0.2)
        self.logger.info("LF-Monopix2 Powered ON.")
        self.power_status(log=True)

    def power_off(self):
        """
        Disables power suplies for the chip.
        """
        self.logger.info("Powering off LF-Monopix2...")
        # Turn down current sources
        self.set_global_current(Idac_TDAC_LSB=0, Iref=0)
        # Turn down voltage sources
        self.set_global_voltage(TH1=0, TH2=0, TH3=0, BL=0)
        # Disable power sources
        for pwr in self.PWR_CONF:
            self.disable_global_power(pwr)
        self.logger.info("LF-Monopix2 Powered OFF.")
    
    def set_global_power(self, **kwarg):
        """
        Sets a global power to a specific value (in V).

        Parameters
        ----------
        kwarg:
            Any name on the list of global power domains as parameter name, followed by the value expected to be set as parameter value.
            e.g. self.set_global_power(VDDD=1.8)
        """
        for k in kwarg.keys():
            if k in self.PWR_CONF:
                self[k].set_voltage(kwarg[k], unit='V')
                self[k].set_enable(True)
                self.SET_VALUE[k]=kwarg[k] 
                feedback=[self[k].get_voltage(unit='V'), self[k].get_current(unit='mA')]
                self.logger.info("Set {0:s}={1:.4f} V | Read {2:s}={3:.4f} V ({4:.4f} mA)".format(k, kwarg[k], k, feedback[0], feedback[1]))
            else:
                self.logger.info("{0:s} is not defined as a valid power domain.".format(k))

    def disable_global_power(self, pwr_str=""):
        """
        Disable a global power.

        Parameters
        ----------
        pwr_str: string
            A string with the name of a valid power domain.
            e.g. self.disable_global_power("VDDD")
        """
        if isinstance(pwr_str, str) and pwr_str!= "":
            if pwr_str in self.PWR_CONF:
                self[pwr_str].set_enable(False)
                time.sleep(0.2)
                feedback=[self[pwr_str].get_voltage(unit='V'), self[pwr_str].get_current(unit='mA')]
                self.logger.info("{0:s} DISABLED | Read {1:s}={2:.4f} V ({3:.4f} mA)".format(pwr_str, pwr_str, feedback[0], feedback[1]))
            else:
                self.logger.info("{0:s} is not defined as a valid power domain.".format(pwr_str))
        else:
            self.logger.info("Your parameter must be the name (string) of a valid power domain.")

    def set_global_voltage(self,**kwarg):
        """
        Sets a global voltage to a specific value (in V).

        Parameters
        ----------
        kwarg:
            Any name on the list of global voltages as parameter name, followed by the value expected to be set as parameter value (in V).
            e.g. self.set_global_voltage(TH1=1.5)
        """
        for k in kwarg.keys():
            if k in self.VLT_CONF:
                self[k].set_voltage(kwarg[k], unit='V')
                self.SET_VALUE[k]=kwarg[k]
                feedback=[self[k].get_voltage(unit='V'), self[k].get_current(unit='mA')]
                self.logger.info("Set {0:s}={1:.4f} V | Read {2:s}={3:.4f} V ({4:.4f} mA)".format(k, kwarg[k], k, feedback[0], feedback[1]))
            else:
                self.logger.info("{0:s} is not a defined as valid voltage source.".format(k))

    def set_global_current(self,**kwarg):
        """
        Sets a global current to a specific value (in uA).

        Parameters
        ----------
        kwarg:
            Any name on the list of global currents as parameter name, followed by the value expected to be set as parameter value (in uA).
            e.g. self.set_global_current(Iref=-8)
        """
        for k in kwarg.keys():
            if k in self.CRR_CONF:
                self[k].set_current(kwarg[k],unit="uA")
                self.SET_VALUE[k]=kwarg[k]
                feedback=[self[k].get_current(unit='uA'), self[k].get_voltage(unit='V')]
                self.logger.info("Set {0:s}={1:.4f} uA | Read {2:s}={3:.4f} uA ({4:.4f} V)".format(k, kwarg[k], k, feedback[0], feedback[1]))
            else:
                self.logger.info("{0:s} is not a defined as valid current source.".format(k))

    def power_status(self, log=False):
        """
        Returns a dictionary with the overall power status of the chip. 

        Parameters
        ----------
        log: boolean
            A flag to determine if the power_status call is logged.

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
            #pw_status[pwr_id+'[V]'] =  self[pwr_id].get_voltage(unit='V')
            pw_status[pwr_id+"_set"] = self.SET_VALUE[pwr_id]
        if log==True:
            self.logger.info("Power status: {0:s}".format(str(pw_status)))
        return pw_status

    def dac_status(self, log=False):
        """
        Returns a dictionary with the overall status of the global registers and DACs of the chip. 

        Parameters
        ----------
        log: boolean
            A flag to determine if the dac_status call is logged.

        Returns
        ----------
        dac_status: dict
            Dictionary with the DAC values currently set for the configuration of the chip.
            Note: All converted from binary to decimal, except 'EnSRDCol', 'EnMonitorCol', 'InjEnCol' and 'EnColRO'.
        """
        dac_status = {}       
        for dac_id in ['EnPreLd', 'EnMonitorLd', 'EnInjLd', 'TrimLd', 'EnSoDCol', 'EnAnaBuffer', 'DelayROConf',
                    'EnTestPattern', 'EnDataCMOS', 'EnDataLVDS', 
                    'Mon_BLRes', 'Mon_VAmp1', 'Mon_VAmp2',
                    'Mon_VPFB', 'Mon_VPFoll', 'Mon_VNFoll', 'Mon_VNLoad', 'Mon_VPLoad',
                    'Mon_Vsf', 'Mon_TDAC_LSB', 'Mon_Driver', 
                    'BLRes', 'VAmp1', 'VAmp2', 'VPFB', 'VPFoll', 'VNFoll',
                    'VNLoad', 'VPLoad', 'Vsf', 'TDAC_LSB', 'Driver'
                    ]:
            dac_status[dac_id] = int(str(self['CONF_SR'][dac_id]), 2)
        for dac_id in ['EnSRDCol', 'EnMonitorCol', 'InjEnCol', 'EnColRO']:
            dac_status[dac_id] = self['CONF_SR'][dac_id]
        if log==True:
            self.logger.info("Register and DAC status: {0:s}".format(str(dac_status)))
        return dac_status

    def set_th(self, th_id=None, th_value=None):
        """
        Sets a global threshold.

        Parameters
        ----------
        th_id: int or list of int
            Single integer or list of integers corresponding to valid Threshold IDs (i.e. 1, 2 or 3).
        th_value: float or list of floats
            Single float or list of floats corresponding to valid Threshold values (in Volts).
        """
        if isinstance(th_id, int):
            if th_id>0 and th_id<4:
                th_string="TH"+str(th_id)
                th_dict={th_string: th_value}
                self.set_global_voltage(**th_dict)
            else:
                self.logger.info("*{0}* is not a valid Threshold ID. (Only 1, 2 or 3 are valid)".format(th_id))
        elif isinstance(th_id, (list, tuple, np.ndarray)) and len(th_id)>0:
            if len(th_id)==len(th_value):
                for th_pos, th_iter in enumerate(th_id):
                    if isinstance(th_iter, int) and th_iter>0 and th_iter<4:
                        th_string="TH"+str(th_iter)
                        th_dict={th_string: th_value[th_pos]}
                        self.set_global_voltage(**th_dict)
                    else:
                        self.logger.info("*{0}* is not a valid Threshold ID. (Only 1, 2 or 3 are valid)".format(th_iter))  
            else:
                self.logger.info("The number of threshold values does not match the number of threshold IDs.")       
        else:
            self.logger.info("The input was incorrect. It must be either: 1. An integer TH ID and a value, or 2. A list of TH IDs and list of values.") 

    def get_th(self):
        """
        Returns a list of all global thresholds.

        Returns
        ----------
        feedback: list
            A list of all global thresholds: [TH1, TH2, TH3]
        """
        feedback=[self["TH1"].get_voltage(unit='V'), self["TH2"].get_voltage(unit='V'), self["TH3"].get_voltage(unit='V')]
        self.logger.info("Global Thresholds: TH1={0:.4f} V | TH2={1:.4f} V | TH3={2:.4f} V".format(feedback[0], feedback[1], feedback[2]))
        return feedback

    """
    INJECTION
    """
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
        self.logger.info("VHi set to {0:.4f} V".format(VHi))

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
        self.logger.info("Configuring injection: VHi:{0:.4f}, VLo:{1:s}, REPEAT:{2:d}, DELAY:{3:d}, WIDTH:{4:d}, PHASE:{5:d}, External Trigger:{6:d}".format(
        self.SET_VALUE['INJ_HI'], "Set on board", self["inj"]["REPEAT"], self["inj"]["DELAY"], self["inj"]["WIDTH"], inj_phase_des, self["inj"]["EN"]))

    def start_inj(self):
        """
        Starts injection into the chip.
        """
        # Starts injection into the chip.
        self.logger.info("Injecting with parameters: VHi:{0:.4f}, VLo:{1:s}, REPEAT:{2:d}, DELAY:{3:d}, WIDTH:{4:d}, External Trigger:{5:d}".format(
        self.SET_VALUE['INJ_HI'], "Set on board", self["inj"]["REPEAT"], self["inj"]["DELAY"], self["inj"]["WIDTH"], self["inj"]["EN"]))
        self["inj"].start()
        while self["inj"].is_done() != 1:
            time.sleep(0.001)

    """
    GLOBAL AND PIXEL CONFIGURATION
    """
    def _write_global_conf(self):
        """
        Writes to the global configuration.
        (Disables the pixel coonfiguration signal En_Cnfg_Pix and the default configuration Def_Conf )
        """
        self['CONF']['En_Cnfg_Pix'] = 0
        self['CONF'].write()
        self['CONF_SR'].write() 
        while not self['CONF_SR'].is_ready:
            time.sleep(0.001)
        self['CONF']['Def_Conf'] = 0
        self['CONF'].write()

    def set_global_reg(self,**kwarg):
        """
        Sets the specified global configuration registers.

        Parameters
        ----------
        kwarg:
            Any name on the list of global configuration registers as parameter name, followed by the value expected to be set as parameter value.
            e.g. set_global_reg(BLRes=32, VAmp1=35, VPFB=30, VPFoll=15, InjEnCol=0xFFFFFFFFFFFFFF)
            Note for monitors: If a monitor register is set to 1, all others will be disabled. If many are set to 1 at the same time, only the last one
            (in order in the *kwarg) will be set to 1.
        """
        mon_dac_list=['Mon_BLRes', 'Mon_VAmp1', 'Mon_VAmp2',
            'Mon_VPFB', 'Mon_VPFoll', 'Mon_VNFoll', 'Mon_VNLoad', 'Mon_VPLoad',
            'Mon_Vsf', 'Mon_TDAC_LSB', 'Mon_Driver']
        s="Setting registers:"
        flag_last_mon=""
        # Go through kwargs. If kwarg is a valid register name, then modify it. 
        for k in kwarg.keys():
            if k in self.REG_CONF.keys():
                # If a monitor is enabled, disable all the others.
                if k.startswith("Mon_"):
                    if k in mon_dac_list:
                        if kwarg[k]==1:
                            for mon_id in mon_dac_list:
                                self["CONF_SR"][mon_id]=0
                        else:
                            pass
                        self["CONF_SR"][k]=kwarg[k]
                        #self._write_global_conf()
                        flag_last_mon=k
                    else:
                        self.logger.info("The monitor you tried to set ({0}) is not in the provided monitor list.".format(reg_name))
                        pass
                # General change of DAC for non-monitor global registers.
                else:
                    self["CONF_SR"][k] = kwarg[k]
                    s= s + " {0}={1:d}".format(k,kwarg[k])
            else:
                s= s + " {0} is not a valid register name".format(k)
        if flag_last_mon != "":
            s= s + " {0}={1:d}".format(flag_last_mon,kwarg[flag_last_mon])
        else:
            pass
        # Write global configuration
        self._write_global_conf()
        # Update self.REG_CONF
        for field in self["CONF_SR"]._conf['fields']:
            self.REG_CONF[field['name']]=self["CONF_SR"][field['name']]
        # Log registers changed
        self.logger.info(s)

    def _write_pixel_mask(self, bit, mask, bit_pos=0, ro_off=False, overwrite=False):
        #TODO: CHECK FUNCTION
        """
        Writes a mask for pixel configuration.

        Parameters
        ----------
        bit: string
            A string with the name of the mask to be modified in the pixel configuration.
            (Options: "EnPre", "EnInj", "EnMonitor", "Trim")
        mask: numpy.ndarray 
            A numpy.ndarray with binary values of dimensions "self.COL_SIZE X self.ROW_SIZE"
        bit_pos: int
            An integer corresponding to the position of the bit to be configured with the input mask.
        ro_off: boolean
            A flag to determine if the read-out clocks should be turned off while the pixel mask is written. 
        overwrite: boolean
            A flag to determine if the current pixel configuration bits mask should be overwritten by the one given as input.
        """
        if bit=="Trim":
            trim_bits = np.unpackbits(self.PIXEL_CONF["Trim"])
            matrix_trim_in_bits = np.reshape(trim_bits, (self.COL_SIZE, self.ROW_SIZE, 8)).astype(np.bool)
            pixel_conf_bitpos = matrix_trim_in_bits[:, :, 7-bit_pos]
        else:
            signal_bits = np.unpackbits(self.PIXEL_CONF[bit])
            matrix_in_bits = np.reshape(signal_bits, (self.COL_SIZE, self.ROW_SIZE, 8)).astype(np.bool)
            pixel_conf_bitpos = matrix_in_bits[:, :, 7-bit_pos]

        # Turn Read-out related clocks off
        if ro_off:
            ClkBX = self['CONF']['ClkBX'].tovalue()
            ClkOut = self['CONF']['ClkOut'].tovalue()
            self['CONF']['ClkOut'] = 0
            self['CONF']['ClkBX'] = 0
        # Enable the corresponding "...Ld" register (Active Low)
        if bit=="Trim":
            self['CONF_SR']["{0:s}Ld".format(bit)][bit_pos] = 0  # active low
            #print(self['CONF_SR']["{0:s}Ld".format(bit)])
        else:
            ###self['CONF_SR']["{0:s}Ld".format(bit)]= 0  # active low
            self['CONF_SR']["{0:s}Ld".format(bit)][bit_pos] = 0

        # Check if the mask given as input will overwrite completely the current configuration, or only specific values will be written.    
        if overwrite:
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
            if bit=="Trim":
                arg = np.argwhere(pixel_conf_bitpos!= mask)
            else:
                ###arg = np.argwhere(self.PIXEL_CONF[bit]!= mask)
                arg = np.argwhere(pixel_conf_bitpos!= mask)

        # Calculate the double column indexes from the pixels that want to be changed. 
        uni = np.unique(arg[:, 0]//2)
        
        # Wirte the mask per double column. 
        for dcol in uni:
            self['CONF_SR']['EnSRDCol'].setall(False)
            self['CONF_SR']['EnSRDCol'][dcol] = '1'
            #Data going to the global configuration
            self['CONF']['En_Cnfg_Pix'] = 0
            self['CONF'].write()
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
            while not self['CONF_DC'].is_ready:
                time.sleep(0.001)
            self['CONF']['En_Cnfg_Pix'] = 0

        # Disable the in-pixel configuration
        if bit=="Trim":
            self['CONF_SR']["{0:s}Ld".format(bit)][bit_pos] = 1  # active low
            #print(self['CONF_SR']["{0:s}Ld".format(bit)])
            #print ("-----")
        else:
            ###self['CONF_SR']["{0:s}Ld".format(bit)]= 1  # active low
            self['CONF_SR']["{0:s}Ld".format(bit)][bit_pos] = 1  # active low
        self['CONF_SR'].write()
        while not self['CONF_SR'].is_ready:
            time.sleep(0.001)

        # Set the read-out clocks to their original state.
        if ro_off:
            self['CONF']['ClkOut'] = ClkOut  # Readout OFF
            self['CONF']['ClkBX'] = ClkBX
        self['CONF'].write()

        # Update Pixel Configuration.
        if bit=="Trim":
            matrix_trim_in_bits[:, :, 7-bit_pos]=mask
            pixconf_exchanged_bit= np.reshape(np.packbits(matrix_trim_in_bits),(self.COL_SIZE, self.ROW_SIZE))
            self.PIXEL_CONF[bit] = pixconf_exchanged_bit
        else:
            ###self.PIXEL_CONF[bit] = mask
            matrix_in_bits[:, :, 7-bit_pos]=mask
            pixconf_exchanged_bit= np.reshape(np.packbits(matrix_in_bits),(self.COL_SIZE, self.ROW_SIZE))
            self.PIXEL_CONF[bit] = pixconf_exchanged_bit

    def _create_mask(self, pix):
        """
        Creates a mask of the same dimensions as the chip's dimensions.

        Parameters
        ----------
        pix: string OR list OR tuple OR np.ndarray
            - valid strings as input: "all" (all 1s) or "none" (all 0s)
            - list, tuple or np.ndarray:
                - Single pixel: e.g. pix=[20,60]
                - Matrix of the same dimensions as the chip
                - A list of pixels: e.g. pix=[[20,60],[20,61],[20,62]]
        """        
        mask = np.empty([self.COL_SIZE, self.ROW_SIZE])
        mask.fill(np.NaN)
        # A string as input: "all" (all 1s) or "none" (all 0s)
        if isinstance(pix, str):
            if pix == "all":
                mask.fill(1)
            elif pix == "none":
                mask.fill(0)
            else:
                pass
        # A list, tuple or np.ndarray as input
        elif isinstance(pix, (list, tuple, np.ndarray)):
            mask.fill(0)
            # Single pixel format: e.g. pix=[20,60]
            if isinstance(pix[0], int):
                mask[pix[0], pix[1]] = 1
            # A matrix of the same dimensions as the chip
            elif len(pix) == self.COL_SIZE and len(pix[0]) == self.ROW_SIZE:
                mask[:, :] = np.array(pix, np.bool)
            # A list of pixels: e.g. pix=[[20,60],[20,61],[20,62]]
            else:
                for p in pix:
                    if len(p)==2 and isinstance(p[0], int) and isinstance(p[1], int):
                        mask[p[0], p[1]] = 1
                    else: 
                        self.logger.info("The listed item {0:s} does not correspond to a valid pixel format.".format(p))
                        mask.fill(np.NaN)
                        break
        else:
            self.logger.info("You have not specified a valid input for mask creation. Please check the code documentation.")
        return mask

    def set_preamp_en(self, pix="all", EnColRO="auto", Out='autoCMOS'):
        #TODO: Check after write_pixel_mask
        mask = self._create_mask(pix)
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
        self['CONF']['Rst'] = 1
        self['CONF'].write()
        time.sleep(0.001)
        self['CONF']['Rst'] = 0
        self['CONF'].write()

    def set_mon_en(self, pix="none", overwrite=False):
        """
        Creates a mask based on the pixels given as parameter and writes it to the chip in order to enable MONITOR.

        Parameters
        ----------
        pix: string OR list OR tuple OR np.ndarray
            - valid strings as input: "all" (all 1s) or "none" (all 0s)
            - list, tuple or np.ndarray:
                - Single pixel: e.g. pix=[20,60]
                - Matrix of the same dimensions as the chip
                - A list of pixels: e.g. pix=[[20,60],[20,61],[20,62]]
        overwrite: boolean
            A flag to determine if the current pixel configuration bits mask should be overwritten by the one given as input.
        """   
        mask = self._create_mask(pix)
        self['CONF_SR']['EnMonitorCol'].setall(False)
        for i in range(self.COL_SIZE):
            self['CONF_SR']['EnMonitorCol'][i] = bool(np.any(mask[i,:]))
        self._write_pixel_mask(bit="EnMonitor", mask=mask, overwrite=overwrite)
      
        arg = np.argwhere(self.PIXEL_CONF["EnMonitor"][:, :])
        self.logger.info("Enabling Monitor for {0:d} pixels:  {1:s}".format(len(arg), str(arg).replace("\n", " ")))

    def set_inj_en(self, pix="none", overwrite=False):
        """
        Creates a mask based on the pixels given as parameter and writes it to the chip in order to enable INJECTION.

        Parameters
        ----------
        pix: string OR list OR tuple OR np.ndarray
            - valid strings as input: "all" (all 1s) or "none" (all 0s)
            - list, tuple or np.ndarray:
                - Single pixel: e.g. pix=[20,60]
                - Matrix of the same dimensions as the chip
                - A list of pixels: e.g. pix=[[20,60],[20,61],[20,62]]
        overwrite: boolean
            A flag to determine if the current pixel configuration bits mask should be overwritten by the one given as input.
        """   
        mask = self._create_mask(pix)
        self['CONF_SR']['InjEnCol'].setall(True)
        for i in range(self.COL_SIZE):
            # The mask is negative as InjEnCol is active Low, unlike EnColRO or EnMonitorCol
            self['CONF_SR']['InjEnCol'][i] = not bool(np.any(mask[i,:]))
        self._write_pixel_mask(bit="EnInj",mask=mask, overwrite=overwrite)
        
        arg = np.argwhere(self.PIXEL_CONF["EnInj"][:,:])
        self.logger.info("Enabling Injection for {0:d} pixels: {1:s}".format(len(arg), str(arg).replace("\n", " ")))
        
    def set_tdac(self, tdac):
        #TODO: Maybe better to make this function write all the bit masks only after all four have been changed, and not one by one. 
        """
        Writes the 4-bit mask of trim values to the whole pixel matrix.

        Parameters
        ----------
        tdac: int or np.ndarray
            A single trim value to be written to the whole matrix, or a specific matrix with the same dimensions as the chip and every single value to be written.
        """     
        mask = np.copy(self.PIXEL_CONF["Trim"])
        if isinstance(tdac, int):
            mask.fill(tdac)
            self.logger.info("Setting a single TDAC/TRIM value to all pixels: {0:s}".format(str(tdac)))
        elif np.shape(tdac) == np.shape(mask):
            self.logger.info("set_tdac: matrix")
            mask = np.array(tdac, dtype=np.uint8)
        else:
            self.logger.error("The input tdac parameter must be int or array of size [{0:d},{1:d}]".format(self.COL_SIZE, self.ROW_SIZE))
            return 

        # Unpack the mask as 8 different masks, where the first 4 masks correspond to the 4 Trim bits.
        trim_bits = np.unpackbits(mask)
        trim_bits_array = np.reshape(trim_bits, (self.COL_SIZE, self.ROW_SIZE, 8)).astype(np.bool)
        # Write the mask for every trim bit.
        for bit in range(4):
            trim_bits_sel_mask = trim_bits_array[:, :, 7-bit]
            self._write_pixel_mask(bit='Trim', mask=trim_bits_sel_mask, bit_pos=bit)

    def get_conf_sr(self, mode='mwr'):
        #TODO: Check if this is properly implemented
        """ 
        Writes/reads registers in to the chip.

        Parameters
        ----------
        mode: string
            'w' get values in FPGA write register (output to SI_CONF)
            'r' get values in FPGA read register (input from SO_CONF)
            'm' get values in cpu memory (data in self['CONF_SR'])
            'mrw' get allmask
        Returns
        ----------
        data: dict
            A dictionary containing the size of CONF_SR, the array of bits written and read to the chip and the values stored in CPU memory.
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
            data["read_reg"] = basil.RL.StdRegister.StdRegister(None, self["CONF_SR"]._conf)
            data["read_reg"][:] = r[size-1::-1]
        if "m" in mode:
           data["memory"] = basil.RL.StdRegister.StdRegister(None, self["CONF_SR"]._conf)
           data["memory"][:] = self["CONF_SR"][:].copy()
        return data

    """
    READ-OUT AND OUTPUT DATA HANDLING
    """
    def get_data_now(self):
        """
        Returns current data on the FIFO.
        """  
        return self['fifo'].get_data()

    def get_data(self, wait=0.2):
        """
        Returns data on the FIFO generated by injected pulses.
        
        Parameters
        ----------
        wait: float
            Period of time (in seconds) between the last injection and read-out of the last batch of data.
        
        Return
        ----------
        raw: numpy.ndarray 
            Read-out data
        """  
        self["inj"].start()
        i = 0
        raw = np.empty(0,dtype='uint32')
        while self["inj"].is_done() != 1:
            time.sleep(0.001)
            raw = np.append(raw, self['fifo'].get_data())
            #print("=====sim===== get_data len",len(raw),self["inj"].is_done())
            i = i+1
            if i > 10000:
                break
        for i in range(10):
            pass
            #print("=====sim===== get_data len", i, len(raw),self["inj"].is_done())
        time.sleep(wait)
        raw = np.append(raw, self['fifo'].get_data())
        if i > 10000:
            self.logger.info("get_data: error timeout len={0:d}".format(len(raw)))
        lost_cnt = self["data_rx"]["LOST_COUNT"]
        if self["data_rx"]["LOST_COUNT"]!=0:
            self.logger.warn("get_data: error cnt={0:d}".format(lost_cnt))      
        return raw

    def reset_monoread(self, wait=0.001, sync_timestamp=True, bcid_only=True):
        """
        Resets the read-out of the chip.
        
        Parameters
        ----------
        wait: float
            Period of time (in seconds) that the function waits before changing back the state of the reset.
        sync_timestamp: boolean
            A flag to synchronize the bunch crossing counter reset with timestamp reset.
        bcid_only: boolean
            A flag to signal if just the the bunch crossing counter is reset, or the in-pixel logic too. (False: Both are reset)
        """  
        self['CONF']['ResetBcid_WITH_TIMESTAMP'] = sync_timestamp

        if not bcid_only:
            self['CONF']['Rst'] = 1
        else:
            self['CONF']['Rst'] = 0

        self['CONF']['ResetBcid'] = 1
        self['CONF'].write()

        if not bcid_only:
            time.sleep(wait)
            self['CONF']['Rst'] = 0
            self['CONF'].write()
        else:
            pass
        time.sleep(wait)

        self['CONF']['ResetBcid'] = 0
        self['CONF'].write()

    def set_monoread(self, start_freeze=90, start_read=90+2, stop_read=90+2+2,
                     stop_freeze=90+40, stop=90+40+24, read_shift=(27+4)*2,
                     sync_timestamp=True, decode=True):
        """
        Enables the read-out of the chip.

        Parameters
        ----------
        start_freeze: int
            Time (in clocks) between the rising edge of Token and rising edge of Freeze.
        start_read: int
            Time (in clocks) between the rising edge of Token and rising edge of Read.
        stop_read: int
            Time (in clocks) between the rising edge of Token and falling edge of Read.
        stop_freeze: int
            Time (in clocks) between the rising edge of Token and falling edge of Freeze.
        stop: int
            ....
        read_shift: int
            Time (in clocks) between the rising edge of Read and falling edge of Freeze.
            Condition: > 62
        sync_timestamp: boolean
            A flag to synchronize the bunch crossing counter reset with timestamp reset.
        decode: boolean
            A flag to disable (or not) the gray decoder. (False: Disable gray decoder)
        read_shift>54 
        """
        # Save initial global threshold values and set all global thresholds to a very high value.
        current_th=[self.SET_VALUE["TH1"],self.SET_VALUE["TH2"],self.SET_VALUE["TH3"]]
        self.set_th([1,2,3], [1.5,1.5,1.5])
        # Reset read-out module of the.
        self['data_rx'].reset()
        self['data_rx'].READ_SHIFT = read_shift
        self['data_rx'].CONF_START_FREEZE = start_freeze
        self['data_rx'].CONF_START_READ = start_read
        self['data_rx'].CONF_STOP_FREEZE = stop_freeze
        self['data_rx'].CONF_STOP_READ = stop_read
        self['data_rx'].CONF_STOP = stop
        self['data_rx'].DISSABLE_GRAY_DECODER = not decode
        self['data_rx'].FORCE_READ = 0 
        # Set switches.
        self['CONF']['ClkBX'] = 1
        self['CONF']['ClkOut'] = 1
        # Reset read-out.
        self.reset_monoread(wait=0.001, sync_timestamp=sync_timestamp, bcid_only=False)
        # Set initial threshold values of all global thresholds.
        self.set_th([1,2,3], current_th)
        # Reset FIFO
        self["fifo"]["RESET"]   # If 'fifo' type: sitcp_fifo 
        #self['fifo'].reset()   # If 'fifo' type: sram_fifo
        #Read-out trash data from the chip
        self['data_rx'].set_en(True)
        time.sleep(0.2)
        self.logger.info('Setting Monopix Read-out: start_freeze={0:d} start_read={1:d} stop_read={2:0} stop_freeze={3:0} stop={4:0} reset_fifo={5:0}'.format(
                     start_freeze, start_read, stop_read, stop_freeze, stop, self['fifo'].get_FIFO_SIZE()))
        # Reset FIFO
        self["fifo"]["RESET"]   # If 'fifo' type: sitcp_fifo 
        #self['fifo'].reset()   # If 'fifo' type: sram_fifo
        
    def stop_monoread(self):
        """
        Stops the read-out of the chip.

        Returns
        ----------
        lost_cnt: int
            Number of hits not read-out when the read-out was stopped.
        """
        self['data_rx'].set_en(False)
        lost_cnt=self["data_rx"]["LOST_COUNT"]
        if lost_cnt != 0:
            self.logger.warn("stop_monoread: error cnt={0:d}".format(lost_cnt))
        #exp=self["data_rx"]["EXPOSURE_TIME"]
        self.logger.info("stop_monoread:lost_cnt={0:d}".format(lost_cnt))
        self['CONF']['Rst'] = 1
        self['CONF']['ResetBcid'] = 1
        self['CONF']['ClkOut'] = 0
        self['CONF']['ClkBX'] = 0
        self['CONF'].write()
        return lost_cnt

    def set_tlu(self,tlu_delay=8):
        """
        Enables and configures the TLU (Trigger Logic Unit).

        Parameters
        ----------
        tlu_delay: int
            Delay value to be set to the TLU (For regular cable lenghts 7 or 8 are reliable values)
        """
        self.dut["tlu"]["RESET"]=1
        self.dut["tlu"]["TRIGGER_MODE"]=3
        self.dut["tlu"]["EN_TLU_VETO"]=0
        self.dut["tlu"]["MAX_TRIGGERS"]=0
        self.dut["tlu"]["TRIGGER_COUNTER"]=0
        self.dut["tlu"]["TRIGGER_LOW_TIMEOUT"]=0
        self.dut["tlu"]["TRIGGER_VETO_SELECT"]=0
        self.dut["tlu"]["TRIGGER_THRESHOLD"]=0
        self.dut["tlu"]["DATA_FORMAT"]=2
        self.dut["tlu"]["TRIGGER_HANDSHAKE_ACCEPT_WAIT_CYCLES"]=20
        self.dut["tlu"]["TRIGGER_DATA_DELAY"]=tlu_delay
        self.dut["tlu"]["TRIGGER_SELECT"]=0
        self.logger.info("Setting TLU with a delay of {0:d}".format(tlu_delay))
        self.dut["tlu"]["TRIGGER_ENABLE"]=1    
        
    def stop_tlu(self):
        """
        Disables the TLU (Trigger Logic Unit).
        """
        self.dut["tlu"]["TRIGGER_ENABLE"]=0

    def set_timestamp640(self, src="tlu"):
        """
        Configures one specific timestamp640 module (sampling at the FPGA level with a 640 MHz clock)

        Parameters
        ----------
        src: string
            "tlu" (TLU sampling in 640 MHz), 
            "inj" (Injection sampling in 640 MHz),
            "rx1" (Sampling of the RX1 lemo input of the MIO3 in 640 MHz) 
            "mon" (Sampling of the monitor output in 640 MHz) ???
        """
        self["timestamp_{0:s}".format(src)].reset()
        self["timestamp_{0:s}".format(src)]["EXT_TIMESTAMP"] = True
        if src == "tlu":
                self["timestamp_tlu"]["INVERT"] = 1
                self["timestamp_tlu"]["ENABLE_TRAILING"] = 0
                self["timestamp_tlu"]["ENABLE"] = 0
                self["timestamp_tlu"]["ENABLE_EXTERN"] = 1
        elif src == "inj":
                self["timestamp_inj"]["ENABLE_EXTERN"] = 0  # although this is connected to gate
                self["timestamp_inj"]["INVERT"] = 0
                self["timestamp_inj"]["ENABLE_TRAILING"] = 0
                self["timestamp_inj"]["ENABLE"] = 1
        elif src == "rx1":
                self["timestamp_rx1"]["INVERT"] = 1
                self["timestamp_rx1"]["ENABLE_EXTERN"] = 0  # connected to 1'b1
                self["timestamp_rx1"]["ENABLE_TRAILING"] = 0
                self["timestamp_rx1"]["ENABLE"] = 1
        elif src == "mon":  
                self["timestamp_mon"]["INVERT"] = 1
                self["timestamp_mon"]["ENABLE_TRAILING"] = 1
                self["timestamp_mon"]["ENABLE_EXTERN"] = 0
                self["timestamp_mon"]["ENABLE"] = 1
        else: 
            self.logger.warning("*{0:s}* is not a valid input that can be sampled with a 640 MHz clock.".format(src))
            return
        self.logger.info("640 MHz sampling enabled for: timestamp_{0:s} with INVERT={1:i}, ENABLE_EXTERN={2:i}, ENABLE_TRAILING={3:i}, ENABLE={4:i}".format(
            src, self["timestamp_{0:s}".format(src)]["INVERT"], self["timestamp_{0:s}".format(src)]["ENABLE_EXTERN"], 
            self["timestamp_{0:s}".format(src)]["ENABLE_TRAILING"], self["timestamp_{0:s}".format(src)]["ENABLE"]))
        
    def stop_timestamp640(self, src="tlu"):
        """
        Disables one specific timestamp640 module (sampling at the FPGA level with a 640 MHz clock)

        Parameters
        ----------
        src: string
            "tlu" (TLU sampling in 640 MHz), 
            "inj" (Injection sampling in 640 MHz),
            "rx1" (Sampling of the RX1 lemo input of the MIO3 in 640 MHz) 
            "mon" (Sampling of the monitor output in 640 MHz) ???
        """
        self["timestamp_{0:s}".format(src)]["ENABLE_EXTERN"] = 0
        self["timestamp_{0:s}".format(src)]["ENABLE"]=0
        lost_cnt=self["timestamp_{0:s}".format(src)]["LOST_COUNT"]
        self.logger.info("640 MHz sampling disabled for: timestamp_{0:s} (lost_cnt={1:d})".format(src, lost_cnt))

    def stop_all_data(self):
        """
        Stops all chip and module data coming out of the device.
        """
        self.stop_tlu()
        self.stop_monoread()
        self.stop_timestamp640("tlu")
        self.stop_timestamp640("inj")
        self.stop_timestamp640("rx1")
        self.stop_timestamp640("mon")

    """
    TEMPERATURE READING
    """
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
