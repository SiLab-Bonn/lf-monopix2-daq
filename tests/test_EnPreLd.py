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


class TestEnPreLd(test_Monopix2.TestMonopix2):
    hit_file=[
            #hit_file,     ## test02     
            #hit_file[:-4]+"02.csv", ## test02  
            #hit_file[:-4]+"03.csv", ## test03  
            ]

    def test_00init(self):
        self.dut.init()
        ###### set preamp OFF
        self.dut.PIXEL_CONF["EnPre"].fill(False)
        self.dut['CONF_SR']['EnColRO'].setall(True)
        self.util_set_pixel(bit="EnPre",defval=False)
        
        ####### set inj ON
        self.dut.PIXEL_CONF["EnInj"].fill(True)
        self.dut['CONF_SR']['InjEnCol'].setall(False) ## active low
        self.util_set_pixel(bit="EnInj",defval=True)

        self.dut.set_inj_all(inj_n=1,inj_width=2,inj_delay=10)
        #self.dut.set_timestamp640(src="mon")
        self.dut.set_monoread(sync_timestamp=False)

    #@unittest.skip('skip')
    def test_01all0(self):
        self.dut.start_inj()
        for i in range(50):
            ready=self.dut["inj"].is_ready
            if ready:
                break
        raw=self.dut.get_data_now()  
        self.assertEquals(len(raw),0)

    #@unittest.skip('skip')
    def test_02pix(self):
        col=5
        row=20
        inj_width=self.dut["inj"].WIDTH
        self.dut.PIXEL_CONF["EnPre"][col,row]=True

        bit="EnPre"
        defval=False
        ClkBX=self.dut['CONF']['ClkBX'].tovalue()
        ClkOut=self.dut['CONF']['ClkOut'].tovalue()
        self.dut['CONF']['ClkOut'] = 0
        self.dut['CONF']['ClkBX'] = 0
        arg=np.argwhere(self.dut.PIXEL_CONF[bit]!=defval)
        uni=np.unique(arg[:,0]//2)
        self.dut['CONF_SR']["{0:s}Ld".format(bit)] = 0
        for dcol in uni:
            self.dut['CONF_SR']['EnSRDCol'].setall(False)
            self.dut['CONF_SR']['EnSRDCol'][dcol]=True
            self.dut['CONF']['Ld_Cnfg'] = 0
            self.dut['CONF'].write()
            self.dut['CONF_SR'].write()
            while not self.dut['CONF_SR'].is_ready:
                pass
            ## set pix_config
            self.dut['CONF_DC']['Col0'] = bitarray.bitarray(list(self.dut.PIXEL_CONF[bit][dcol*2+1,:]))
            self.dut['CONF_DC']['Col1'] = bitarray.bitarray(list(self.dut.PIXEL_CONF[bit][dcol*2,::-1]))
            self.dut['CONF']['Ld_Cnfg'] = 1
            self.dut['CONF'].write()
            self.dut['CONF_DC'].write()
            while not self.dut['CONF_DC'].is_ready:
                pass
            self.dut['CONF']['Ld_Cnfg'] = 0
            print("=====sim=====",dcol)
        self.dut['CONF_SR']["{0:s}Ld".format(bit)] = 1
        self.dut['CONF']['ClkOut'] = ClkOut  ###Readout OFF
        self.dut['CONF']['ClkBX'] = ClkBX
        self.dut['CONF'].write()

        self.dut.start_inj()
        raw=self.dut.get_data_now()
        print("=====sim=====",end=" ")
        for i in range(50):
            raw=np.append(raw,self.dut.get_data_now())
            if len(raw) == 3:
                break
            print(i,len(raw))
        dat=interpreter.raw2list(raw)
        for r in raw:
            print(hex(r),end=" ")
        print(len(raw))
        pix=dat[dat["col"]<self.dut.COL]
        mon=dat[dat["col"]==interpreter.COL_MON]
        print("=====sim=====",pix)

        self.assertEqual(len(pix),1)
        self.assertEqual(pix["col"],col)
        self.assertEqual(pix["row"],row)
        self.assertEqual((pix["te"]-pix["le"]) & 0x3F,inj_width)

    #@unittest.skip('skip')
    def test_03rowmax(self):
        inj_width=self.dut["inj"].WIDTH
        self.dut.PIXEL_CONF["EnPre"].fill(False)
        self.dut.PIXEL_CONF["EnPre"][:,self.dut.ROW-1]=True

        bit="EnPre"
        ClkBX=self.dut['CONF']['ClkBX'].tovalue()
        ClkOut=self.dut['CONF']['ClkOut'].tovalue()
        self.dut['CONF']['ClkOut'] = 0
        self.dut['CONF']['ClkBX'] = 0
        uni=[0] ## short cut
        self.dut['CONF_SR']["{0:s}Ld".format(bit)] = 0
        dcol=0 ## shortcut
        self.dut['CONF_SR']['EnSRDCol'].setall(True) 
        self.dut['CONF']['Ld_Cnfg'] = 0
        self.dut['CONF'].write()
        self.dut['CONF_SR'].write()
        while not self.dut['CONF_SR'].is_ready:
            pass
        ## set pix_config
        self.dut['CONF_DC']['Col0'] = bitarray.bitarray(list(self.dut.PIXEL_CONF[bit][dcol*2+1,:]))
        self.dut['CONF_DC']['Col1'] = bitarray.bitarray(list(self.dut.PIXEL_CONF[bit][dcol*2,::-1]))
        self.dut['CONF']['Ld_Cnfg'] = 1
        self.dut['CONF'].write()
        self.dut['CONF_DC'].write()
        while not self.dut['CONF_DC'].is_ready:
            pass
        self.dut['CONF']['Ld_Cnfg'] = 0
        print("=====sim===== rowmaxON")
        self.dut['CONF_SR']["{0:s}Ld".format(bit)] = 1
        self.dut['CONF']['ClkOut'] = ClkOut  ###Readout OFF
        self.dut['CONF']['ClkBX'] = ClkBX
        self.dut['CONF'].write()
        
        self.dut.start_inj()
        raw=self.dut.get_data_now()
        print("=====sim=====",end="")
        for i in range(1000):
            raw=np.append(raw,self.dut.get_data_now())
            if len(raw) == 3*self.dut.COL:
                break
            print(len(raw),end="")
        print(len(raw),"-",i)
        dat=interpreter.raw2list(raw)
        #for r in raw:
        #    print hex(r),
        #print len(raw)
        pix=dat[dat["col"]<self.dut.COL]
        mon=dat[dat["col"]==interpreter.COL_MON]
        print("=====sim=====",pix)

        self.assertEqual(len(pix),self.dut.COL)
        for i,p in enumerate(pix):
            self.assertEqual(p["col"],i)
            self.assertEqual(p["row"],self.dut.ROW-1)
            self.assertEqual((p["te"]-p["le"])&0x3F, inj_width&0x3F)

    #@unittest.skip('skip')
    def test_04colmax(self):
        inj_width=self.dut["inj"].WIDTH
        self.dut.PIXEL_CONF["EnPre"].fill(False)
        print("=====sim=====EnPre", self.dut.PIXEL_CONF["EnPre"][:,self.dut.ROW-1])
        self.dut.PIXEL_CONF["EnPre"][self.dut.COL-1,:]=True
        self.util_set_pixel(bit="EnPre",defval=False)

        self.dut.start_inj()
        raw=self.dut.get_data_now()
        print("=====sim=====raw",end="")
        flg=0
        pre_len=len(raw)
        for i in range(5000):
            raw=np.append(raw,self.dut.get_data_now())
            if len(raw) == 3*self.dut.ROW:
                break
            if pre_len==len(raw):
                flg=flg+1
            else:
                pre_len=len(raw)
                flg=0
            if flg>10:
                break
            print(len(raw))
        print(len(raw),"-",i,flg)
        dat=interpreter.raw2list(raw)
        #for r in raw:
        #    print hex(r),
        pix=dat[dat["col"]<self.dut.COL]
        pix=pix[np.argsort(pix['row'])]
        mon=dat[dat["col"]==interpreter.COL_MON]
        print("=====sim=====", pix)
        self.assertEqual(len(pix),self.dut.ROW)
        for i,p in enumerate(pix):
            self.assertEqual(p["col"],self.dut.COL-1)
            self.assertEqual(p['row'],i)
            self.assertEqual((p["te"]-p["le"])&0x3F,inj_width)

    @unittest.skip('skip')
    def test_05random(self):  ####TOTO this takes too long
        inj_width=self.dut["inj"].WIDTH
        self.dut.PIXEL_CONF["EnPre"]= (np.random.randint(2, size=(self.dut.COL, self.dut.ROW)) == 1) 
        hitin=np.argwhere(self.dut.PIXEL_CONF["EnPre"])

        bit="EnPre"
        ClkBX=self.dut['CONF']['ClkBX'].tovalue()
        ClkOut=self.dut['CONF']['ClkOut'].tovalue()
        self.dut['CONF']['ClkOut'] = 0
        self.dut['CONF']['ClkBX'] = 0
        self.dut['CONF_SR']["{0:s}Ld".format(bit)] = 0
        for dcol in range(self.dut.COL//2):
            self.dut['CONF_SR']['EnSRDCol'].setall(False)
            self.dut['CONF_SR']['EnSRDCol'][dcol]=True
            self.dut['CONF']['Ld_Cnfg'] = 0
            self.dut['CONF'].write()
            self.dut['CONF_SR'].write()
            while not self.dut['CONF_SR'].is_ready:
                pass
            ## set pix_config
            self.dut['CONF_DC']['Col0'] = bitarray.bitarray(list(self.dut.PIXEL_CONF[bit][dcol*2+1,:]))
            self.dut['CONF_DC']['Col1'] = bitarray.bitarray(list(self.dut.PIXEL_CONF[bit][dcol*2,::-1]))
            self.dut['CONF']['Ld_Cnfg'] = 1
            self.dut['CONF'].write()
            self.dut['CONF_DC'].write()
            while not self.dut['CONF_DC'].is_ready:
                pass
            self.dut['CONF']['Ld_Cnfg'] = 0
            print("=====sim=====",dcol)
        self.dut['CONF_SR']["{0:s}Ld".format(bit)] = 1
        self.dut['CONF']['ClkOut'] = ClkOut  ###Readout OFF
        self.dut['CONF']['ClkBX'] = ClkBX
        self.dut['CONF'].write()

        self.dut.start_inj()
        raw=self.dut.get_data_now()
        print("=====sim=====05 raw")
        flg=0
        pre_len=len(raw)
        for i in range(5000):
            raw=np.append(raw,self.dut.get_data_now())
            if len(raw) == 3*len(hitin):
                break
            elif flg>10:
                break
            elif pre_len==len(raw):
                flg=flg+1
            else:
                pre_len=len(raw)
                flg=0
            print(len(raw),3*len(hitin))
        print(len(raw),"-",i,flg)
        dat=interpreter.raw2list(raw)
        #for r in raw:
        #    print hex(r)
        pix=dat[dat["col"]<self.dut.COL]
        mon=dat[dat["col"]==interpreter.COL_MON]
        print("=====sim=====pix",pix)
        self.assertEqual(len(pix), len(hitin))
        for i,h in enumerate(hitin):
            print(hitin[i,:])
            p=pix[np.bitwise_and(pix["col"]==h[0],pix["row"]==h[1])]
            self.assertEqual(len(p),1)
            self.assertEqual((p[0]["te"]-p[0]["le"]) & 0x3F,inj_width)
        
if __name__ == '__main__':
    if len(sys.argv)>1:
        TestEnPreLd.extra_defines=[sys.argv.pop()]
    unittest.main()