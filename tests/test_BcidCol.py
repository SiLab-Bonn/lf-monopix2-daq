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

class TestBcidCol(test_Monopix2.TestMonopix2):
    hit_file=[
            HIT_FILE0,               ## test01     
            HIT_FILE0[:-4]+"02.csv", ## test02  
            HIT_FILE0[:-4]+"03.csv", ## test03  
            HIT_FILE0[:-4]+"04.csv", ## test04  
            ]

    def test_00init(self):
        self.dut.init()
        ##########################
        #### set all preamp ON, inj row0 ON
        self.dut.PIXEL_CONF["EnPre"].fill(True)
        self.util_set_pixel(bit="EnPre",defval=True)

        self.dut.PIXEL_CONF["EnInj"].fill(False)
        self.dut.PIXEL_CONF["EnInj"][:,0]=True
        self.dut['CONF_SR']['InjEnCol'].setall(False) ## active low
        self.util_set_pixel(bit="EnInj",defval=0)

        self.dut.set_inj_all(inj_n=1,inj_width=40,inj_delay=100)
        #self.dut.set_timestamp640(src="mon")
        self.dut.set_monoread(sync_timestamp=False)

    #@unittest.skip('skip')
    def test_01(self):
        ################
        #### 1. HIT in diagnal pixels, different ToT, LE=same 
        self.util_startHIT()
        hitin=self.util_nextHit(n_data="all")
        raw= self.dut.get_data_now()
        print("=====sim=====",end='')
        flg=0
        pre_len=len(raw)
        for i in range(1000):
            raw=np.append(raw,self.dut.get_data_now())
            if len(raw)==len(hitin)*3:
                break
            if pre_len==len(raw):
                flg=flg+1
            else:
                flg=0
                pre_len=len(raw)
            if flg>10:
                break
        print(len(raw),"-",i,end='')
        dat=interpreter.raw2list(raw,delete_noise=False)
        pix=dat[dat['col']<self.dut.COL]
        print("n_dat", len(dat),end='') 
        print("n_pix", len(pix),end='')
        
        pix=pix[np.argsort(pix["row"])]
        for i,p in enumerate(pix):
            print (i, p, hitin[i])
            self.assertEqual(p['col'], hitin[i]['col'])
            self.assertEqual(p['row'], hitin[i]['row'])
            self.assertEqual((p['te']-p['le']) & 0x3F, hitin[i]["tot"] & 0x3F)
            self.assertEqual(p['te'], (pix[0]['te']+i) & 0x3F)
            self.assertEqual(p['le'], pix[0]['le'])

    #@unittest.skip('skip') 
    def test_02random(self): ##TODO investigate why row of first data is 0
        #############################
        ## 2.1 enable random number of col
        self.dut['CONF_SR']["EnColRO"]=random.randint(0,0xFFFFFFFFFFFFFF)
        self.dut['CONF']['ClkOut'] = 0  ###Readout OFF
        self.dut['CONF']['ClkBX'] = 0
        self.dut['CONF']['Ld_Cnfg'] = 0
        self.dut['CONF'].write()
        self.dut['CONF_SR'].write()
        while not self.dut['CONF_SR'].is_ready:
            pass
        self.dut['CONF']['ClkOut'] = 1
        self.dut['CONF']['ClkBX'] = 1
        self.dut['CONF'].write()
        ##############################
        ### create hits to all column (LE=1bxid step, TE=same)
        self.util_startHIT()
        hitin=np.empty(self.dut.COL,dtype=[
            ("timestamp","u4"),("col","u1"),("row","u2"),("tot","u4"),("flg","u1")])
        for i in range(self.dut.COL):
            bxid,col,row,tot = self.util_nextHit()
            print(i,col,row,self.dut['CONF_SR']["EnColRO"][col])
            if self.dut['CONF_SR']["EnColRO"][col] is True:
                hitin["flg"][i]=1
            else:
                hitin["flg"][i]=0
            hitin["timestamp"][i]=bxid
            hitin["col"][i]=col
            hitin["row"][i]=row
            hitin["tot"][i]=tot
        hitin1=hitin[hitin["flg"]==1]
        hitin0=hitin[hitin["flg"]==0]
        raw= self.dut.get_data_now()
        print("=====sim=====random",end='')
        flg=0
        pre_len=len(raw)
        for i in range(1000):
            raw=np.append(raw,self.dut.get_data_now())
            if len(raw)==len(hitin1)*3:
                break
            if pre_len==len(raw):
                flg=flg+1
            else:
                flg=0
                pre_len=len(raw)
            if flg>10:
                break
            print("{0:d}:{1:d}/{2:d}".format(flg,len(raw),len(hitin1)*3))
        print("=====sim=====random",i,end="")
        dat=interpreter.raw2list(raw,delete_noise=False)       
        pix=dat[dat['col']<self.dut.COL]
        pix=pix[np.argsort(pix["col"])]
        print("-",len(pix),len(hitin1))

        self.assertEqual(len(pix),len(hitin1))
        for i,p in enumerate(pix):
            logging.info("i={0:d} p={1:s} h={2:s}".format(i, str(p), str(hitin1[i])))
            self.assertEqual(p['col'],hitin1[i]['col'])
            self.assertEqual(p['row'],hitin1[i]['row'])
            self.assertEqual( (p['te']-p['le']) & 0x3F, hitin1[i]["tot"] & 0x3F)
            self.assertEqual(p['le'], (pix[0]['le']-pix[0]["col"]+hitin1[i]['col']) & 0x3F)
            self.assertEqual(p['te'], pix[0]['te'])
        
        #############################
        ## 2.2 set all col ON  (readout LE,TE from disabled/now enabled pix)
        self.dut['data_rx'].set_en(False)
        self.dut['CONF_SR']["EnColRO"]=0xFFFFFFFFFFFFFF
        self.dut['CONF']['ClkOut'] = 0  ###Readout OFF
        self.dut['CONF']['ClkBX'] = 0
        self.dut['CONF']['Ld_Cnfg'] = 0
        self.dut['CONF'].write()
        self.dut['CONF_SR'].write()
        while not self.dut['CONF_SR'].is_ready:
            pass
        self.dut['CONF']['ClkOut'] = 1
        self.dut['CONF']['ClkBX'] = 1
        self.dut['CONF'].write()
        self.dut['data_rx'].set_en(True)
        raw= self.dut.get_data_now()
        print("=====sim=====02-2 ",end="")
        for i in range(1000):
            raw=np.append(raw,self.dut.get_data_now())
            if len(raw)==len(hitin0)*3:
                break
            print(len(raw),end="")            
        print(len(raw),"-",i)
        dat=interpreter.raw2list(raw,delete_noise=False)       
        pix=dat[dat['col']<self.dut.COL]
        print(pix)
        print(hitin0)
        #############################
        ## le,te should be all 0 --> bxid stopped properly
        self.assertEqual(len(pix),len(hitin0))
        for i,h in enumerate(hitin0):
            p=pix[np.bitwise_and(pix["col"]==h["col"],pix["row"]==h["row"])]
            print(i, h, p)
            self.assertEqual(len(p), 1)
            self.assertEqual(p[0]['te'], 0)
            self.assertEqual(p[0]['le'], 0)

    #@unittest.skip('skip')
    def test_03resetbcid(self):
        #######
        ### 3. Readout: colmax ON
        self.dut['CONF_SR']["EnColRO"]=0x80000000000000
        self.dut['CONF']['ClkOut'] = 0  ###Readout OFF
        self.dut['CONF']['ClkBX'] = 0
        self.dut['CONF']['Ld_Cnfg'] = 0
        self.dut['CONF'].write()
        self.dut['CONF_SR'].write()
        while not self.dut['CONF_SR'].is_ready:
            pass
        self.dut['CONF']['ClkOut'] = 1  ###Readout ON
        self.dut['CONF']['ClkBX'] = 1
        self.dut['CONF'].write()
        ########
        ## 3.1 HIT in colmax pixels same LE, shorter ToT in higher row 
        self.util_startHIT()
        raw= self.dut.get_data_now()
        print("=====sim=====03-1",end="")
        for i in range(1000):
            raw=np.append(raw,self.dut.get_data_now())
            if len(raw)>=10*3:
                self.util_pauseHIT()
                break
            print(len(raw),end="")
        print("-",i,end="")
        dat=interpreter.raw2list(raw,delete_noise=False)       
        pix=dat[dat['col']<self.dut.COL]
        pix=pix[np.argsort(pix['row'])]
        self.assertEqual(len(pix),10)
        for i,p in enumerate(pix):
            bxid,col,row,tot=self.util_nextHit()
            print("=====sim=====",bxid,col,row,tot,p)
            self.assertEqual(p['col'],col)
            self.assertEqual(p['row'],row)
            self.assertEqual( (p['te']-p['le']) & 0x3F, tot & 0x3F)
            self.assertEqual(p['le']&0x3F, (pix[0]['le']+i) & 0x3F)
        ####
        ## 3.2 HIT during ResetBcid=1
        self.dut['CONF']['ResetBcid'] = 1
        self.dut['CONF'].write()
        self.util_resumeHIT()
        raw= self.dut.get_data_now()
        print("=====sim=====03-2",end="")
        for i in range(1000):
            raw=np.append(raw,self.dut.get_data_now())
            if len(raw)>=10*3:
                self.util_pauseHIT()
                break
            print(len(raw),end="")
        print("-",i,end="")
        dat=interpreter.raw2list(raw,delete_noise=False)       
        pix=dat[dat['col']<self.dut.COL]
        pix=pix[np.argsort(pix['row'])]
        print(len(pix))
        self.assertEqual(len(pix),10)
        for i,p in enumerate(pix):
            bxid, col, row, tot=self.util_nextHit()
            self.assertEqual(p['col'],col)
            self.assertEqual(p['row'],row)
            self.assertEqual(p['te'], 0)
            self.assertEqual(p['le'], 0)
        ########
        ## 3.3 ResetBcid=0, HIT in col55 and 0 but readout only col55
        self.dut['CONF']['ResetBcid'] = 0
        self.dut['CONF'].write()   
        self.util_resumeHIT()
        raw= self.dut.get_data_now()
        print("=====sim=====03-3",end="")
        for i in range(1000):
            raw=np.append(raw,self.dut.get_data_now())
            if len(raw)>=10*3:
                self.util_pauseHIT()
                break
            print(len(raw), end="")
        print("-",i, end="")
        dat=interpreter.raw2list(raw, delete_noise=False)       
        pix=dat[dat['col']<self.dut.COL]
        pix=pix[np.argsort(pix['row'])]
        print(pix, end="")
        self.assertEqual(len(pix),10)
        ii=0
        ij=0
        hitin=np.empty(10,dtype=[
            ("timestamp","u4"),("col","u1"),("row","u2"),("tot","u4"),("flg","u1")])
        for i in range(20):
            bxid,col,row,tot=self.util_nextHit()
            if col==0:
                hitin[ij]['timestamp']=bxid
                hitin[ij]['col']=col
                hitin[ij]['row']=row
                hitin[ij]['tot']=tot
                ij=ij+1
            else:
                p=pix[ii]
                self.assertEqual(p['col'],col)
                self.assertEqual(p['row'],row)
                self.assertEqual( (p['te']-p['le']) & 0x3F, tot & 0x3F)
                self.assertEqual(p['le'], (pix[0]['le']+ii) & 0x3F)
                ii=ii+1
        hitin=hitin[np.argsort(hitin["row"])]
        ########
        ## 3.4 Readout col55, 0 ON, readout old data from col0 and new data from col55 and 0
        self.dut['data_rx'].set_en(False)
        self.dut['CONF_SR']["EnColRO"]=0x80000000000001
        self.dut['CONF']['ClkOut'] = 0  ###Readout OFF
        self.dut['CONF']['ClkBX'] = 0
        self.dut['CONF']['Ld_Cnfg'] = 0
        self.dut['CONF'].write()
        self.dut['CONF_SR'].write()
        while not self.dut['CONF_SR'].is_ready:
            pass
        self.dut['CONF']['ClkOut'] = 1  ###Readout ON
        self.dut['CONF']['ClkBX'] = 1
        self.dut['CONF'].write()
        self.dut['data_rx'].set_en(True)
        self.util_resumeHIT()
        raw= self.dut.get_data_now()
        print("=====sim=====03-4",end="")
        for i in range(100):
            raw=np.append(raw,self.dut.get_data_now())
            if len(raw)>=30*3:
                self.util_pauseHIT()
                break
            print(len(raw),end="")
        print("-",i,end="")
        dat=interpreter.raw2list(raw,delete_noise=False)       
        pix=dat[dat['col']<self.dut.COL]
        pix[:10]=pix[:10][np.argsort(pix[:10]['row'])]
        print(pix[:10])
        self.assertEqual(len(pix),30)
        for i,p in enumerate(pix[:10]):
            self.assertEqual(p['col'],hitin[i]['col'])
            self.assertEqual(p['row'],hitin[i]['row'])
            self.assertEqual(p['te'], 0)
            self.assertEqual(p['le'], 0)
        pix=pix[10:30][np.argsort(pix[10:30][["row","col"]])]
        print(pix)
        for i,p in enumerate(pix):
            bxid, col, row, tot=self.util_nextHit()
            self.assertEqual(p['col'],col)
            self.assertEqual(p['row'],row)
            self.assertEqual(p['te'], pix[0]["te"])
            self.assertEqual(p['le'], (0x40+pix[0]["te"]-tot)&0x3F)

    #@unittest.skip('skip')
    def test_04restart0(self):
        #######
        ### Readout: col0,1,max-1,max ON
        self.dut['CONF_SR']["EnColRO"]=0xC0000000000003
        self.dut['CONF']['ClkOut'] = 0  ###Readout OFF
        self.dut['CONF']['ClkBX'] = 0
        self.dut['CONF']['Ld_Cnfg'] = 0
        self.dut['CONF'].write()
        self.dut['CONF_SR'].write()
        while not self.dut['CONF_SR'].is_ready:
            pass
        self.dut['CONF']['ClkOut'] = 1  ###Readout ON
        self.dut['CONF']['ClkBX'] = 1
        self.dut['CONF'].write()

        ####################
        ## Rest Bcid during hits are created
        ## Hit in col0,1 row0->339, col55,54 row339->0, LE increased by 1, ToT=1
        self.util_startHIT()
        hitin=self.util_nextHit(n_data="all")
        self.dut['CONF']['ResetBcid'] = 1
        self.dut['CONF'].write()
        self.dut['CONF']['ResetBcid'] = 0
        self.dut['CONF'].write()
        raw= self.dut.get_data_now()
        print("=====sim=====04",end="")
        for i in range(1000):
            raw=np.append(raw,self.dut.get_data_now())
            if len(raw)>=len(hitin)*3:
                self.util_pauseHIT()
                break
            print(len(raw),end="")
        print("-",i,end="")
        dat=interpreter.raw2list(raw,delete_noise=False)       
        pix=dat[dat['col']<self.dut.COL]
        print("=====sim=====rst", len(pix),len(hitin))
        #self.assertEqual(len(pix),len(hitin))
        for i,h in enumerate(hitin):
            p=pix[np.bitwise_and(pix["col"]==h["col"],pix["row"]==h["row"])]
            self.assertEqual(len(p),1)
            print("=====sim=====rst",i, p,h, end="")
            if i==0:
                le0=p[0]['le']
                bxid0=h['bxid']
                flg_rst=0
                print("first hit",end="")
            else:
                if p[0]['le'] == ((h['bxid']-bxid0+le0) & 0x3F) and (flg_rst==0 or flg_rst==2):
                    print("flg",flg_rst,end="")
                    self.assertTrue(True)
                elif p[0]['le']==0 and flg_rst==0: ## reset asserted
                    flg_rst=1
                    print("flg",flg_rst,end="")
                    self.assertTrue(True)
                elif p[0]['le']==0 and flg_rst==1: ## reset asserted
                    flg_rst=1
                    print("reset",end="")
                    self.assertTrue(True)
                elif p[0]['le']==1 and flg_rst==1: ## reset released
                    flg_rst=2
                    print("flg",flg_rst,end="")
                    le0=p[0]['le']
                    bxid0=h['bxid']
                    self.assertTrue(True)
                else:
                    print("ERROR",h['bxid']-bxid0+le0, "off",bxid0,le0,"flg",flg_rst,end="")
                    self.assertTrue(False)     
            if i==0:
                te0=p[0]['te']
                bxid_te0=h['bxid']+h['tot']
                flg_rst_te=0
                print("first hit")
            else:
                if p[0]['te']== ((h['bxid']+h["tot"]-bxid_te0+te0) & 0x3F) and (flg_rst_te==0 or flg_rst_te==2):
                    print("flg_te",flg_rst_te)
                    self.assertTrue(True)
                elif p[0]['te']==0 and flg_rst_te==0: ## reset asserted
                    flg_rst_te=1
                    te0=p[0]['te']
                    bxid_te0=h['bxid']+h['tot']
                    print("flg_te",flg_rst_te)
                    self.assertTrue(True)
                elif p[0]['te']==0 and flg_rst_te==1: ## reset asserted
                    flg_rst_te=1
                    print("reset")
                    self.assertTrue(True)
                elif p[0]['te']==1 and flg_rst_te==1: ## reset released
                    flg_rst_te=2
                    te0=p[0]['te']
                    bxid_te0=h['bxid']+h['tot']
                    print("flg_te",flg_rst_te)
                else:
                    print("ERROR_TE",h['bxid']+h["tot"]-bxid_te0+te0, "off",bxid_te0,te0,"flg",flg_rst_te)
                    self.assertTrue(False)
        
if __name__ == '__main__':
    if len(sys.argv)>1:
        TestBcidCol.extra_defines=[sys.argv.pop()]
    unittest.main()