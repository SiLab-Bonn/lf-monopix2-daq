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

class TestFreeze(test_Monopix2.TestMonopix2):
    hit_file=[
            HIT_FILE0,     ## test01
            HIT_FILE0,     ## test02
            HIT_FILE0[:-4]+"03.csv",   ## reverse diagnal
            ]

    def test_00init(self):
        self.dut.init()
        self.dut['CONF']['SLOW_RX']='1'
        self.dut['CONF'].write()
        #########################
        ### init preamp:all ON(col5 50 ON), injection off
        self.dut['CONF_SR']['EnColRO'].setall(False)
        self.dut['CONF_SR']['EnColRO'][5]=True
        self.dut['CONF_SR']['EnColRO'][50]=True
        self.dut.PIXEL_CONF["EnPre"].fill(True)
        self.util_set_pixel(bit="EnPre",defval=True)

        #############################
        ## set "default" freeze setting
        self.dut.set_monoread(sync_timestamp=False,)
        #self.dut.set_timestamp640("mon")

    #@unittest.skip("skip")
    def test_01col5(self):
        ##########################
        #### col=5
        self.util_startHIT()
        hitin=self.util_nextHit(n_data="all")
        raw=self.dut.get_data_now()
        for i in range(100):
            raw=np.append(raw,self.dut.get_data_now())
            if len(raw) == 3*len(hitin):
                self.util_pauseHIT()
                break
        dat=interpreter.raw2list(raw,delete_noise=False)
        print("=====sim=====dat",dat)
        pix=dat[dat["col"]<self.dut.COL]
        #pix=pix[np.argsort(pix['row'])]
        ## test result
        self.assertEqual(len(pix),len(hitin))
        
        start_freeze=self.dut['data_rx'].CONF_START_FREEZE
        stop_freeze=self.dut['data_rx'].CONF_STOP_FREEZE
        print("=====sim=====freeze", start_freeze, stop_freeze)
        le0=pix[0]["le"]
        bxid0=hitin[0]["bxid"]
        token0=hitin[0]["bxid"]+hitin[0]["tot"]
        for i,p in enumerate(pix):
            print("=====sim=====pix", i, p["cnt"],"col",p["col"],"row",p["row"],(p["te"]-p["le"]) & 0x3F, hitin[i]["tot"] & 0x3F,end=" ")
            self.assertEqual(p["col"], hitin[i]["col"])
            self.assertEqual(p["row"], hitin[i]["row"])
            self.assertEqual((p["te"]-p["le"]) & 0x3F, hitin[i]["tot"] & 0x3F)
            print("le",(hitin[i]["bxid"]-bxid0+le0) & 0x3F, p["le"], end=" ")
            print("hitin_le",token0, end=" ")
            self.assertEqual(p["le"], (hitin[i]["bxid"]-bxid0+le0) & 0x3F)
            if i in [0,8,10,12,14,16,18,20,22]:
                self.assertEqual(p["cnt"],0)
                token0=hitin[i]["bxid"]+hitin[i]["tot"]
                ts0=p['timestamp']
                print("seed", token0, ts0, "start", token0+start_freeze, "stop", token0+stop_freeze)
            elif (hitin[i]["bxid"]+hitin[i]["tot"] > token0+start_freeze+2 and self.option!="max" \
                 and   hitin[i]["bxid"]+hitin[i]["tot"] <= token0+stop_freeze+2) \
                 or (hitin[i]["bxid"]+hitin[i]["tot"] > token0+start_freeze+3 and self.option=="max" \
                 and   hitin[i]["bxid"]+hitin[i]["tot"] <= token0+stop_freeze+3):
                print("freeze", token0, hitin[i]["bxid"]+hitin[i]["tot"], ts0, p['timestamp'],end=" ")
                print("ts", hitin[i]["bxid"]+hitin[i]["tot"]-token0, (p['timestamp']-ts0)/16)
                #print bxid0+stop_freeze >= hitin[i]["bxid"]+hitin[i]["tot"]
                self.assertTrue( hitin[i]["bxid"]+hitin[i]["tot"]-token0 < (p['timestamp']-ts0)/16)
            elif hitin[i]["bxid"]+hitin[i]["tot"] <= token0+start_freeze+2:
                print("not-freeze", token0, hitin[i]["bxid"]+hitin[i]["tot"], ts0, p['timestamp'],end=" ")
                print("ts", hitin[i]["bxid"]+hitin[i]["tot"]-token0, (p['timestamp']-ts0)/16)
                self.assertTrue(hitin[i]["bxid"]+hitin[i]["tot"]-token0 == (p['timestamp']-ts0)/16
                               or (p['timestamp']-ts0)/16==0)

    #@unittest.skip("skip")
    def test_02noFreeze(self):
        start_freeze= 0xFFFE
        stop_freeze=self.dut['data_rx'].CONF_STOP_FREEZE 
        self.dut['data_rx'].CONF_START_FREEZE = start_freeze
        #########################
        ## no freeze signal
        self.util_startHIT()
        hitin=self.util_nextHit(n_data="all")
        raw=self.dut.get_data_now()
        for i in range(100):
            raw=np.append(raw,self.dut.get_data_now())
            if len(raw) == 3*len(hitin):
                self.util_pauseHIT()
                break
        dat=interpreter.raw2list(raw,delete_noise=False)
        print("=====sim=====dat",dat)
        pix=dat[dat["col"]<self.dut.COL]
        ## test result
        self.assertEqual(len(pix),len(hitin))
        print("=====sim=====assert", start_freeze, stop_freeze)
        for i,p in enumerate(pix):
            print(i,p["cnt"],(p["te"]-p["le"]) & 0x3F,hitin[i]["tot"] & 0x3F,end="")
            self.assertEqual(p["col"],hitin[i]["col"])
            self.assertEqual(p["row"],hitin[i]["row"])
            self.assertEqual((p["te"]-p["le"]) & 0x3F,hitin[i]["tot"] & 0x3F)
            if i in [0,8,10,12,14,16,18,20,22]:
                token0=hitin[i]["bxid"]+hitin[i]["tot"]
                ts0=p['timestamp']
                print("seed", token0, "start", token0+start_freeze, "stop", token0+stop_freeze)
                self.assertEqual(p["cnt"],0)
            else:
                print("not-freeze", token0, hitin[i]["bxid"]+hitin[i]["tot"], ts0, p['timestamp'],end=" ")
                print("ts", hitin[i]["bxid"]+hitin[i]["tot"]-token0, (p['timestamp']-ts0)/16)
                self.assertTrue(hitin[i]["bxid"]+hitin[i]["tot"]-token0 == (p['timestamp']-ts0)/16 or (p['timestamp']-ts0)/16==0)

    @unittest.skip("skip")
    def test_03AllCol(self): ##TODO analysis is not completed
        ##########################
        #### all col=ON
        self.dut['CONF_SR']['EnColRO'].setall(True)
        self.dut['CONF_SR']['InjEnCol'].setall(True) ## active low
        self.dut['CONF_SR']['EnMonitorCol'].setall(False)
        self.dut['CONF_SR']['EnSRDCol'].setall(False)
        self.dut['CONF']['Ld_Cnfg'] = 0
        self.dut['CONF']['ClkOut'] = 0
        self.dut['CONF']['ClkBX'] = 0
        self.dut['CONF']['Rst'] = 1
        self.dut['CONF'].write()
        self.dut['CONF_SR'].write()
        while not self.dut['CONF_SR'].is_ready:
            pass
        self.dut['CONF']['ClkOut'] = 1
        self.dut['CONF']['ClkBX'] = 1
        self.dut['CONF']['Rst'] = 0
        self.dut['CONF'].write()
        start_freeze= 90
        self.dut['data_rx'].CONF_START_FREEZE = start_freeze
        stop_freeze=self.dut['data_rx'].CONF_STOP_FREEZE 

        ##########################
        #### create hits
        self.util_startHIT()
        hitin=self.util_nextHit(n_data="all")
        raw=self.dut.get_data_now()
        print("=====sim=====raw",len(raw))
        pre_len=len(raw)
        flg=0
        for i in range(2000):
            raw=np.append(raw,self.dut.get_data_now())
            if len(raw) == 3*len(hitin):
                self.util_pauseHIT()
                break
            if len(raw)==pre_len:
                flg=flg+1
            else:
                flg=0
                pre_len=len(raw)
            if flg>10:
                self.util_pauseHIT()
                break
            print(i,"len",len(raw),"flg",flg)

        print("raw_i",i)
        dat=interpreter.raw2list(raw,delete_noise=False)
        print("=====sim=====dat",dat)
        pix=dat[dat["col"]<self.dut.COL]
        np.save("tmp.np",pix)

        ## test result
        self.assertEqual(len(pix),len(hitin))
        
        stop_freeze=127
        start_freeze=90
        print("=====sim=====assert", start_freeze, stop_freeze)
        le0=pix[np.bitwise_and(pix['col']==hitin[0]['col'],pix['row']==hitin[0]['row'])][0]['le']
        bxid0=hitin[0]["bxid"]
        pre_token=hitin[0]["bxid"]+hitin[0]["tot"]
        ts0=pix[np.bitwise_and(pix['col']==hitin[0]['col'],pix['row']==hitin[0]['row'])][0]["timestamp"]
        print(0, pix[np.bitwise_and(pix['col']==hitin[0]['col'],pix['row']==hitin[0]['row'])][0],end="")
        print(pre_token, ts0, bxid0) 
    
        for i,h in enumerate(hitin[1:100]):
            p=pix[np.bitwise_and(pix['col']==h['col'],pix['row']==h['row'])]
            print(i,"p",p)
            p=p[0]
            pix["timestamp"]=(pix["timestamp"]-ts0)//16+bxid0
            #print("tot",p["cnt"],(p["te"]-p["le"]) & 0x3F,h["tot"] & 0x3F,
            self.assertEqual((p["te"]-p["le"]) & 0x3F,h["tot"] & 0x3F)
            #print("le",(h["bxid"]-bxid0+le0) & 0x3F, p["le"],
            self.assertEqual(p["le"], (h["bxid"]-bxid0+le0) & 0x3F)
            
            #### TODO too difficult
            if h["bxid"]+h["tot"] > pre_token+start_freeze+1 \
                    and   h["bxid"]+h["tot"] <= pre_token+stop_freeze+1:
                print("freeze", "pre_token", pre_token, "te",h["bxid"]+h["tot"], end="")
                print("token",p['timestamp'],end="")
                print("diff_te", h["bxid"]+h["tot"]-pre_token, "diff_token",p['timestamp']-pre_token)
                print("---",h["bxid"]+h["tot"] < p['timestamp'])
                pre_token = pre_token+stop_freeze+1
                #self.assertTrue(h["bxid"]+h["tot"]-pre_token < (p['timestamp']-ts0)/16)
                stop_freeze=102+37 ##TODO this number be differ
                start_freeze=102

            elif h["bxid"]+h["tot"] > pre_token+stop_freeze+1:
                print("after freeze", "pre_token", pre_token, "te",h["bxid"]+h["tot"], end="")
                print("token", p['timestamp'],end="")
                print("diff_te", h["bxid"]+h["tot"]-pre_token, "diff_token",p['timestamp']-pre_token)
                print("---",h["bxid"]+h["tot"]== p['timestamp'])
                #self.assertTrue(h["bxid"]+h["tot"]-pre_token == (p['timestamp']-ts0)/16)
                pre_token=p['timestamp']
                stop_freeze=127
                start_freeze=90
            else:
                print("before freeze", "pre_token",pre_token,"token", p['timestamp'])
                print("---",pre_token==p['timestamp'])
                stop_freeze=stop_freeze+37
                start_freeze=90
                #self.assertTrue((p['timestamp']-ts0)/16==0)

if __name__ == '__main__':
    if len(sys.argv)>1:
        TestFreeze.extra_defines=[sys.argv.pop()]
    unittest.main()
