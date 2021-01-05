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

class TestEnInjLd(test_Monopix2.TestMonopix2):
    hit_file=[
            ]
    def test_00init(self):
        self.dut.init()
        #####################
        ## set preamp ON, TDAC colwise value
        self.dut['CONF_SR']["EnColRO"].setall(True)
        self.dut['CONF_SR']["InjEnCol"].setall(False) ##active low
        self.dut.PIXEL_CONF['EnPre'].fill(True)
        self.util_set_pixel(bit="EnPre",defval=True)
        for c in range(self.dut.COL):
            self.dut.PIXEL_CONF['Trim'][c,:]=c%16
        self.util_set_tdac(defval=None)
        self.dut.set_inj_all(inj_n=1,inj_width=2,inj_delay=10)
        #self.dut.set_timestamp640(src="mon")
        self.dut.set_monoread(sync_timestamp=False)

    @unittest.skip('skip')
    def test_01pix(self):
        self.dut.PIXEL_CONF["EnInj"].fill(False)
        self.dut.PIXEL_CONF["EnInj"][5,20]=True
        self.util_set_pixel(bit="EnInj",defval=False)

        self.dut.start_inj()
        print("=====sim=====01",end="")
        raw=self.dut.get_data_now()
        for i in range(100000):
            raw=np.append(raw,self.dut.get_data_now())
            if len(raw) == 3:
                break
            print(len(raw),end="")
        print("-",i,end="")
        dat=interpreter.raw2list(raw)        
        pix=dat[dat['col']<self.dut.COL]
        print(pix, pix['te']-pix['le'] &0x3F,self.dut.PIXEL_CONF["Trim"][5,20])
        tdac=self.dut.PIXEL_CONF["Trim"][5,20]
        self.assertEqual(pix['col'],5)
        self.assertEqual(pix['row'],20)
        print("=====sim=====tot",(pix[0]['te']-pix[0]['le'])&0x3F, [((24-tdac)*4-2)&0x3F,((24-tdac)*4-1)&0x3F,((24-tdac)*4)&0x3F])
        self.assertTrue(((pix[0]['te']-pix[0]['le']) & 0x3F) in [((24-tdac)*4-2)&0x3F,((24-tdac)*4-1)&0x3F,((24-tdac)*4)&0x3F] )

    @unittest.skip('skip')
    def test_02all0(self):
        self.dut.PIXEL_CONF["EnInj"].fill(False)
        self.util_set_pixel(bit="EnInj",defval=False)

        self.dut.start_inj()
        print("=====sim=====all0",end="")
        for i in range(100):
            if self.dut['inj'].is_ready:
                break
        print("-",i,end="")
        raw=self.dut.get_data_now()
        self.assertEqual(len(raw),0)

    @unittest.skip('skip')
    def test_03col0(self):
        self.dut.PIXEL_CONF["EnInj"].fill(False)
        self.dut.PIXEL_CONF["EnInj"][0,:]=True
        self.util_set_pixel(bit="EnInj",defval=False)

        self.dut.start_inj()
        print("=====sim=====col0",end="")
        raw=self.dut.get_data_now()
        for i in range(1000):
            raw=np.append(raw,self.dut.get_data_now())
            if len(raw) >= 3*self.dut.ROW:
                break
            print(len(raw),end="")
        print("-",i,end="")
        dat=interpreter.raw2list(raw)        
        pix=dat[dat['col']<self.dut.COL]
        print(len(pix), pix)
        tdac=self.dut.PIXEL_CONF["Trim"][0,:]
        for i in np.arange(self.dut.ROW):
            self.assertEqual(pix[i]['col'],0)
            self.assertEqual(pix[i]['row'],self.dut.ROW-i-1)
            print("=====sim=====col0",i,(pix[i]['te']-pix[i]['le'])&0x3F,end="")
            print(((24-tdac[self.dut.ROW-i-1])*4-2)&0x3F,((24-tdac[self.dut.ROW-i-1])*4-1)&0x3F,((24-tdac[self.dut.ROW-i-1])*4)&0x3F,((24-tdac[self.dut.ROW-i-1])*4+1)&0x3F)
            self.assertTrue(
                ( (pix[i]['te']-pix[i]['le'])&0x3F ) in [
                ((24-tdac[self.dut.ROW-i-1])*4-2)&0x3F,((24-tdac[self.dut.ROW-i-1])*4-1)&0x3F,((24-tdac[self.dut.ROW-i-1])*4)&0x3F,((24-tdac[self.dut.ROW-i-1])*4+1)&0x3F])

   # @unittest.skip('skip')
    def test_04colmax(self):
        self.dut.PIXEL_CONF["EnInj"].fill(False)
        self.dut.PIXEL_CONF["EnInj"][self.dut.COL-1,:]=True
        self.util_set_pixel(bit="EnInj",defval=0)

        self.dut.start_inj()
        print("=====sim=====colmax",end="")
        raw=self.dut.get_data_now()
        for i in range(100000):
            raw=np.append(raw,self.dut.get_data_now())
            if len(raw) >= 3*self.dut.ROW:
                break
            print(len(raw),end="")
        print("-",i,end="")
        dat=interpreter.raw2list(raw)        
        pix=dat[dat['col']<self.dut.COL]
        print(len(pix), pix, pix['te']-pix['le'] &0x3F)
        tdac=self.dut.PIXEL_CONF["Trim"][self.dut.COL-1,:]
        for i in np.arange(self.dut.ROW):
            self.assertEqual(pix[i]['col'],self.dut.COL-1)
            self.assertEqual(pix[i]['row'],self.dut.ROW-i-1)
            self.assertTrue(
                ( (pix[i]['te']-pix[i]['le'])&0x3F ) in [
                ((24-tdac[self.dut.ROW-1-i])*4-2)&0x3F,((24-tdac[self.dut.ROW-1-i])*4-1)&0x3F,((24-tdac[self.dut.ROW-1-i])*4)&0x3F])

    #@unittest.skip('skip')
    def test_05row0(self):
        self.dut["CONF"]["Rst"]=1
        self.dut["CONF"].write()
        self.dut["CONF"]["Rst"]=0
        self.dut.PIXEL_CONF["EnInj"].fill(False)
        self.dut.PIXEL_CONF["EnInj"][:,0]=True
        self.util_set_pixel(bit="EnInj",defval=0)

        self.dut.start_inj()
        print("=====sim=====row0",end="")
        raw=self.dut.get_data_now()
        for i in range(1000):
            raw=np.append(raw,self.dut.get_data_now())
            if len(raw) >= 3*self.dut.COL:
                break
            print(len(raw),end="")
        print("-",i,end="")
        dat=interpreter.raw2list(raw)        
        pix=dat[dat['col']<self.dut.COL]
        #print(len(pix),pix)
        tdac=self.dut.PIXEL_CONF["Trim"][:,0]
        for i in np.arange(self.dut.COL):
            self.assertEqual(pix[i]['col'],i)
            self.assertEqual(pix[i]['row'],0)
            print(i,  (pix[i]['te']-pix[i]['le'])&0x3F, 
                [((24-tdac[i])*4-2)&0x3F,((24-tdac[i])*4-1)&0x3F,((24-tdac[i])*4)&0x3F,((24-tdac[i])*4+1)&0x3F] )
            self.assertTrue(
                ((pix[i]['te']-pix[i]['le'])&0x3F) in [
                ((24-tdac[i])*4-2)&0x3F,((24-tdac[i])*4-1)&0x3F,((24-tdac[i])*4)&0x3F,((24-tdac[i])*4+1)&0x3F])

    @unittest.skip('skip')
    def test_06rowmax(self):
        self.dut.PIXEL_CONF["EnInj"].fill(False)
        self.dut.PIXEL_CONF["EnInj"][:,self.dut.ROW-1]=True
        self.util_set_pixel(bit="EnInj",defval=0)

        self.dut.start_inj()
        print("=====sim=====rowmax ",end="")
        raw=self.dut.get_data_now()
        for i in range(100000):
            raw=np.append(raw,self.dut.get_data_now())
            if len(raw) == 3*self.dut.COL:
                break
            print(len(raw),end="")
        print(len(raw),"-",i,end="")
        dat=interpreter.raw2list(raw)        
        pix=dat[dat['col']<self.dut.COL]
        print(len(pix))
        tdac=self.dut.PIXEL_CONF["Trim"][:,self.dut.ROW-1]
        for i in range(self.dut.COL):
            print(i, (pix['te'][i]-pix['le'][i]) & 0x3F, self.dut.PIXEL_CONF["Trim"][i,self.dut.ROW-1],end="")
            print("(",((24-tdac[i])*4-1)&0x3F,((24-tdac[i])*4)&0x3F,((24-tdac[i])*4+1)&0x3F,")")
        for i in np.arange(self.dut.COL):
            self.assertEqual(pix[i]['col'],i)
            self.assertEqual(pix[i]['row'],self.dut.ROW-1)
            self.assertTrue(
                (pix['te'][i]-pix['le'][i]) & 0x3F in [
                ((24-tdac[i])*4-2)&0x3F,((24-tdac[i])*4-1)&0x3F,((24-tdac[i])*4)&0x3F,((24-tdac[i])*4+1)&0x3F])
        print("=====sim=====rowmax done")
            
    @unittest.skip('skip')
    def test_07random(self):  ## TODO too long to test
        self.dut.PIXEL_CONF["EnInj"] = (np.random.randint(2, size=(self.dut.COL, self.dut.ROW)) == 1)
        self.util_set_pixel(bit="EnInj",defval=None)
        pixlist=np.argwhere(self.dut.PIXEL_CONF["EnInj"])
        print("=====sim=====eninj",len(pixlist))

        self.dut.start_inj()
        print("=====sim=====random",end="")
        raw=self.dut.get_data_now()
        for i in range(10000):
            raw=np.append(raw,self.dut.get_data_now())
            print(len(raw),end="")
            if len(raw) >= 3*len(pixlist):
                break
        print('-',i,end="")
        dat=interpreter.raw2list(raw)          
        pix=dat[dat['col']<self.dut.COL]
        print(len(pix),pix)
        for i,h in enumerate(pixlist):
            tdac=self.dut.PIXEL_CONF['Trim'][h[0],h[1]]
            print(i, h, tdac, pix[i], [((24-tdac)*4-1)&0x3F,((24-tdac)*4)&0x3F,((24-tdac)*4+1)&0x3F])
            p=pix[np.bitwise_and(pix['col']==h[0],pix['row']==h[1])]
            self.assertEqual(len(p),1)
            self.assertTrue(
                ( (p['te']-p['le']) & 0x3F ) in [
                ((24-tdac)*4-2)&0x3F,((24-tdac)*4-1)&0x3F,((24-tdac)*4)&0x3F,((24-tdac)*4+1)&0x3F])

if __name__ == '__main__':
    if len(sys.argv)>1:
        TestEnInjLd.extra_defines=[sys.argv.pop()]
    unittest.main()