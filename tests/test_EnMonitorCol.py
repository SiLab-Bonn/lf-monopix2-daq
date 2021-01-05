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
import logging

import monopix2_daq.monopix2_sim as monopix2
import monopix2_daq.analysis.interpreter_idx as interpreter
import test_Monopix2
HIT_FILE0 = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
           "tests/data/"+os.path.basename(os.path.abspath(__file__))[:-2].split("_")[0]+"_"+os.path.basename(os.path.abspath(__file__))[:-2].split("_")[-1]+"csv")

class TestEnMonitorCol(test_Monopix2.TestMonopix2):
    hit_file=[
            HIT_FILE0,
            HIT_FILE0[:-4]+"02.csv",
            HIT_FILE0[:-4]+"03.csv",
            HIT_FILE0[:-4]+"04.csv",
            HIT_FILE0[:-4]+"05.csv",
            HIT_FILE0[:-4]+"03.csv"
            ]

    def test_00init(self):
        self.dut.init()
        ##########################
        #### set all preamp ON mon ON
        #self.util_shiftphaseHIT(True)
        self.dut.PIXEL_CONF["EnPre"].fill(True)
        self.dut.PIXEL_CONF["EnMonitor"].fill(True)
        self.dut['CONF_SR']['EnMonitorLd']=0 # active low
        self.util_set_pixel(bit="EnPre",defval=True)
        self.dut['CONF_SR']['EnMonitorLd']=1

        self.dut.set_monoread(sync_timestamp=False)
        self.dut.set_timestamp640("mon")

    #@unittest.skip("skip")
    def test_01col5disabled(self):
        #### AnalogHit at col=6,row=19
        ## get TokOut HIGH when a hit comes but no HIT_OR
        self.dut["data_rx"].set_en(False) 
        print("=====sim=====01 start HIT",end='')
        self.util_startHIT()
        print("=====sim=====01 token",end='')
        for i in range(20):
            token=self.dut["tb"].get_TokOut_PAD()
            print(token,end='')
            if token == "1":
                self.util_pauseHIT()
                break
        self.assertEqual(token,"1")
        size=self.dut["fifo"].FIFO_INT_SIZE
        self.assertEqual(size,0)   ### no HIT_OR

        ## get TokOut LOW when data_rx run
        self.dut["data_rx"].set_en(True)
        for i in range(20):
            size=self.dut["fifo"].FIFO_INT_SIZE
            print(size,end='')
            if size == 3:
                break
        raw=self.dut.get_data_now()
        dat=interpreter.raw2list(raw)
        print("=====sim=====01 size",size)
        print("=====sim=====01 dat",end='')
        for r in raw:
            print(hex(r),end='')
        print("\n",dat)

        bxid, col, row, tot = self.util_nextHit()
        self.assertEqual(size,3)
        token=self.dut["tb"].get_TokOut_PAD()
        self.assertEqual(token,"0")    ## finished readout
        self.assertEqual(dat[0]['col'],col)
        self.assertEqual(dat[0]['row'],row)
        self.assertEqual((dat[0]['te']-dat[0]['le']) & 0x3F , tot & 0x3F)
    
    #@unittest.skip("skip")
    def test_02col5(self):
        ################### 
        ## AnalogHit at col=5,row=20
        self.dut["data_rx"].set_en(False) 
        self.util_startHIT()
        for i in range(20):
            size=self.dut["fifo"].FIFO_INT_SIZE
            print(size,end='')
            if size == 6:
                self.util_pauseHIT()
                break
        raw=self.dut.get_data_now()
        dat=interpreter.raw2list(raw)
        print("=====sim=====02 hit",size)
        print("=====sim=====02 raw",end='')
        for r in raw:
            print(hex(r),end='')
        print("\n",dat)

        token=self.dut["tb"].get_TokOut_PAD()
        self.assertEqual(token,"1")
        self.assertEqual(size,6)   ### HITOR
        
        self.assertTrue(np.all(dat["col"]==interpreter.COL_MON))
        bxid, col, row, tot = self.util_nextHit()
        hit_or=dat[dat["row"]==0]["timestamp"]-dat[dat["row"]==1]["timestamp"]
        self.assertTrue(hit_or[0] in [tot*16, tot*16+1])

        ## get TokOut LOW when data_rx run
        self.dut["data_rx"].set_en(True)
        raw=self.dut.get_data_now()
        for i in range(20):
            raw=np.append(raw, self.dut.get_data_now())
            print(len(raw),end='')
            if len(raw) == 3:
                break
        dat=interpreter.raw2list(raw)
        print("=====sim=====02 dat",dat)
        token=self.dut["tb"].get_TokOut_PAD()
        self.assertEqual(token,"0")

        self.assertEqual(len(dat),1)
        self.assertEqual(dat[0]['col'],col)
        self.assertEqual(dat[0]['row'],row)
        self.assertEqual((dat[0]['te']-dat[0]['le']) & 0x3F , tot & 0x3F)

    #@unittest.skip('skip')
    def test_03all1(self):
        self.dut['CONF_SR']["EnMonitorCol"].setall(True)
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

        ### inject 1-by-1 to row0
        self.util_startHIT()
        flg=0
        raw=self.dut.get_data_now()
        pre_len=len(raw)
        for i in range(10000):
            raw=np.append(raw,self.dut.get_data_now())
            print(len(raw),end=' ')
            if len(raw) == 9*self.dut.COL:
                self.util_pauseHIT()
                break
            elif flg>10:
                break
            elif len(raw)==pre_len:
                flg=flg+1
            else:
                flg=0
                pre_len=len(raw)
        dat=interpreter.raw2list(raw)
         
        te=dat[np.bitwise_and(dat["row"]==0,dat['col']==interpreter.COL_MON)]
        le=dat[np.bitwise_and(dat["row"]==1,dat['col']==interpreter.COL_MON)]
        print("=====sim=====03 ts_tot",te["timestamp"]-le["timestamp"])       
        pix=dat[dat['col']<self.dut.COL]
        hitin=np.empty(self.dut.COL,dtype=dat.dtype)
        for i in range(self.dut.COL):
              hitin["timestamp"][i], hitin["col"][i], hitin["row"][i], hitin["index"][i] = self.util_nextHit()

        print("=====sim=====03 pix_tot",hitin["index"]*16)
        print("=====sim=====03 assert",te["timestamp"]-le["timestamp"])
        self.assertEqual(len(te), self.dut.COL)  
        self.assertEqual(len(le), self.dut.COL)
        self.assertTrue(np.all(np.bitwise_or(
                        (pix['te']-pix['le'] & 0x3F) == (hitin['index'] & 0x3F),
                        (pix['te']-pix['le'] & 0x3F) == (hitin['index']+1) & 0x3F)))   
        self.assertTrue(np.all(pix[["col","row"]]==hitin[["col","row"]]))
        self.assertTrue(np.all((pix['te']-pix['le'] & 0x3F) == (hitin['index'] & 0x3F)))

    #@unittest.skip('skip')
    def test_04colmax(self):
        self.dut['CONF_SR']["EnMonitorCol"].setall(False)
        self.dut['CONF_SR']["EnMonitorCol"][self.dut.COL-1]=1
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

        self.util_startHIT()
        print("=====sim=====",end='')
        for i in range(20):
            size=self.dut["fifo"].FIFO_INT_SIZE
            print(size,end='')
            if size == 12:
                self.util_pauseHIT()
                break
        print('-',i)
        raw=self.dut.get_data_now()
        dat=interpreter.raw2list(raw) 
        pix=dat[dat["col"]<self.dut.COL]
        mon=dat[dat["col"]==interpreter.COL_MON]
        print("=====sim=====",dat)
        
        bxid,col,row,tot=self.util_nextHit()
        bxid1,col1,row1,tot1=self.util_nextHit()
        self.assertEqual(size, 12)
        self.assertEqual(self.dut["tb"].ENMONITORCOL, 0x80000000000000)
        self.assertEqual(pix['col'][0],col)
        self.assertEqual(pix['col'][1],col1)
        self.assertEqual(pix['row'][0],row)
        self.assertEqual(pix['row'][1],row1)
        self.assertEqual(pix['le'][1]-pix['le'][0],bxid1-bxid)
        self.assertEqual((pix['te'][0]-pix['le'][0]) & 0x3F, tot)
        self.assertEqual((pix['te'][1]-pix['le'][1]) & 0x3F, tot1)
        print(mon[1]['timestamp']-mon[0]['timestamp'] , bxid1-bxid, tot1)
        self.assertTrue( "=====sim=====",mon[1]['timestamp']-mon[0]['timestamp'] in [tot1*16,tot1*16+1,tot1*16+2])

        ###############
        ## set Def_Conf==1
        self.dut['CONF']['Def_Conf'] = 1
        self.dut['CONF'].write()

        self.util_resumeHIT()
        print("=====sim=====",end='')
        for i in range(20):
            size=self.dut["fifo"].FIFO_INT_SIZE
            print(size,end='')
            if size == 6:
                self.util_pauseHIT()
                break
        print('-',i)
        raw=self.dut.get_data_now()
        dat=interpreter.raw2list(raw) 
        pix=dat[dat["col"]<self.dut.COL]
        mon=dat[dat["col"]==interpreter.COL_MON]
        print("=====sim=====",dat)
        
        bxid,col,row,tot=self.util_nextHit()
        bxid1,col1,row1,tot1=self.util_nextHit()
        self.assertEqual(size, 6)
        self.assertEqual(self.dut["tb"].ENMONITORCOL,0x00000000000000)
        self.assertEqual(pix['col'][0],37)
        self.assertEqual(pix['col'][1],37)
        self.assertEqual(pix['row'][0],15)
        self.assertEqual(pix['row'][1],15)
        self.assertEqual(pix['le'][1]-pix['le'][0],0)
        self.assertEqual((pix['te'][0]-pix['le'][0]) & 0x3F, 34)
        self.assertEqual((pix['te'][1]-pix['le'][1]) & 0x3F, 34)
        self.assertEqual(len(mon), 0)

        ###############
        ## set Def_Conf==0
        self.dut['CONF']['Def_Conf'] = 0
        self.dut['CONF'].write()
        self.util_resumeHIT()
        print("=====sim=====",end='')
        for i in range(20):
            size=self.dut["fifo"].FIFO_INT_SIZE
            print(size,end='')
            if size == 12:
                #self.util_pauseHIT()
                break
        print('-',i)
        raw=self.dut.get_data_now()
        dat=interpreter.raw2list(raw) 
        pix=dat[dat["col"]<self.dut.COL]
        mon=dat[dat["col"]==interpreter.COL_MON]
        print("=====sim=====",dat)
        
        bxid,col,row,tot=self.util_nextHit()
        bxid1,col1,row1,tot1=self.util_nextHit()
        self.assertEqual(size, 12)
        self.assertEqual(self.dut["tb"].ENMONITORCOL, 0x80000000000000)
        self.assertEqual(pix['col'][0],col)
        self.assertEqual(pix['col'][1],col1)
        self.assertEqual(pix['row'][0],row)
        self.assertEqual(pix['row'][1],row1)
        self.assertEqual(pix['le'][1]-pix['le'][0],bxid1-bxid)
        self.assertEqual((pix['te'][0]-pix['le'][0]) & 0x3F, tot)
        self.assertEqual((pix['te'][1]-pix['le'][1]) & 0x3F, tot1)
        self.assertTrue( mon[1]['timestamp']-mon[0]['timestamp'] in [tot1*16,tot1*16+1,tot1*16+2])

        self.util_nextHit()

    #@unittest.skip('skip')
    def test_05col0(self):
        self.dut["CONF"]["Rst"]=1
        self.dut['CONF_SR']["EnMonitorCol"].setall(False)
        self.dut['CONF_SR']["EnMonitorCol"][0]=1
        self.dut['CONF']['Ld_Cnfg'] = 0
        self.dut['CONF']['ClkOut'] = 0 
        self.dut['CONF']['ClkBX'] = 0
        self.dut['CONF'].write()
        self.dut['CONF_SR'].write()
        while not self.dut['CONF_SR'].is_ready:
            pass
        self.dut['CONF']['ClkOut'] = 1 
        self.dut['CONF']['ClkBX'] = 1
        self.dut["CONF"]["Rst"]=0
        self.dut['CONF'].write()
        self.util_startHIT()
        print("=====sim=====05",end=' ')
        for i in range(20):
            size=self.dut["fifo"].FIFO_INT_SIZE
            print(size,end='')
            if size == 12:
                self.util_pauseHIT()
                break
        print('-',i)
        raw=self.dut.get_data_now()
        dat=interpreter.raw2list(raw) 
        pix=dat[dat["col"]<self.dut.COL]
        mon=dat[dat["col"]==interpreter.COL_MON]
        print("=====sim=====05",dat)
        
        bxid,col,row,tot=self.util_nextHit()
        bxid1,col1,row1,tot1=self.util_nextHit()
        tot_or= max(bxid+tot,bxid1+tot1)-min(bxid,bxid1)
        self.assertEqual(size, 12)
        self.assertEqual(self.dut["tb"].ENMONITORCOL, 0x00000000000001)
        self.assertEqual(pix['col'][0],col1)
        self.assertEqual(pix['col'][1],col)
        self.assertEqual(pix['row'][0],row1)
        self.assertEqual(pix['row'][1],row)
        self.assertEqual(pix['le'][0]-pix['le'][1],bxid1-bxid)
        self.assertEqual((pix['te'][0]-pix['le'][0]) & 0x3F, tot1)
        self.assertEqual((pix['te'][1]-pix['le'][1]) & 0x3F, tot)
        self.assertTrue( mon[1]['timestamp']-mon[0]['timestamp'] in [tot_or*16, tot_or*16+1,tot1*16+2])

        ###############
        ## set ResetBcid 
        self.dut['CONF']['ResetBcid'] = 1
        self.dut['CONF'].write()   
        self.util_resumeHIT()
        print("=====sim=====05",end='')
        for i in range(20):
            size=self.dut["fifo"].FIFO_INT_SIZE
            print(size,end='')
            if size == 12:
                self.util_pauseHIT()
                break
        print('-',i)
        raw=self.dut.get_data_now()
        dat=interpreter.raw2list(raw) 
        pix=dat[dat["col"]<self.dut.COL]
        mon=dat[dat["col"]==interpreter.COL_MON]
        print("=====sim=====05",dat)
        
        bxid,col,row,tot=self.util_nextHit()
        bxid1,col1,row1,tot1=self.util_nextHit()
        tot_or= max(bxid+tot,bxid1+tot1)-min(bxid,bxid1)
        self.assertEqual(size, 12)
        self.assertEqual(self.dut["tb"].ENMONITORCOL,0x00000000000001)
        self.assertTrue( mon[1]['timestamp']-mon[0]['timestamp'] in [tot_or*16,tot_or*16+1,tot1*16+2])
        self.assertEqual(len(pix), 2)
        self.assertEqual(pix['col'][0],col1)
        self.assertEqual(pix['col'][1],col)
        self.assertEqual(pix['row'][0],row1)
        self.assertEqual(pix['row'][1],row)
        self.assertTrue(np.all(pix['le']==0))
        self.assertTrue(np.all(pix['te']==0))

        ###############
        ## set ResetBcid==0
        self.dut['CONF']['ResetBcid'] = 0
        self.dut['CONF'].write()
        self.util_resumeHIT()
        print("=====sim=====05",end='')
        for i in range(20):
            size=self.dut["fifo"].FIFO_INT_SIZE
            print(size,end='')
            if size == 12:
                #self.util_pauseHIT()
                break
        print('-',i)
        raw=self.dut.get_data_now()
        dat=interpreter.raw2list(raw) 
        pix=dat[dat["col"]<self.dut.COL]
        mon=dat[dat["col"]==interpreter.COL_MON]
        print("=====sim=====05",dat)
        
        bxid,col,row,tot=self.util_nextHit()
        bxid1,col1,row1,tot1=self.util_nextHit()
        tot_or= max(bxid+tot,bxid1+tot1)-min(bxid,bxid1)
        self.assertEqual(size, 12)
        self.assertEqual(self.dut["tb"].ENMONITORCOL, 0x00000000000001)
        self.assertEqual(pix['col'][0],col1)
        self.assertEqual(pix['col'][1],col)
        self.assertEqual(pix['row'][0],row1)
        self.assertEqual(pix['row'][1],row)
        self.assertEqual((pix['le'][0]-pix['le'][1])&0x3F,(bxid1-bxid)&0x3F)
        self.assertEqual((pix['te'][0]-pix['le'][0]) & 0x3F, tot1)
        self.assertEqual((pix['te'][1]-pix['le'][1]) & 0x3F, tot)
        self.assertTrue( mon[1]['timestamp']-mon[0]['timestamp'] in [tot_or*16, tot_or*16+1, tot1*16+2])
        self.util_nextHit()

    #@unittest.skip('skip')
    def test_06all0(self):
        self.dut['CONF_SR']["EnMonitorCol"].setall(False)
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
        
        ### inject 1-by-1 to row0
        self.util_startHIT()
        for i in range(300):
            size=self.dut["fifo"].FIFO_INT_SIZE
            print(size,end='')
            if size == 3*self.dut.COL:
                self.util_pauseHIT()
                break
        raw=self.dut.get_data_now()
        dat=interpreter.raw2list(raw)
         
        mon = dat[dat['col']==interpreter.COL_MON]
        print("=====sim=====06 mon",mon )   
        pix=dat[dat['col']<self.dut.COL]
        print("=====sim=====06 pix_tot",pix['te']-pix['le'] & 0x3F)
        hitin=np.empty(self.dut.COL,dtype=dat.dtype)
        for i in range(self.dut.COL):
              hitin["timestamp"][i], hitin["col"][i], hitin["row"][i], hitin["index"][i] = self.util_nextHit()
        self.assertEqual(len(mon),0)
        self.assertEqual(size, 3*self.dut.COL)
        print("=====sim=====assert",pix[["col","row"]]==hitin[["col","row"]])
        print("=====sim=====pix",pix[["col","row"]])
        print("=====sim=====hit",hitin[["col","row"]])
        self.assertTrue(np.all(pix[["col","row"]]==hitin[["col","row"]]))
        print("=====sim=====06 hit_tot", hitin['index'] & 0x3F)
        print("=====sim=====06 tot    ", (pix['te']-pix['le'] & 0x3F))
        self.assertTrue(np.all(np.bitwise_or(
                        (pix['te']-pix['le'] & 0x3F) == (hitin['index'] & 0x3F),
                        (pix['te']-pix['le'] & 0x3F) == (hitin['index']+1) & 0x3F)))               

if __name__ == '__main__':
    if len(sys.argv)>1:
        TestEnMonitorCol.extra_defines=[sys.argv.pop()]
    unittest.main()