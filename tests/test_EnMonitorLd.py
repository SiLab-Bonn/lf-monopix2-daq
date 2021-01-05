#
# ------------------------------------------------------------
# Copyright (c) All rights reserved
# SiLab, Institute of Physics, University of Bonn
# ------------------------------------------------------------
#
from __future__ import print_function
import unittest
import os
import sys
import yaml
import time
import bitarray
import numpy as np
import csv
import random
import logging

import monopix2_daq.monopix2_sim as monopix2
import monopix2_daq.analysis.interpreter_idx as interpreter
from monopix2_daq.sim.utils import cocotb_compile_and_run, cocotb_compile_clean
import test_Monopix2

HIT_FILE0 = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
           "tests/data/"+os.path.basename(os.path.abspath(__file__))[:-2].split("_")[0]+"_"+os.path.basename(os.path.abspath(__file__))[:-2].split("_")[-1]+"csv")

class TestEnMonitorLd(test_Monopix2.TestMonopix2):
    hit_file=[
            HIT_FILE0,     ## test01
            HIT_FILE0[:-4]+"02.csv",   ## test02 inject 9pixels
            HIT_FILE0[:-4]+"03.csv",    # test03
            ##hit_file[:-4]+"03.csv",   # test04 ##TODO csv has not implemented yet
            HIT_FILE0[:-4]+"04.csv",   # test05
            HIT_FILE0[:-4]+"04.csv",   # test06
            ]

    def test_00init(self):
        self.dut.init()
        #########################
        ### init all preamp, injection OFF, mon OFF (EnMonitorCol=ON)
        self.dut['CONF_SR']['EnColRO'].setall(True)
        self.dut['CONF_SR']['EnMonitorCol'].setall(True)
        self.dut.PIXEL_CONF["EnPre"].fill(True)
        self.util_set_pixel(bit="EnPre",defval=True)
    
        self.dut.PIXEL_CONF["EnMonitor"].fill(False)
        self.util_set_pixel(bit="EnMonitor",defval=False)

        #self.dut.set_inj_all(inj_n=1,inj_width=2,inj_delay=10)
        self.dut.set_timestamp640(src="mon")
        self.dut.set_monoread(sync_timestamp=False)

    #@unittest.skip("skip")
    def test_01All0(self):
        ##########################
        #### col=5,row=20 HIT
        self.util_startHIT()
        bxid,col,row,tot=self.util_nextHit()

        self.dut.logger.info("No HIT_OR, only pixel_data")
        raw=self.dut.get_data_now()
        for i in range(20):
            raw=np.append(raw,self.dut.get_data_now())
            self.dut.logger.info("{0:d}".format(len(raw)))
            if len(raw) == 3:
                self.util_pauseHIT()
                break
        print("=====sim=====raw",hex(raw[0]),hex(raw[1]),hex(raw[2]))
        dat=interpreter.raw2list(raw)
        print("=====sim=====dat",dat)
        pix=dat[dat["col"]<self.dut.COL]
        mon=dat[dat["col"]==interpreter.COL_MON]

        ## test result
        self.assertEqual(len(mon),0)
        self.assertEqual(len(pix),1)
        self.assertEqual(pix[0]["col"],col)
        self.assertEqual(pix[0]["row"],row)
        self.assertEqual((pix[0]["te"]-pix[0]["le"]) & 0x3F,tot & 0x3F)

    #@unittest.skip("skil")
    def test_02pix(self):
        col=5
        row=20
        self.dut.PIXEL_CONF["EnMonitor"].fill(False)
        self.dut.PIXEL_CONF["EnMonitor"][col,row]=True
        self.util_set_pixel(bit="EnMonitor",defval=False)
        self.dut['data_rx'].set_en(False)

        self.util_startHIT()
        hitin=self.util_nextHit("all")
        raw=self.dut.get_data_now()
        print("=====sim=====",end='')
        for i in range(50):
            raw=np.append(raw,self.dut.get_data_now())
            if len(raw) == 12:
                self.util_pauseHIT()
                break
        print(i,end='')
        dat=interpreter.raw2list(raw)
        for r in raw:
            print(hex(r),end='')
        print(len(raw))
        pix=dat[dat["col"]<self.dut.COL]
        mon=dat[dat["col"]==interpreter.COL_MON]
        print("=====sim=====mon",mon)
        print("=====sim=====pix",pix)

        ## test result
        self.assertEqual(len(mon),2*2)
        le=mon[mon["row"]==1]["timestamp"]
        te=mon[mon["row"]==0]["timestamp"]
        totin=hitin[np.bitwise_and(hitin["col"]==col,hitin["row"]==row)]["tot"]
        print('=====sim=====mon',te-le,totin)
        self.assertTrue( te[0]-le[0] in [totin[0]*16,totin[0]*16+1])
        self.assertTrue( te[1]-le[1] in [totin[1]*16,totin[1]*16+1])

    #@unittest.skip("skip")
    def test_03Col0(self):
        self.dut.PIXEL_CONF["EnMonitor"].fill(False)
        self.dut.PIXEL_CONF["EnMonitor"][0,:]=True
        self.util_set_pixel(bit="EnMonitor",defval=False)
        self.dut['data_rx'].set_en(False)
        ### set mono_read off
        self.dut['CONF']['ClkOut'] = 0
        self.dut['CONF']['ClkBX'] = 0

        self.util_startHIT()
        hitin=self.util_nextHit("all")
        totin=hitin[hitin["col"]==0]["tot"]
        raw=self.dut.get_data_now()
        print("=====sim=====",end='')
        flg=0
        pre_len=len(raw)
        for i in range(10000):
            raw=np.append(raw,self.dut.get_data_now())
            if len(raw) == 6*len(totin):
                self.util_pauseHIT()
                break
            if pre_len==len(raw):
                flg=flg+1
            else:
                pre_len=len(raw)
                flg=0
            if flg>10:
                break
            print(len(raw),"/",len(totin)*6)
        print(i,end='')
        dat=interpreter.raw2list(raw)
        #for r in raw:
        #    print hex(r),
        print(len(raw))
        pix=dat[dat["col"]<self.dut.COL]
        mon=dat[dat["col"]==interpreter.COL_MON]
        print("=====sim=====mon",mon)
        print("=====sim=====pix",pix)

        ## test result
        self.assertEqual(len(mon),len(totin)*2)
        le=mon[mon["row"]==1]["timestamp"]
        te=mon[mon["row"]==0]["timestamp"]
        print('=====sim=====mon',te-le,totin)
        for i,t in enumerate(totin):
            self.assertTrue(te[i]-le[i] in [t*16, t*16+1])

    @unittest.skip("skip")
    def test_04colmax(self): ##TODO csv has not implemented yet
        self.dut.PIXEL_CONF["EnMonitor"].fill(False)
        self.dut.PIXEL_CONF["EnMonitor"][self.dut.COL-1,:]=True
        self.util_set_pixel(bit="EnMonitor",defval=0)
        ### set mono_read off
        self.dut['data_rx'].set_en(False)
        self.dut['CONF']['ClkOut'] = 0
        self.dut['CONF']['ClkBX'] = 0

        self.util_startHIT()  ##TODO csv has not implemented yet
        hitin=self.util_nextHit("all")
        totin=hitin[hitin["col"]==self.dut.COL-1]["tot"]
        raw=self.dut.get_data_now()
        print("=====sim=====colmax",end='')
        flg=0
        pre_len=len(raw)
        for i in range(10000):
            raw=np.append(raw,self.dut.get_data_now())
            if len(raw) == 6*len(totin):
                self.util_pauseHIT()
                break
            if pre_len==len(raw):
                flg=flg+1
            else:
                pre_len=len(raw)
                flg=0
            if flg>10:
                break
            print(len(raw))
        print(i,end='')
        dat=interpreter.raw2list(raw)
        for r in raw:
            print(hex(r),end=" ")
        print(len(raw))
        pix=dat[dat["col"]<self.dut.COL]
        mon=dat[dat["col"]==interpreter.COL_MON]
        print("=====sim=====mon",mon)
        print("=====sim=====pix",pix)

        ## test result
        self.assertEqual(len(mon),len(totin)*2)
        le=mon[mon["row"]==1]["timestamp"]
        te=mon[mon["row"]==0]["timestamp"]
        print('=====sim=====mon',te-le,totin)
        for i,t in enumerate(totin):
            self.assertTrue(te[i]-le[i] in [t*16, t*16+1])

    #@unittest.skip("skip")
    def test_05Rowmax(self):
        self.dut.PIXEL_CONF["EnMonitor"].fill(False)
        self.dut.PIXEL_CONF["EnMonitor"][:,self.dut.ROW-1]=True
        self.util_set_pixel(bit="EnMonitor",defval=0)
        ### set mono_read off
        self.dut['data_rx'].set_en(False)
        self.dut['CONF']['ClkOut'] = 0
        self.dut['CONF']['ClkBX'] = 0

        self.util_startHIT()  
        hitin=self.util_nextHit("all")
        totin=hitin[hitin["row"]==self.dut.ROW-1]["tot"]
        raw=self.dut.get_data_now()
        print("=====sim=====rowmax",end='')
        flg=0
        pre_len=len(raw)
        for i in range(10000):
            raw=np.append(raw,self.dut.get_data_now())
            if len(raw) == 6*len(totin):
                self.util_pauseHIT()
                break
            if pre_len==len(raw):
                flg=flg+1
            else:
                pre_len=len(raw)
                flg=0
            if flg> 10:
                break
            print(len(raw))
        print(i)
        dat=interpreter.raw2list(raw)
        for r in raw:
            print(hex(r),end="")
        print(len(raw))
        pix=dat[dat["col"]<self.dut.COL]
        mon=dat[dat["col"]==interpreter.COL_MON]
        print("=====sim=====mon",mon)
        print("=====sim=====pix",pix)

        ## test result
        print("=====sim=====05",len(mon),len(totin)*2)
        le=mon[mon["row"]==1]["timestamp"]
        te=mon[mon["row"]==0]["timestamp"]
        print('=====sim=====05 mon',te-le)
        print('=====sim=====05 totin',totin)
        #print(np.argwhere((te-le)!=totin*16))
        self.assertEqual(len(mon),len(totin)*2)
        ###################################################
        ## allow tot*16 and tot*16+1 (1clk of 640MHz) 
        #flg=0
        for i, t in enumerate(totin):
            self.assertTrue(te[i]-le[i] in [t*16,t*16+1,t*16+2])
        #    if flg==0 and (te[i]-le[i]) == t*16:
        #        self.assertTrue(True)
        #    elif (te[i]-le[i]) == t*16+1:
        #        flg=1
        #        self.assertTrue(True)
        #    else:
        #        print('=====sim=====05 error in mon',t, te[i]-le[i])
        #        self.assertTrue(False)

    #@unittest.skip("skip")
    def test_06Row0(self):
        self.dut.PIXEL_CONF["EnMonitor"].fill(False)
        self.dut.PIXEL_CONF["EnMonitor"][:,0]=True
        self.util_set_pixel(bit="EnMonitor",defval=0)
        ### set mono_read off
        self.dut['data_rx'].set_en(False)
        self.dut['CONF']['ClkOut'] = 0
        self.dut['CONF']['ClkBX'] = 0

        self.util_startHIT()
        hitin=self.util_nextHit("all")
        totin=hitin[hitin["row"]==0]["tot"]
        raw=self.dut.get_data_now()
        print("=====sim=====colmax",end="")
        flg=0
        pre_len=len(raw)
        for i in range(10000):
            raw=np.append(raw,self.dut.get_data_now())
            if len(raw) == 6*len(totin):
                self.util_pauseHIT()
                break
            if pre_len==len(raw):
                flg=flg+1
            else:
                pre_len=len(raw)
                flg=0
            if flg> 10:
                break
            print(len(raw))
        print(i,end="")
        dat=interpreter.raw2list(raw)
        for r in raw:
            print(hex(r),end="")
        print(len(raw))
        pix=dat[dat["col"]<self.dut.COL]
        mon=dat[dat["col"]==interpreter.COL_MON]
        print("=====sim=====mon",mon)
        print("=====sim=====pix",pix)

        ## test result
        print("=====sim=====mon",len(mon),len(totin)*2)
        le=mon[mon["row"]==1]["timestamp"]
        te=mon[mon["row"]==0]["timestamp"]
        print('=====sim=====06 mon',te-le)
        print('=====sim=====06 totin',totin)
        self.assertEqual(len(mon),len(totin)*2)
        ###################################################
        ## allow tot*16 and tot*16+1 (1clk of 640MHz) 
        #flg=0
        for i, t in enumerate(totin):
            self.assertTrue(te[i]-le[i] in [t*16,t*16+1,t*16+2])
        #    if flg==0 and (te[i]-le[i]) == t*16:
        #        self.assertTrue(True)
        #    elif (te[i]-le[i]) == t*16+1:
        #        flg=1
        #        self.assertTrue(True)
        #    else:
        #        self.assertTrue(False)
    
if __name__ == '__main__':
    if len(sys.argv)>1:
        TestEnMonitorLd.extra_defines=[sys.argv.pop()]
    unittest.main()