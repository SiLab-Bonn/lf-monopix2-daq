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

class TestTrimLd(test_Monopix2.TestMonopix2):

    def test_00init(self):
        self.dut.init()
        #########################
        ### init all preamp, injection ON
        self.dut['CONF_SR']['EnColRO'].setall(True)
        self.dut['CONF_SR']['InjEnCol'].setall(False) ## active low
        self.dut.PIXEL_CONF["EnPre"].fill(True)
        self.dut.PIXEL_CONF["Trim"].fill(15)
        self.dut['CONF_SR']['TrimLd']=0 # active low
        #self.dut['CONF_SR']['EnInjLd']=0 # active low
        self.util_set_pixel(bit="EnPre",defval=True)
        self.dut['CONF_SR']['TrimLd']=1
        #self.dut['CONF_SR']['EnInjLd']=1

        self.dut.PIXEL_CONF["EnInj"].fill(False)
        for i in range(self.dut.ROW):
            self.dut.PIXEL_CONF["EnInj"][i%self.dut.COL,i]=True
        self.util_set_pixel(bit="EnInj",defval=None)

        self.dut.set_inj_all(inj_n=1,inj_width=2,inj_delay=10)
        #self.dut.set_timestamp640(src="mon")
        self.dut.set_monoread(sync_timestamp=False)

    #@unittest.skip('skip')
    def test_01all1(self):
        self.dut.start_inj()
        hitin=np.argwhere(np.bitwise_and(self.dut.PIXEL_CONF["EnInj"],self.dut.PIXEL_CONF["EnPre"]))
        print("=====sim=====01",end="")
        raw=self.dut.get_data_now()
        pre_len=len(raw)
        flg=0
        for i in range(1000):
            raw=np.append(raw,self.dut.get_data_now())
            if len(raw) == 3*len(hitin):
                break
            print(len(raw),"/",3*len(hitin),"-",end="")
            if len(raw)==pre_len:
                flg=flg+1
            else:
                pre_len=len(raw)
                flg=0
            if flg>10:
                break
        print("-{0:d}".format(i))
        dat=interpreter.raw2list(raw)
        print("=====sim=====",dat)
        pix=dat[dat['col']<self.dut.COL]
        self.assertEqual(len(pix), len(hitin))
        for h in hitin:
            p=pix[np.bitwise_and(pix['col']==h[0],pix['row']==h[1])]
            tot=(p['te']-p['le']) & 0x3F
            self.dut.logger.info("h{0} tot{1}".format(str(h),str(tot)))
            self.assertTrue(tot in [
                ((24-15)*4+1)&0x3F,((24-15)*4-2)&0x3F,((24-15)*4)&0x3F])
        self.dut.logger.info("=====sim=====all1 done")

    #@unittest.skip('skip')
    def test_02all0(self):
        self.dut.PIXEL_CONF["Trim"].fill(0)
        self.util_set_tdac(defval=0)

        self.dut.start_inj()
        hitin=np.argwhere(np.bitwise_and(self.dut.PIXEL_CONF["EnInj"],self.dut.PIXEL_CONF["EnPre"]))   
        raw=self.dut.get_data_now()
        pre_len=len(raw)
        flg=0
        for i in range(1000):
            raw=np.append(raw,self.dut.get_data_now())
            if len(raw) == 3*len(hitin):
                break
            print("{0:d}/{1:d} ".format(len(raw),len(hitin)*3),end="")
            if len(raw)==pre_len:
                flg=flg+1
            else:
                pre_len=len(raw)
                flg=0
            if flg>10:
                break
        print("-",i)
        dat=interpreter.raw2list(raw)
        pix=dat[dat['col']<self.dut.COL]
        print("=====sim=====all0",pix)
        self.assertEqual(len(pix), len(hitin))
        for h in hitin:
            p=pix[np.bitwise_and(pix['col']==h[0],pix['row']==h[1])]
            tot=(p['te']-p['le']) & 0x3F
            self.dut.logger.info("h{0:s} tot{1:s}".format(str(h),str(tot)))
            self.assertTrue(tot in [
                ((24-0)*4-2)&0x3F,((24-0)*4+1)&0x3F,((24-0)*4)&0x3F])
        self.dut.logger.info("=====sim=====all0 done")

    #@unittest.skip('skip')
    def test_04random(self):
        self.dut.PIXEL_CONF["Trim"]=np.random.randint(16, size=(self.dut.COL, self.dut.ROW))
        self.util_set_tdac(defval=False)
        self.dut.PIXEL_CONF["EnPre"] = (np.random.randint(2, size=(self.dut.COL, self.dut.ROW)) == 1)
        self.util_set_pixel(bit="EnPre",defval=None)
        self.dut.PIXEL_CONF["EnInj"] = (np.random.randint(2, size=(self.dut.COL, self.dut.ROW)) == 1)
        self.util_set_pixel(bit="EnInj",defval=None)
        hitin=np.argwhere(np.bitwise_and(self.dut.PIXEL_CONF["EnInj"],self.dut.PIXEL_CONF["EnPre"]))

        self.dut.start_inj()
        raw=self.dut.get_data_now()
        pre_len=len(raw)
        flg=0
        print("=====sim=====random")
        for i in range(10000):
            raw=np.append(raw,self.dut.get_data_now())
            print ("{0:d}/{1:d} ".format(len(raw),len(hitin)*3))
            if len(raw) == 3*len(hitin):
                break
            if pre_len==len(raw):
                flg=flg+1
            else:
                pre_len=len(raw)
                flg=0
            if flg>10:
                break
        print('-',i)
        dat=interpreter.raw2list(raw)
        pix=dat[dat['col']<self.dut.COL]
        self.assertEqual(len(pix), len(hitin))
        for h in hitin:
            p=pix[np.bitwise_and(pix['col']==h[0],pix['row']==h[1])]
            tot=(p['te']-p['le']) & 0x3F
            tdac=self.dut.PIXEL_CONF["Trim"][h[0],h[1]]
            print(h, tdac, ((24-tdac)*4) & 0x3F, tot)
            self.assertEqual(len(p),1)
            self.assertTrue(tot[0] in [
                ((24-tdac)*4-2)&0x3F, ((24-tdac)*4+1)&0x3F, ((24-tdac)*4)&0x3F])

if __name__ == '__main__':
    if len(sys.argv) > 1:
        TestTrimLd.extra_defines=[sys.argv.pop()]
    unittest.main()