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

class TestInjectionCol(test_Monopix2.TestMonopix2):

    def test_00init(self):
        self.dut.init()
        inj_width=128
        inj_delay=100
        inj_n=1
        self.dut.set_monoread(sync_timestamp=False)
        self.dut.set_inj_all(inj_n=inj_n,inj_delay=inj_delay,inj_width=inj_width)
        ##########################
        #### set all preamp ON inj ON
        self.dut.PIXEL_CONF["EnPre"].fill(True)
        self.util_set_pixel(bit="EnPre",defval=True)
        self.dut.PIXEL_CONF["EnInj"].fill(False)
        self.dut.PIXEL_CONF["EnInj"][:,20]=True
        self.util_set_pixel(bit="EnInj",defval=0)

    #@unittest.skip('skip')
    def test_01col5(self):
        #################
        ## select one columnb (COL=0)
        self.dut.start_inj()
        for i in range(1000):
            size=self.dut["fifo"].FIFO_INT_SIZE
            if size == 3:
                break
        print("=====sim=====",i)
        raw=self.dut.get_data_now()
        dat=interpreter.raw2list(raw)
        print("=====sim=====",dat)

        self.assertTrue(np.all(dat["col"]==5))
        self.assertTrue(np.all((dat["te"]-dat["le"]) & 0x3F == 128 & 0x3F))
        self.assertTrue(np.all(dat["row"]==20))

    #@unittest.skip('skip') 
    def test_02default(self):
        row=20
        self.dut['CONF_SR']['InjEnCol']=0x7FFFFFFFFFFFFF # active low
        self.dut['CONF']['Ld_Cnfg'] = 0
        self.dut['CONF']['ClkOut'] = 0
        self.dut['CONF']['ClkBX'] = 0
        self.dut['CONF'].write()
        self.dut['CONF_SR'].write()
        while not self.dut['CONF_SR'].is_ready:
            pass
        self.dut['CONF']['ClkOut'] = 1
        self.dut['CONF']['ClkBX'] = 1
        self.dut['CONF'].write()
        col=np.argwhere(np.bitwise_not(self.dut['CONF_SR']['InjEnCol'].tolist()))
        print("====sim====def",col[:,0])

        ##############################
        ## Default value
        self.dut['CONF']['Def_Conf'] = 1
        self.dut['CONF'].write()
        self.dut.start_inj()
        for i in range(10):
            if self.dut["fifo"].FIFO_INT_SIZE:
                break
        size=self.dut["fifo"].FIFO_INT_SIZE
        print("====sim====size",size)
        self.assertEqual(size, 0)

        ##############################
        ## Default is OFFF again
        self.dut['CONF']['Def_Conf'] = 0
        self.dut['CONF'].write()
        self.dut.start_inj()
        for i in range(100):
            size=self.dut["fifo"].FIFO_INT_SIZE
            #if self.dut['inj'].is_ready:
            if size==3:
                break
        #size=self.dut["fifo"].FIFO_INT_SIZE
        raw=self.dut.get_data_now()
        print('=====sim=====raw',end="")
        for r in raw:
            print(hex(r),end="")
        print("-") 
        dat=interpreter.raw2list(raw,delete_noise=False)

        print('=====sim=====size', size, len(raw), len(dat))
        print('=====sim=====pix',dat)
        self.assertEqual(len(dat), 1)
        self.assertEqual(dat["col"][0],col[0])
        self.assertEqual((dat[0]["te"]-dat[0]["le"]) & 0x3F, 128 & 0x3F)
        self.assertEqual(dat[0]["row"],row)
        
    #@unittest.skip('skip') 
    def test_03all1(self):
        self.dut['CONF_SR']['InjEnCol'].setall(False) # active low
        self.dut['CONF']['Ld_Cnfg'] = 0
        self.dut['CONF']['ClkOut'] = 0
        self.dut['CONF']['ClkBX'] = 0
        self.dut['CONF'].write()
        self.dut['CONF_SR'].write()
        while not self.dut['CONF_SR'].is_ready:
            pass
        self.dut['CONF']['ClkOut'] = 1
        self.dut['CONF']['ClkBX'] = 1
        self.dut['CONF'].write()

        self.dut.start_inj()
        print("=====sim=====all1",end="")
        for i in range(100):
            size=self.dut["fifo"].FIFO_INT_SIZE
            if size == 3*self.dut.COL:
                break
            print(size,end="")
        print("-",i)
        raw=self.dut.get_data_now()
        dat=interpreter.raw2list(raw)

        print("=====sim=====",dat)
        self.assertEqual(len(dat), self.dut.COL)
        self.assertTrue(np.all(dat["col"]==np.arange(self.dut.COL)))
        self.assertTrue(np.all((dat["te"]-dat["le"]) & 0x3F == 128 & 0x3F))
        self.assertTrue(np.all(dat["row"]==20))

    #@unittest.skip('skip') 
    def test_04all0(self):
        self.dut['CONF_SR']['InjEnCol'].setall(True) # active low
        self.dut['CONF']['Ld_Cnfg'] = 0
        self.dut['CONF']['ClkOut'] = 0
        self.dut['CONF']['ClkBX'] = 0
        self.dut['CONF'].write()
        self.dut['CONF_SR'].write()
        while not self.dut['CONF_SR'].is_ready:
            pass
        self.dut['CONF']['ClkOut'] = 1
        self.dut['CONF']['ClkBX'] = 1
        self.dut['CONF'].write()

        self.dut.start_inj()
        for i in range(100):
            if self.dut['inj'].is_ready:
                break
        size=self.dut["fifo"].FIFO_INT_SIZE
        self.assertEqual(size, 0)

    #@unittest.skip('skip')
    def test_05random(self):
        row=20
        self.dut['CONF_SR']['InjEnCol']=random.randint(1,0xFFFFFFFFFFFFFE)
        self.dut['CONF']['Ld_Cnfg'] = 0
        self.dut['CONF']['ClkOut'] = 0
        self.dut['CONF']['ClkBX'] = 0
        self.dut['CONF'].write()
        self.dut['CONF_SR'].write()
        while not self.dut['CONF_SR'].is_ready:
            pass
        self.dut['CONF']['ClkOut'] = 1
        self.dut['CONF']['ClkBX'] = 1
        self.dut['CONF'].write()

        col=np.argwhere(np.bitwise_not(self.dut['CONF_SR']['InjEnCol'].tolist()))[:,0]
        print("====sim====random",col)

        inj_width=32
        inj_delay=5000
        inj_n=5
        self.dut.set_inj_all(inj_n=inj_n,inj_delay=inj_delay,inj_width=inj_width)

        self.dut.start_inj()
        raw=self.dut.get_data_now()
        print("=====sim=====random",end="")
        flg=0
        pre_len=len(raw)
        for i in range(10000):
            raw=np.append(raw,self.dut.get_data_now())
            if len(raw) == 3*inj_n*len(col):
                break
            if pre_len==len(raw):
                flg=flg+1
            else:
                pre_len=len(raw)
                flg=0
            if flg>1000:
                break
            print(flg,len(raw),"/",3*inj_n*len(col),"-",end="")
        print(i)
        dat=interpreter.raw2list(raw,delete_noise=False)
        pix=dat[dat['col']<self.dut.COL]
        
        bcid_off=pix[0]['le']
        bcid_step=inj_width+inj_delay
        print('=====sim=====',dat)
        print('=====sim=====',bcid_off, bcid_step&0x3F)

        self.assertEqual(len(pix),inj_n*len(col))
        for i,p in enumerate(pix):
            self.assertEqual(p['col'], col[i%len(col)])
            self.assertEqual(p['row'],row)
            self.assertEqual(p['le'], (bcid_off+(i//len(col))*bcid_step) & 0x3F)
            self.assertEqual((p['te']-p['le']) & 0x3F, inj_width & 0x3F)

if __name__ == '__main__':
    if len(sys.argv)>1:
        TestInjectionCol.extra_defines=[sys.argv.pop()]
    unittest.main()



