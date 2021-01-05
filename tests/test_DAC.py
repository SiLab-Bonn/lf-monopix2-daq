#
# ------------------------------------------------------------
# Copyright (c) All rights reserved
# SiLab, Institute of Physics, University of Bonn
# ------------------------------------------------------------
#
from __future__ import print_function
import unittest
import os
from monopix2_daq.sim.utils import cocotb_compile_and_run, cocotb_compile_clean
import sys
import yaml
import time
import bitarray
import numpy as np
import csv
import random
import monopix2_daq.monopix2 as monopix2
import monopix2_daq.analysis.interpreter_idx as interpreter
import test_Monopix2

class TestDAC(test_Monopix2.TestMonopix2):

    def test_00init(self):
        self.dut.init()
        ### set init values from yaml
        self.dut['CONF']['Ld_DAC'] = 1
        self.dut['CONF'].write()
        self.dut['CONF_SR'].write() 
        i=0
        t0=time.time()
        while not self.dut['CONF_SR'].is_ready:
            i=i+1
        print("=====sim===== CONF_SR {0:.2f}s,{1:d}".format(time.time()-t0,i))
        self.dut['CONF']['Ld_DAC'] = 0

        #############################
        ## set readout, injection
        #self.dut.set_inj_all(inj_n=1,inj_width=40,inj_delay=100)
        #self.dut.set_timestamp640(src="mon")
        #self.dut.set_monoread(sync_timestamp=False)

    @unittest.skip('skip')
    def test_01init(self):
        ######################## 
        ### set values from yaml file
        
        self.assertEqual(self.dut["tb"].DAC_BLRES,self.dut["CONF_SR"]._conf["init"]["BLRes"])
        self.assertEqual(self.dut["tb"].DAC_VAMP1, self.dut["CONF_SR"]._conf["init"]["VAmp1"])
        self.assertEqual(self.dut["tb"].DAC_VAMP2, self.dut["CONF_SR"]._conf["init"]["VAmp2"])
        self.assertEqual(self.dut["tb"].DAC_VPFB,self.dut["CONF_SR"]._conf["init"]["VPFB"])
        self.assertEqual(self.dut["tb"].DAC_VNFOLL,self.dut["CONF_SR"]._conf["init"]["VNFoll"])
        self.assertEqual(self.dut["tb"].DAC_VPFOLL,self.dut["CONF_SR"]._conf["init"]["VPFoll"])
        self.assertEqual(self.dut["tb"].DAC_VNLOAD,  self.dut["CONF_SR"]._conf["init"]["VNLoad"])
        self.assertEqual(self.dut["tb"].DAC_VPLOAD,  self.dut["CONF_SR"]._conf["init"]["VPLoad"])
        self.assertEqual(self.dut["tb"].DAC_TDAC_LSB,self.dut["CONF_SR"]._conf["init"]["TDAC_LSB"])
        self.assertEqual(self.dut["tb"].DAC_VSF,  self.dut["CONF_SR"]._conf["init"]["Vsf"])
        self.assertEqual(self.dut["tb"].DAC_DRIVER,  self.dut["CONF_SR"]._conf["init"]["Driver"])
        self.assertEqual(self.dut["tb"].MON_VSF,  self.dut["CONF_SR"]._conf["init"]["Mon_Vsf"])
        self.assertEqual(self.dut["tb"].MON_VPFB, self.dut["CONF_SR"]._conf["init"]["Mon_VPFB"])
        self.assertEqual(self.dut["tb"].MON_VNLOAD,self.dut["CONF_SR"]._conf["init"]["Mon_VNLoad"])
        self.assertEqual(self.dut["tb"].MON_VNLOAD,self.dut["CONF_SR"]._conf["init"]["Mon_VPLoad"])
        self.assertEqual(self.dut["tb"].MON_VNFOLL,self.dut["CONF_SR"]._conf["init"]["Mon_VNFoll"])
        self.assertEqual(self.dut["tb"].MON_VPFOLL, self.dut["CONF_SR"]._conf["init"]["Mon_VPFoll"])
        self.assertEqual(self.dut["tb"].MON_VAMP1,self.dut["CONF_SR"]._conf["init"]["Mon_VAmp1"])
        self.assertEqual(self.dut["tb"].MON_VAMP2, self.dut["CONF_SR"]._conf["init"]["Mon_VAmp2"])        
        self.assertEqual(self.dut["tb"].MON_TDAC_LSB,self.dut["CONF_SR"]._conf["init"]["Mon_TDAC_LSB"])
        self.assertEqual(self.dut["tb"].MON_BLRES,self.dut["CONF_SR"]._conf["init"]["Mon_BLRes"])
        self.assertEqual(self.dut["tb"].MON_DRIVER,self.dut["CONF_SR"]._conf["init"]["Mon_Driver"])
        self.assertEqual(self.dut["tb"].ENANABUFFER,self.dut["CONF_SR"]._conf["init"]["EnAnaBuffer"])
        self.assertEqual(int(self.dut["tb"].get_EnDataCMOS()), self.dut["CONF_SR"]._conf["init"]["EnDataCMOS"])
        self.assertEqual(int(self.dut["tb"].get_EnDataLVDS()), self.dut["CONF_SR"]._conf["init"]["EnDataLVDS"])

        self.assertEqual(self.dut["tb"].ENMONITORCOL, self.dut["CONF_SR"]._conf["init"]["EnMonitorCol"])

    @unittest.skip('skip')
    def test_02default(self):
        ##############
        ## set defualt 
        self.dut['CONF']['Def_Conf'] = 1
        self.dut['CONF'].write()

        self.assertEqual(self.dut["tb"].DAC_BLRES,32)
        self.assertEqual(self.dut["tb"].DAC_VAMP1, 35)
        self.assertEqual(self.dut["tb"].DAC_VAMP2, 35)
        self.assertEqual(self.dut["tb"].DAC_VPFB,30)
        self.assertEqual(self.dut["tb"].DAC_VNFOLL,15)
        self.assertEqual(self.dut["tb"].DAC_VPFOLL,15)
        self.assertEqual(self.dut["tb"].DAC_VNLOAD,13)
        self.assertEqual(self.dut["tb"].DAC_VPLOAD,7)
        self.assertEqual(self.dut["tb"].DAC_VSF,32)
        self.assertEqual(self.dut["tb"].DAC_TDAC_LSB,12)
        self.assertEqual(self.dut["tb"].DAC_DRIVER,32)
        self.assertEqual(self.dut["tb"].MON_VSF,0)
        self.assertEqual(self.dut["tb"].MON_VPFB,0)
        self.assertEqual(self.dut["tb"].MON_VNLOAD,0)
        self.assertEqual(self.dut["tb"].MON_VPLOAD,0)
        self.assertEqual(self.dut["tb"].MON_VNFOLL,0)
        self.assertEqual(self.dut["tb"].MON_VPFOLL,0)
        self.assertEqual(self.dut["tb"].MON_VAMP1,1)
        self.assertEqual(self.dut["tb"].MON_VAMP2,0)        
        self.assertEqual(self.dut["tb"].MON_TDAC_LSB,0)
        self.assertEqual(self.dut["tb"].MON_BLRES,0)
        self.assertEqual(self.dut["tb"].MON_DRIVER,0)
        self.assertEqual(self.dut["tb"].ENANABUFFER,1)
        self.assertEqual(int(self.dut["tb"].get_EnDataCMOS()), 1)
        self.assertEqual(int(self.dut["tb"].get_EnDataLVDS()), 0)
        self.assertEqual(self.dut["tb"].ENMONITORCOL, 0)

        ##### disable default value
        self.dut['CONF']['Def_Conf'] = 0
        self.dut['CONF'].write()
        self.assertEqual(self.dut["tb"].DAC_BLRES,self.dut["CONF_SR"]._conf["init"]["BLRes"])
        self.assertEqual(self.dut["tb"].DAC_VAMP1, self.dut["CONF_SR"]._conf["init"]["VAmp1"])
        self.assertEqual(self.dut["tb"].DAC_VAMP2, self.dut["CONF_SR"]._conf["init"]["VAmp2"])
        self.assertEqual(self.dut["tb"].DAC_VPFB,self.dut["CONF_SR"]._conf["init"]["VPFB"])
        self.assertEqual(self.dut["tb"].DAC_VNFOLL,self.dut["CONF_SR"]._conf["init"]["VNFoll"])
        self.assertEqual(self.dut["tb"].DAC_VPFOLL,self.dut["CONF_SR"]._conf["init"]["VPFoll"])
        self.assertEqual(self.dut["tb"].DAC_VNLOAD,  self.dut["CONF_SR"]._conf["init"]["VNLoad"])
        self.assertEqual(self.dut["tb"].DAC_VPLOAD,  self.dut["CONF_SR"]._conf["init"]["VPLoad"])
        self.assertEqual(self.dut["tb"].DAC_TDAC_LSB,self.dut["CONF_SR"]._conf["init"]["TDAC_LSB"])
        self.assertEqual(self.dut["tb"].DAC_VSF,  self.dut["CONF_SR"]._conf["init"]["Vsf"])
        self.assertEqual(self.dut["tb"].DAC_DRIVER,  self.dut["CONF_SR"]._conf["init"]["Driver"])
        self.assertEqual(self.dut["tb"].MON_VSF,  self.dut["CONF_SR"]._conf["init"]["Mon_Vsf"])
        self.assertEqual(self.dut["tb"].MON_VPFB, self.dut["CONF_SR"]._conf["init"]["Mon_VPFB"])
        self.assertEqual(self.dut["tb"].MON_VNLOAD,self.dut["CONF_SR"]._conf["init"]["Mon_VNLoad"])
        self.assertEqual(self.dut["tb"].MON_VPLOAD,self.dut["CONF_SR"]._conf["init"]["Mon_VPLoad"])
        self.assertEqual(self.dut["tb"].MON_VNFOLL,self.dut["CONF_SR"]._conf["init"]["Mon_VNFoll"])
        self.assertEqual(self.dut["tb"].MON_VPFOLL, self.dut["CONF_SR"]._conf["init"]["Mon_VPFoll"])
        self.assertEqual(self.dut["tb"].MON_VAMP1,self.dut["CONF_SR"]._conf["init"]["Mon_VAmp1"])
        self.assertEqual(self.dut["tb"].MON_VAMP2, self.dut["CONF_SR"]._conf["init"]["Mon_VAmp2"])        
        self.assertEqual(self.dut["tb"].MON_TDAC_LSB,self.dut["CONF_SR"]._conf["init"]["Mon_TDAC_LSB"])
        self.assertEqual(self.dut["tb"].MON_BLRES,self.dut["CONF_SR"]._conf["init"]["Mon_BLRes"])
        self.assertEqual(self.dut["tb"].MON_DRIVER,self.dut["CONF_SR"]._conf["init"]["Mon_Driver"])
        self.assertEqual(self.dut["tb"].ENANABUFFER,self.dut["CONF_SR"]._conf["init"]["EnAnaBuffer"])
        self.assertEqual(int(self.dut["tb"].get_EnDataCMOS()), self.dut["CONF_SR"]._conf["init"]["EnDataCMOS"])
        self.assertEqual(int(self.dut["tb"].get_EnDataLVDS()), self.dut["CONF_SR"]._conf["init"]["EnDataLVDS"])
        self.assertEqual(self.dut["tb"].ENMONITORCOL, self.dut["CONF_SR"]._conf["init"]["EnMonitorCol"])
    
    @unittest.skip('skip')   
    def test_03random(self):
        ###############
        ## set random value but Def_Conf=1
        set_values={}
        for dac_name in ["BLRes", "VAmp1", "VAmp2", "VPFB", "VNFoll", "VPFoll", "VNLoad", "VPLoad", "TDAC_LSB", "Vsf", "Driver"]:
             set_values[dac_name] = random.randint(0,0x3F)
             set_values["Mon_{0:s}".format(dac_name)] = 0
        set_values["Mon_TDAC_LSB"] = 1
        for dac_name in set_values.keys():
             self.dut['CONF_SR'][dac_name] = set_values[dac_name]
        set_values["EnAnaBuffer"]=0
        self.dut["CONF_SR"]["EnAnaBuffer"] = set_values["EnAnaBuffer"]
        set_values["EnDataCMOS"]=0
        self.dut["CONF_SR"]["EnDataCMOS"] = set_values["EnDataCMOS"]
        set_values["EnDataLVDS"] = 1
        self.dut["CONF_SR"]["EnDataLVDS"] = set_values["EnDataLVDS"]
        set_values["EnMonitorCol"] = random.randint(0,0xFFFFFFFFFFFFFF)
        self.dut["CONF_SR"]["EnMonitorCol"] = set_values["EnMonitorCol"]

        self.dut['CONF']['Def_Conf'] = 1
        self.dut['CONF']['Ld_DAC'] = 1
        self.dut['CONF'].write()
        self.dut['CONF_SR'].write() 
        while not self.dut['CONF_SR'].is_ready:
            pass
        self.dut['CONF']['Ld_DAC'] = 0

        self.assertEqual(self.dut["tb"].DAC_BLRES, 32)
        self.assertEqual(self.dut["tb"].DAC_VAMP1, 35)
        self.assertEqual(self.dut["tb"].DAC_VAMP2, 35)
        self.assertEqual(self.dut["tb"].DAC_VPFB, 30)
        self.assertEqual(self.dut["tb"].DAC_VNFOLL, 15)
        self.assertEqual(self.dut["tb"].DAC_VPFOLL, 15)
        self.assertEqual(self.dut["tb"].DAC_VNLOAD, 13)
        self.assertEqual(self.dut["tb"].DAC_VPLOAD, 7)
        self.assertEqual(self.dut["tb"].DAC_VSF, 32)
        self.assertEqual(self.dut["tb"].DAC_TDAC_LSB, 12)
        self.assertEqual(self.dut["tb"].DAC_DRIVER, 32)
        self.assertEqual(self.dut["tb"].MON_VSF, 0)
        self.assertEqual(self.dut["tb"].MON_VPFB, 0)
        self.assertEqual(self.dut["tb"].MON_VNLOAD, 0)
        self.assertEqual(self.dut["tb"].MON_VPLOAD, 0)
        self.assertEqual(self.dut["tb"].MON_VNFOLL, 0)
        self.assertEqual(self.dut["tb"].MON_VPFOLL, 0)
        self.assertEqual(self.dut["tb"].MON_VAMP1, 1)
        self.assertEqual(self.dut["tb"].MON_VAMP2, 0)        
        self.assertEqual(self.dut["tb"].MON_TDAC_LSB, 0)
        self.assertEqual(self.dut["tb"].MON_BLRES, 0)
        self.assertEqual(self.dut["tb"].MON_DRIVER, 0)
        self.assertEqual(self.dut["tb"].ENANABUFFER, 1)
        self.assertEqual(int(self.dut["tb"].get_EnDataCMOS()), 1)
        self.assertEqual(int(self.dut["tb"].get_EnDataLVDS()), 0)
        self.assertEqual(self.dut["tb"].ENMONITORCOL, 0)

        ###############
        ## Def_Conf=0 expecting random numbers
        self.dut['CONF']['Def_Conf'] = 0
        self.dut['CONF'].write()

        self.assertEqual(self.dut["tb"].DAC_BLRES, set_values["BLRes"])
        self.assertEqual(self.dut["tb"].DAC_VAMP1, set_values["VAmp1"])
        self.assertEqual(self.dut["tb"].DAC_VAMP2, set_values["VAmp2"])
        self.assertEqual(self.dut["tb"].DAC_VPFB, set_values["VPFB"])
        self.assertEqual(self.dut["tb"].DAC_VNFOLL, set_values["VNFoll"])
        self.assertEqual(self.dut["tb"].DAC_VPFOLL, set_values["VPFoll"])
        self.assertEqual(self.dut["tb"].DAC_VNLOAD, set_values["VNLoad"])
        self.assertEqual(self.dut["tb"].DAC_VPLOAD, set_values["VPLoad"])
        self.assertEqual(self.dut["tb"].DAC_TDAC_LSB, set_values["TDAC_LSB"])
        self.assertEqual(self.dut["tb"].DAC_VSF, set_values["Vsf"])
        self.assertEqual(self.dut["tb"].DAC_DRIVER, set_values["Driver"])
        self.assertEqual(self.dut["tb"].MON_BLRES, set_values["Mon_BLRes"])
        self.assertEqual(self.dut["tb"].MON_VAMP1, set_values["Mon_VAmp1"])
        self.assertEqual(self.dut["tb"].MON_VAMP2, set_values["Mon_VAmp2"])
        self.assertEqual(self.dut["tb"].MON_VPFB, set_values["Mon_VPFB"])
        self.assertEqual(self.dut["tb"].MON_VNFOLL, set_values["Mon_VNFoll"])
        self.assertEqual(self.dut["tb"].MON_VPFOLL, set_values["Mon_VPFoll"])
        self.assertEqual(self.dut["tb"].MON_VNLOAD, set_values["Mon_VNLoad"])   
        self.assertEqual(self.dut["tb"].MON_VPLOAD, set_values["Mon_VPLoad"])      
        self.assertEqual(self.dut["tb"].MON_TDAC_LSB, set_values["Mon_TDAC_LSB"])
        self.assertEqual(self.dut["tb"].MON_VSF, set_values["Mon_Vsf"])
        self.assertEqual(self.dut["tb"].MON_DRIVER, set_values["Mon_Driver"])
        self.assertEqual(self.dut["tb"].ENANABUFFER, set_values["EnAnaBuffer"])
        self.assertEqual(int(self.dut["tb"].get_EnDataCMOS()), set_values["EnDataCMOS"])
        self.assertEqual(int(self.dut["tb"].get_EnDataLVDS()), set_values["EnDataLVDS"])
        self.assertEqual(self.dut["tb"].ENMONITORCOL, set_values["EnMonitorCol"])

    @unittest.skip('skip')
    def test_04All0(self):
        #######
        ## set all 0 but only Ld_Cnfg=1
        set_values={}
        for dac_name in ["BLRes","VAmp1","VAmp2","VPFB","VNFoll","VPFoll","VPLoad","VNLoad","TDAC_LSB","Vsf","Driver"]:
             set_values[dac_name]=self.dut['CONF_SR'][dac_name].tovalue()
             set_values["Mon_{0:s}".format(dac_name)]=self.dut['CONF_SR']["Mon_{0:s}".format(dac_name)].tovalue()
        for dac_name in ["EnAnaBuffer","EnDataCMOS","EnDataLVDS","EnMonitorCol"]:
            set_values[dac_name]=self.dut['CONF_SR'][dac_name].tovalue()
        self.dut['CONF_SR'].setall(False)
        self.dut['CONF']['Ld_Cnfg'] = 1
        self.dut['CONF'].write()
        self.dut['CONF_SR'].write() 
        while not self.dut['CONF_SR'].is_ready:
            pass
        self.dut['CONF']['Ld_Cnfg'] = 0
        self.dut['CONF'].write()

        self.assertEqual(self.dut["tb"].DAC_BLRES,set_values["BLRes"])
        self.assertEqual(self.dut["tb"].DAC_VAMP1, set_values["VAmp1"])
        self.assertEqual(self.dut["tb"].DAC_VAMP2, set_values["VAmp2"])
        self.assertEqual(self.dut["tb"].DAC_VPFB,set_values["VPFB"])
        self.assertEqual(self.dut["tb"].DAC_VNFOLL,set_values["VNFoll"])
        self.assertEqual(self.dut["tb"].DAC_VPFOLL,set_values["VPFoll"])
        self.assertEqual(self.dut["tb"].DAC_VNLOAD,  set_values["VNLoad"])
        self.assertEqual(self.dut["tb"].DAC_VPLOAD,  set_values["VPLoad"])
        self.assertEqual(self.dut["tb"].DAC_TDAC_LSB,set_values["TDAC_LSB"])
        self.assertEqual(self.dut["tb"].DAC_VSF,  set_values["Vsf"])
        self.assertEqual(self.dut["tb"].DAC_DRIVER,  set_values["Driver"])
        self.assertEqual(self.dut["tb"].MON_BLRES,  set_values["Mon_BLRes"])
        self.assertEqual(self.dut["tb"].MON_VAMP1, set_values["Mon_VAmp1"])
        self.assertEqual(self.dut["tb"].MON_VAMP2,set_values["Mon_VAmp2"])
        self.assertEqual(self.dut["tb"].MON_VPFB,set_values["Mon_VPFB"])
        self.assertEqual(self.dut["tb"].MON_VNFOLL, set_values["Mon_VNFoll"])
        self.assertEqual(self.dut["tb"].MON_VPFOLL,set_values["Mon_VPFoll"])
        self.assertEqual(self.dut["tb"].MON_VNLOAD, set_values["Mon_VNLoad"])
        self.assertEqual(self.dut["tb"].MON_VPLOAD, set_values["Mon_VPLoad"])       
        self.assertEqual(self.dut["tb"].MON_TDAC_LSB,set_values["Mon_TDAC_LSB"])
        self.assertEqual(self.dut["tb"].MON_VSF,set_values["Mon_Vsf"])
        self.assertEqual(self.dut["tb"].MON_DRIVER,set_values["Mon_Driver"])
        self.assertEqual(self.dut["tb"].ENANABUFFER,set_values["EnAnaBuffer"])
        self.assertEqual(int(self.dut["tb"].get_EnDataCMOS()), set_values["EnDataCMOS"])
        self.assertEqual(int(self.dut["tb"].get_EnDataLVDS()), set_values["EnDataLVDS"])
        self.assertEqual(self.dut["tb"].ENMONITORCOL, set_values["EnMonitorCol"])

        #######
        ## set all 0 to DAC
        self.dut['CONF_SR'].setall(False)
        self.dut['CONF']['Ld_DAC'] = 1
        self.dut['CONF'].write()
        self.dut['CONF_SR'].write() 
        while not self.dut['CONF_SR'].is_ready:
            pass
        self.dut['CONF']['Ld_DAC'] = 0
        self.dut['CONF'].write()

        self.assertEqual(self.dut["tb"].DAC_BLRES,0)
        self.assertEqual(self.dut["tb"].DAC_VAMP1, 0)
        self.assertEqual(self.dut["tb"].DAC_VAMP2, 0)
        self.assertEqual(self.dut["tb"].DAC_VPFB,0)
        self.assertEqual(self.dut["tb"].DAC_VNFOLL,0)
        self.assertEqual(self.dut["tb"].DAC_VPFOLL,0)
        self.assertEqual(self.dut["tb"].DAC_VNLOAD,0)
        self.assertEqual(self.dut["tb"].DAC_VPLOAD,0)
        self.assertEqual(self.dut["tb"].DAC_VSF,0)
        self.assertEqual(self.dut["tb"].DAC_TDAC_LSB,0)
        self.assertEqual(self.dut["tb"].DAC_DRIVER,0)
        self.assertEqual(self.dut["tb"].MON_VSF,0)
        self.assertEqual(self.dut["tb"].MON_VPFB,0)
        self.assertEqual(self.dut["tb"].MON_VNLOAD,0)
        self.assertEqual(self.dut["tb"].MON_VPLOAD,0)
        self.assertEqual(self.dut["tb"].MON_VNFOLL,0)
        self.assertEqual(self.dut["tb"].MON_VPFOLL,0)
        self.assertEqual(self.dut["tb"].MON_VAMP1,0)
        self.assertEqual(self.dut["tb"].MON_VAMP2,0)        
        self.assertEqual(self.dut["tb"].MON_TDAC_LSB,0)
        self.assertEqual(self.dut["tb"].MON_BLRES,0)
        self.assertEqual(self.dut["tb"].MON_DRIVER,0)
        self.assertEqual(self.dut["tb"].ENANABUFFER,0)
        self.assertEqual(int(self.dut["tb"].get_EnDataCMOS()), 0)
        self.assertEqual(int(self.dut["tb"].get_EnDataLVDS()), 0)
        self.assertEqual(self.dut["tb"].ENMONITORCOL, 0)

    @unittest.skip('skip')
    def test_05All1(self):
        self.dut['CONF_SR'].setall(True)
        self.dut['CONF']['Ld_DAC'] = 1
        self.dut['CONF'].write()
        self.dut['CONF_SR'].write() 
        while not self.dut['CONF_SR'].is_ready:
            pass
        self.dut['CONF']['Ld_Cnfg'] = 0
        self.dut['CONF']['Ld_DAC'] = 0
        self.dut['CONF'].write()

        self.assertEqual(self.dut["tb"].DAC_BLRES,0x3F)
        self.assertEqual(self.dut["tb"].DAC_VAMP1, 0x3F)
        self.assertEqual(self.dut["tb"].DAC_VAMP2, 0x3F)
        self.assertEqual(self.dut["tb"].DAC_VPFB,0x3F)
        self.assertEqual(self.dut["tb"].DAC_VNFOLL,0x3F)
        self.assertEqual(self.dut["tb"].DAC_VPFOLL,0x3F)
        self.assertEqual(self.dut["tb"].DAC_VNLOAD,0x3F)
        self.assertEqual(self.dut["tb"].DAC_VPLOAD,0x3F)
        self.assertEqual(self.dut["tb"].DAC_VSF,0x3F)
        self.assertEqual(self.dut["tb"].DAC_TDAC_LSB,0x3F)
        self.assertEqual(self.dut["tb"].DAC_DRIVER,0x3F)
        self.assertEqual(self.dut["tb"].MON_VSF,1)
        self.assertEqual(self.dut["tb"].MON_VPFB,1)
        self.assertEqual(self.dut["tb"].MON_VNLOAD,1)
        self.assertEqual(self.dut["tb"].MON_VPLOAD,1)
        self.assertEqual(self.dut["tb"].MON_VNFOLL,1)
        self.assertEqual(self.dut["tb"].MON_VPFOLL,1)
        self.assertEqual(self.dut["tb"].MON_VAMP1,1)
        self.assertEqual(self.dut["tb"].MON_VAMP2,1)        
        self.assertEqual(self.dut["tb"].MON_TDAC_LSB,1)
        self.assertEqual(self.dut["tb"].MON_BLRES,1)
        self.assertEqual(self.dut["tb"].MON_DRIVER,1)
        self.assertEqual(self.dut["tb"].ENANABUFFER,1) 
        self.assertEqual(int(self.dut["tb"].get_EnDataCMOS()),1)
        self.assertEqual(int(self.dut["tb"].get_EnDataLVDS()),1)
        self.assertEqual(self.dut["tb"].ENMONITORCOL, 0xFFFFFFFFFFFFFF)

    @unittest.skip('skip')
    def test_06Rst(self):
        #####
        ## write random number one more time
        set_values={}
        for dac_name in ["BLRes","VAmp1","VAmp2","VPFB","VNFoll","VPFoll","VNLoad","TDAC_LSB","Vsf","Driver"]:
             set_values[dac_name]=random.randint(0,0x3F)
             set_values["Mon_{0:s}".format(dac_name)]=0
        set_values["Mon_TDAC_LSB"]=1
        for dac_name in set_values.keys():
             self.dut['CONF_SR'][dac_name]=set_values[dac_name]
        set_values["EnAnaBuffer"]=0
        self.dut["CONF_SR"]["EnAnaBuffer"] =set_values["EnAnaBuffer"]
        set_values["EnDataCMOS"]=0
        self.dut["CONF_SR"]["EnDataCMOS"] =set_values["EnDataCMOS"]
        set_values["EnDataLVDS"]=1
        self.dut["CONF_SR"]["EnDataLVDS"] =set_values["EnDataLVDS"]
        set_values["EnMonitorCol"]=random.randint(0,0xFFFFFFFFFFFFFF)
        self.dut["CONF_SR"]["EnMonitorCol"]=set_values["EnMonitorCol"]

        self.dut['CONF']['Ld_DAC'] = 1
        self.dut['CONF'].write()
        self.dut['CONF_SR'].write() 
        while not self.dut['CONF_SR'].is_ready:
            pass
        self.dut['CONF']['Ld_DAC'] = 0
        #####
        ## RST on-->should be no change
        self.dut['CONF']['Rst'] = 1
        self.dut['CONF'].write()

        self.assertEqual(self.dut["tb"].DAC_BLRES,set_values["BLRes"])
        self.assertEqual(self.dut["tb"].DAC_VAMP1, set_values["VAmp1"])
        self.assertEqual(self.dut["tb"].DAC_VAMP2, set_values["VAmp2"])
        self.assertEqual(self.dut["tb"].DAC_VPFB,set_values["VPFB"])
        self.assertEqual(self.dut["tb"].DAC_VNFOLL,set_values["VNFoll"])
        self.assertEqual(self.dut["tb"].DAC_VPFOLL,set_values["VPFoll"])
        self.assertEqual(self.dut["tb"].DAC_VNLOAD,  set_values["VNLoad"])
        self.assertEqual(self.dut["tb"].DAC_TDAC_LSB,set_values["TDAC_LSB"])
        self.assertEqual(self.dut["tb"].DAC_VSF,  set_values["Vsf"])
        self.assertEqual(self.dut["tb"].DAC_DRIVER,  set_values["Driver"])
        self.assertEqual(self.dut["tb"].MON_BLRES,  set_values["Mon_BLRes"])
        self.assertEqual(self.dut["tb"].MON_VAMP1, set_values["Mon_VAmp1"])
        self.assertEqual(self.dut["tb"].MON_VAMP2,set_values["Mon_VAmp2"])
        self.assertEqual(self.dut["tb"].MON_VPFB,set_values["Mon_VPFB"])
        self.assertEqual(self.dut["tb"].MON_VNFOLL, set_values["Mon_VNFoll"])
        self.assertEqual(self.dut["tb"].MON_VPFOLL,set_values["Mon_VPFoll"])
        self.assertEqual(self.dut["tb"].MON_VNLOAD, set_values["Mon_VNLoad"])        
        self.assertEqual(self.dut["tb"].MON_TDAC_LSB,set_values["Mon_TDAC_LSB"])
        self.assertEqual(self.dut["tb"].MON_VSF,set_values["Mon_Vsf"])
        self.assertEqual(self.dut["tb"].MON_DRIVER,set_values["Mon_Driver"])
        self.assertEqual(self.dut["tb"].ENANABUFFER, set_values["EnAnaBuffer"])
        self.assertEqual(int(self.dut["tb"].get_EnDataCMOS()), set_values["EnDataCMOS"])
        self.assertEqual(int(self.dut["tb"].get_EnDataLVDS()), set_values["EnDataLVDS"])
        self.assertEqual(self.dut["tb"].ENMONITORCOL, set_values["EnMonitorCol"])
        #####
        ## RST off again-->should be no change
        self.dut['CONF']['Rst'] = 0
        self.dut['CONF'].write()

        self.assertEqual(self.dut["tb"].DAC_BLRES,set_values["BLRes"])
        self.assertEqual(self.dut["tb"].DAC_VAMP1, set_values["VAmp1"])
        self.assertEqual(self.dut["tb"].DAC_VAMP2, set_values["VAmp2"])
        self.assertEqual(self.dut["tb"].DAC_VPFB,set_values["VPFB"])
        self.assertEqual(self.dut["tb"].DAC_VNFOLL,set_values["VNFoll"])
        self.assertEqual(self.dut["tb"].DAC_VPFOLL,set_values["VPFoll"])
        self.assertEqual(self.dut["tb"].DAC_VNLOAD,  set_values["VNLoad"])
        self.assertEqual(self.dut["tb"].DAC_TDAC_LSB,set_values["TDAC_LSB"])
        self.assertEqual(self.dut["tb"].DAC_VSF,  set_values["Vsf"])
        self.assertEqual(self.dut["tb"].DAC_DRIVER,  set_values["Driver"])
        self.assertEqual(self.dut["tb"].MON_BLRES,  set_values["Mon_BLRes"])
        self.assertEqual(self.dut["tb"].MON_VAMP1, set_values["Mon_VAmp1"])
        self.assertEqual(self.dut["tb"].MON_VAMP2,set_values["Mon_VAmp2"])
        self.assertEqual(self.dut["tb"].MON_VPFB,set_values["Mon_VPFB"])
        self.assertEqual(self.dut["tb"].MON_VNFOLL, set_values["Mon_VNFoll"])
        self.assertEqual(self.dut["tb"].MON_VPFOLL,set_values["Mon_VPFoll"])
        self.assertEqual(self.dut["tb"].MON_VNLOAD, set_values["Mon_VNLoad"])        
        self.assertEqual(self.dut["tb"].MON_TDAC_LSB,set_values["Mon_TDAC_LSB"])
        self.assertEqual(self.dut["tb"].MON_VSF,set_values["Mon_Vsf"])
        self.assertEqual(self.dut["tb"].MON_DRIVER,set_values["Mon_Driver"])
        self.assertEqual(self.dut["tb"].ENANABUFFER, set_values["EnAnaBuffer"])
        self.assertEqual(int(self.dut["tb"].get_EnDataCMOS()), set_values["EnDataCMOS"])
        self.assertEqual(int(self.dut["tb"].get_EnDataLVDS()), set_values["EnDataLVDS"])

        self.assertEqual(self.dut["tb"].ENMONITORCOL, set_values["EnMonitorCol"])


if __name__ == '__main__':
    if len(sys.argv)>1:
        TestDAC.sim_files=sys.argv.pop()
    unittest.main()

