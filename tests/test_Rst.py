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

import monopix2_daq.monopix2_sim as monopix2
import monopix2_daq.analysis.interpreter_idx as interpreter
import test_Monopix2

HIT_FILE0 = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
           "tests/data/"+os.path.basename(os.path.abspath(__file__))[:-2].split("_")[0]+"_"+os.path.basename(os.path.abspath(__file__))[:-2].split("_")[-1]+"csv")

class TestRst(test_Monopix2.TestMonopix2):
    hit_file=[
        HIT_FILE0,     ## test02     
        HIT_FILE0[:-4]+"03.csv", ## test03  
        ]

    def test_00init(self):
        self.dut.init()
        ##########################
        #### set all preamp ON mon ON
        self.dut['CONF_SR']['EnColRO'].setall(True) 
        self.dut['CONF_SR']['InjEnCol'].setall(False)  #active low 
        self.dut['CONF_SR']['EnInjLd']=0 # active low
        self.dut.PIXEL_CONF["EnPre"].fill(True)
        self.util_set_pixel(bit="EnPre",defval=True)
        self.dut['CONF_SR']['EnInjLd']=1

        self.dut.set_inj_all(inj_n=1,inj_width=40,inj_delay=100)
        #self.dut.set_monoread(sync_timestamp=False)
        #self.dut.set_timestamp640("mon")

    #@unittest.skip('skip') 
    def test_01TokOut(self):
        """ Rst should reset TOKEN to LOW
        """
        print("=====sim=====01 TOKEN, data=", repr(self.dut['intf'].read_str(0x12009,size=1)[0]))
        ## set switches
        self.dut['CONF']['ResetBcid'] = 0
        self.dut['CONF']['Rst'] = 1
        self.dut['CONF']['LVDS_Out'] = 0
        self.dut['CONF']['ClkBX'] = 0
        self.dut['CONF']['ClkOut'] = 0
        self.dut['CONF'].write()

        self.dut['CONF']['Rst'] = 0
        self.dut['CONF'].write()

        print("=====sim=====01 TOKEN, data=", repr(self.dut['intf'].read_str(0x12009,size=1)[0]))
        TokOut_PAD=self.dut['intf'].read(0x12009,size=1)[0]
        self.assertEqual(TokOut_PAD,0)

    #@unittest.skip('skip') 
    def test_02Hit(self):
        """ Rst should reset TOKEN to LOW (hit is asserted)
        """
        self.dut['CONF']['ResetBcid'] = 1
        self.dut['CONF']['Rst'] = 1
        self.dut['CONF']['LVDS_Out'] = 0
        self.dut['CONF']['ClkBX'] = 1
        self.dut['CONF']['ClkOut'] = 1
        self.dut['CONF'].write()

        self.dut['CONF']['Rst'] = 0
        self.dut['CONF'].write()

        self.dut['CONF']['ResetBcid'] = 0
        self.dut['CONF'].write()
        self.assertEqual(self.dut['tb'].TOKOUT_PAD,0)
        ######
        ## 2.1 inject HIT then TOKEN should be HIGH
        self.util_startHIT()
        bxid, col, row, tot=self.util_nextHit()
        for i in range(100):
            TokOut_PAD=self.dut['tb'].TOKOUT_PAD
            print("=====sim=====02",i,col,row,TokOut_PAD)
            if TokOut_PAD==1:
                break
        self.assertEqual(TokOut_PAD,1)
         
        ######
        ## 2.2 Rst=1 then TOKEN=0
        self.dut['CONF']['Rst'] = 1
        self.dut['CONF'].write()
        self.assertEqual(self.dut['tb'].TOKOUT_PAD,0)

        self.dut['CONF']['Rst'] = 0
        self.dut['CONF'].write()    
        self.assertEqual(self.dut['tb'].TOKOUT_PAD,0)

    #@unittest.skip('skip')
    def test_03TE(self):
        """ TOKEN should be kept LOW when Rst=1 (even hit is injected)
        """
        self.dut['CONF']['ResetBcid'] = 1
        self.dut['CONF']['Rst'] = 1
        self.dut['CONF']['LVDS_Out'] = 0
        self.dut['CONF']['ClkBX'] = 1
        self.dut['CONF']['ClkOut'] = 1
        self.dut['CONF'].write()

        self.dut['CONF']['Rst'] = 0
        self.dut['CONF'].write()

        self.dut['CONF']['ResetBcid'] = 0
        self.dut['CONF'].write()
        self.assertEqual(self.dut['tb'].TOKOUT_PAD,0)

        self.util_startHIT()
        print("=====sim=====02 TIMESTAMP",self.dut['tb'].TIMESTAMP)
        #for i in range(100):
        #    TokOut_PAD=self.dut['tb'].TOKOUT_PAD
        #    if TokOut_PAD==1:
        #        break
        self.assertEqual(self.dut['tb'].TOKOUT_PAD,0)
        self.dut['CONF']['Rst'] = 1
        self.dut['CONF'].write()
        self.assertEqual(self.dut['tb'].TOKOUT_PAD,0)
        self.dut['CONF']['Rst'] = 0
        self.dut['CONF'].write() 
        self.assertEqual(self.dut['tb'].TOKOUT_PAD,0)
        print("=====sim=====02 TIMESTAMP",self.dut['tb'].TIMESTAMP)
        bxid, col, row, tot=self.util_nextHit()
        for i in range(100):
            TokOut_PAD=self.dut['tb'].TOKOUT_PAD
            print("=====sim=====02",i,col,row,TokOut_PAD)
            if TokOut_PAD==1:
                break
        print("=====sim=====02 TIMESTAMP",self.dut['tb'].TIMESTAMP)
        self.assertEqual(self.dut['tb'].TOKOUT_PAD,1)
        self.dut['CONF']['Rst'] = 1
        self.dut['CONF'].write()
        self.dut['CONF']['Rst'] = 0
        self.dut['CONF'].write() 
        self.assertEqual(self.dut['tb'].TOKOUT_PAD,0)

    #@unittest.skip('skip')
    def test_04all(self):
        ####
        ## if EnCOlRO OFF, and injected then hits are saved in pixels
        ## Rst=1 --> Rst=0  -->  EnColRO ON
        ## then TOKEN should be 0.
        self.dut['CONF_SR']['EnColRO'].setall(False)
        self.dut['CONF']['Ld_Cnfg'] = 0
        self.dut['CONF'].write()
        self.dut['CONF_SR'].write()
        while not self.dut['CONF_SR'].is_ready:
            pass
        self.assertEqual(self.dut['tb'].TOKOUT_PAD,0)
        self.dut.start_inj()
        for i in range(100):
            TokOut_PAD=self.dut['tb'].TOKOUT_PAD
            print("=====sim=====all",i,TokOut_PAD)
            if TokOut_PAD==1:
                break
        self.assertEqual(TokOut_PAD,0)

        self.dut['CONF']['Rst'] = 1
        self.dut['CONF'].write() 
        self.dut['CONF']['Rst'] = 0
        self.dut['CONF'].write()
        self.assertEqual(self.dut['tb'].TOKOUT_PAD,0)
        ### enable all column
        self.dut['CONF_SR']['EnColRO'].setall(True)
        self.dut['CONF']['Ld_Cnfg'] = 0
        self.dut['CONF'].write()
        self.dut['CONF_SR'].write()
        while not self.dut['CONF_SR'].is_ready:
            pass
        ## reset was sent to disabled column
        self.assertEqual(self.dut['tb'].TOKOUT_PAD,0)

    #@unittest.skip('skip')
    def test_06rst(self):
        ## inject all reset all
        self.dut['CONF_SR']['EnColRO'].setall(True)
        self.dut['CONF']['Ld_Cnfg'] = 0
        self.dut['CONF'].write()
        self.dut['CONF_SR'].write()
        while not self.dut['CONF_SR'].is_ready:
            pass
        self.dut.start_inj()

        for i in range(10):
            if self.dut['inj'].READY==True:
                break
        print("=====sim=====06 TOKEN=", self.dut['tb'].TOKOUT_PAD)
        self.assertEqual(self.dut['tb'].TOKOUT_PAD,1)
        self.dut['CONF']['Rst'] = 1
        self.dut['CONF'].write() 
        self.dut['CONF']['Rst'] = 0
        self.dut['CONF'].write()
        self.assertEqual(self.dut['tb'].TOKOUT_PAD,0)

    #@unittest.skip('skip')
    def test_05noRst(self):
        ### enable col5
        col=self.dut.COL-1
        self.dut['CONF_SR']['EnColRO'].setall(False)
        self.dut['CONF_SR']['EnColRO'][col]=True
        self.dut['CONF']['Ld_Cnfg'] = 0
        self.dut['CONF'].write()
        self.dut['CONF_SR'].write()
        while not self.dut['CONF_SR'].is_ready:
            pass
        self.assertEqual(self.dut['tb'].TOKOUT_PAD,0)
        self.dut.start_inj()
        for i in range(10):
            if self.dut['inj'].READY==True:
                break
        self.assertEqual(self.dut['tb'].TOKOUT_PAD,1)

        ### disable all column
        self.dut['CONF_SR']['EnColRO'][col]=False
        self.dut['CONF']['Ld_Cnfg'] = 0
        self.dut['CONF'].write()
        self.dut['CONF_SR'].write()
        while not self.dut['CONF_SR'].is_ready:
            pass
        self.assertEqual(self.dut['tb'].TOKOUT_PAD,0)

        ### enable all column
        self.dut['CONF_SR']['EnColRO'].setall(True)
        self.dut['CONF_SR']['EnColRO'][col]=False
        self.dut['CONF']['Ld_Cnfg'] = 0
        self.dut['CONF'].write()
        self.dut['CONF_SR'].write()
        while not self.dut['CONF_SR'].is_ready:
            pass
        self.assertEqual(self.dut['tb'].TOKOUT_PAD,1)

if __name__ == '__main__':
    if len(sys.argv)>1:
        TestRst.extra_defines=[sys.argv.pop()]
    unittest.main()