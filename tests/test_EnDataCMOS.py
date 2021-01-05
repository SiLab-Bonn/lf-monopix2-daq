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

class TestEnDataCMOS(test_Monopix2.TestMonopix2):
    hit_file=[
            HIT_FILE0,     ## test01     
            #hit_file[:-4]+"02.csv", ## test02  
            #hit_file[:-4]+"03.csv", ## test03  
            ]
            
    def test_00init(self):
        ## Injection all ON
        self.dut.init()
        self.dut['CONF_SR']['InjEnCol'].setall(False) ## active low
        self.dut.PIXEL_CONF["EnInj"].fill(True)
        self.util_set_pixel(bit="EnInj",defval=True)
        #############################
        ## set readout, injection
        self.dut.set_inj_all(inj_n=1,inj_width=128,inj_delay=100)
        #self.dut.set_timestamp640(src="mon")
        self.dut.set_monoread(sync_timestamp=False)

    #@unittest.skip('skip')
    def test_01init(self):
        col=5
        row=20
        self.dut.PIXEL_CONF["EnPre"].fill(False)
        self.dut.PIXEL_CONF["EnPre"][5,20]=True
        self.util_set_pixel(bit="EnPre",defval=False)
        #################
        ### inject 
        self.dut.start_inj()
        print("=====sim=====",self.dut["fifo"].FIFO_INT_SIZE,end='')
        for i in range(10):
            size=self.dut["fifo"].FIFO_INT_SIZE
            print(i,end='')
            if size == 3:
                break
        print("-",size)
        raw=self.dut.get_data_now()
        dat=interpreter.raw2list(raw)

        EnDataCMOS=self.dut["tb"].get_EnDataCMOS()
        self.assertEqual(int(EnDataCMOS), self.dut["CONF_SR"]._conf["init"]["EnDataCMOS"])
        self.assertEqual(len(dat),1)
        self.assertTrue(np.all(dat["col"]==col))
        self.assertTrue(np.all(dat["row"]==row))
        self.assertTrue(np.all((dat["te"]-dat["le"]) & 0x3F == 128 & 0x3F))

    #@unittest.skip('skip')
    def test_02disable(self):
        self.dut['CONF_SR']['EnDataCMOS']=0
        self.dut['CONF']['Ld_DAC'] = 1
        self.dut['CONF'].write()        
        self.dut['CONF_SR'].write()
        while not self.dut['CONF_SR'].is_ready:
            pass
        self.dut['CONF']['Ld_DAC'] = 0

        self.dut.start_inj()
        print("=====sim=====",self.dut["fifo"].FIFO_INT_SIZE,end='')
        for i in range(10):
            size=self.dut["fifo"].FIFO_INT_SIZE
            print(i,end='')
            if size == 3:
                break
        print("-",size)

        EnDataCMOS=self.dut["tb"].get_EnDataCMOS() ### check again..
        self.assertEqual(int(EnDataCMOS), 0)
        self.assertEqual(size, 3)
        raw=self.dut["intf"].read_str(addr=self.dut["fifo"]._conf["base_data_addr"], size=size*4)
        dat=''
        for r in raw:
            dat=dat+r[::-1]
        #self.assertEqual( dat[:27], "zzzzzzzzzzzzzzzzzzzzzzzzzzz")
        self.assertEqual( dat[:27], "xxxxxxxxxxxxxxxxxxxxxxxxxxx")

    #@unittest.skip('skip')
    def test_03default(self):
        #############
        ## set defualt(ON)
        self.dut['CONF']['Def_Conf'] = 1
        self.dut['CONF'].write()        

        self.dut["data_rx"].DISSABLE_GRAY_DECODER=1
        self.util_startHIT()
        print("=====sim=====",end='')
        for i in range(10):
            size=self.dut["fifo"].FIFO_INT_SIZE
            if size == 3:
                break
            print(i,end='')
        print()
        self.dut["data_rx"].DISSABLE_GRAY_DECODER=0
        raw=self.dut.get_data_now()
         
        EnDataCMOS=self.dut["tb"].get_EnDataCMOS()
        print("=====sim===== def",EnDataCMOS)
        self.assertEqual(int(EnDataCMOS), 1)
        self.assertEqual(size, 3)
        print("=====sim===== def", hex(raw[0]),hex(raw[1]),hex(raw[2]))
        self.assertEqual(raw[0], 0x4aacc0F)

if __name__ == '__main__':
    if len(sys.argv)>1:
        TestEnDataCMOS.extra_defines=[sys.argv.pop()]
    unittest.main()