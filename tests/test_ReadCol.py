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

class TestReadCol(test_Monopix2.TestMonopix2):

    hit_file=[
        HIT_FILE0,     ## test01

        HIT_FILE0[:-4]+"02.csv", ## test02
        HIT_FILE0[:-4]+"02.csv", ## test02
        HIT_FILE0[:-4]+"02.csv", ## test02
        HIT_FILE0[:-4]+"02.csv", ## test02

        HIT_FILE0[:-4]+"02.csv", ## test03
        HIT_FILE0[:-4]+"02.csv", ## test03
        HIT_FILE0[:-4]+"02.csv", ## test03
        HIT_FILE0[:-4]+"02.csv", ## test03
        HIT_FILE0[:-4]+"02.csv", ## test03

        #HIT_FILE0[:-4]+"03.csv", ## test04
        ]

    def test_00init(self):
        self.dut.init()
        #inj_width=128
        #inj_delay=100
        #inj_n=1
        self.dut.set_monoread(sync_timestamp=False)
        #self.dut.set_inj_all(inj_n=inj_n,inj_delay=inj_delay,inj_width=inj_width)
        ##########################
        #### set all preamp ON
        self.dut.PIXEL_CONF["EnPre"].fill(True)
        self.util_set_pixel(bit="EnPre",defval=True)

    #@unittest.skip('skip')
    def test_01pix(self):
        self.util_startHIT()
        hitin=self.util_nextHit(n_data="all")
        t0=self.dut['tb'].TIMESTAMP
        raw=self.dut.get_data_now()
        for i in range(100):
            t=self.dut['tb'].TIMESTAMP
            raw=np.append(raw,self.dut.get_data_now())
            if t-t0 > (hitin[-1]['bxid']+hitin[-1]['tot'])*16:
                break
            logging.info("reading data.. time={0:d} len={1:d}".format((t-t0)>>4,len(raw)))
        raw=np.append(raw,self.dut.get_data_now())
        dat=interpreter.raw2list(raw,delete_noise=False)
        logging.info("hitin={0:d} dat={1:d} {2:s}".format(len(hitin),len(dat),str(dat)))
        for i,h in enumerate(hitin):
            p=dat[np.bitwise_and(dat['col']==h['col'],dat['row']==h['row'])]
            self.assertEqual(len(p),1)
            self.assertEqual((p[0]["te"]-p[0]["le"]) & 0x3F, h['tot'] & 0x3F)

    #@unittest.skip('skip')
    def test_02delay(self):
        if self.option=="max":
            dlist=[1, random.randint(2,29), 30, 4]
        else:
            dlist=[0,random.randint(1,29), 30, 4]
        for delay in dlist:
            print("=====sim===== delay",delay)
            self.dut['data_rx'].CONF_STOP_FREEZE =252+8+8+(27+delay-1)+8
            self.dut['data_rx'].CONF_STOP=252+8+8+(27+delay-1)+16
            self.dut['data_rx'].READ_SHIFT = (27+delay-1)*2+1

            self.dut['CONF_SR']['DelayROConf']=delay
            self.dut['CONF']['ClkOut'] = 0 
            self.dut['CONF']['ClkBX'] = 0
            self.dut['CONF']['Ld_Cnfg'] = 0
            self.dut['CONF'].write()
            self.dut['CONF_SR'].write()
            while not self.dut['CONF_SR'].is_ready:
                pass 
            self.dut['CONF']['ClkOut'] = 1 
            self.dut['CONF']['ClkBX'] = 1
            self.dut['CONF'].write()

            self.util_startHIT()
            hitin=self.util_nextHit(n_data="all")
            #t0=self.dut['tb'].TIMESTAMP
            raw=self.dut.get_data_now()
            for i in range(100):
                #t=self.dut['tb'].TIMESTAMP
                if len(raw)==3*len(hitin):
                    break
                raw=np.append(raw,self.dut.get_data_now())

                logging.info("reading data.. len={0:d}".format(len(raw)))
            dat=interpreter.raw2list(raw,delete_noise=False)
            logging.info("hitin={0:d} dat={1:d} {2:s}".format(len(hitin),len(dat),str(dat)))
            for i,h in enumerate(hitin):
                p=dat[np.bitwise_and(dat['col']==h['col'],dat['row']==h['row'])]
                if i==0:
                    le0=p[0]['le']
                self.assertEqual(len(p),1)
                self.assertEqual((p[0]["te"]-p[0]["le"]) & 0x3F, h['tot'] & 0x3F)
                self.assertEqual( (p[0]['le']-le0) & 0x3F,(h['bxid']-hitin[0]['bxid'])&0x3F)

    #@unittest.skip('skip')
    def test_03ReadStop(self):
        delay=self.dut['CONF_SR']['DelayROConf'].tovalue()
        for read_width in [5,6,7,9,8]:
            logging.info("read_width={0:d}".format(read_width))
            self.dut['data_rx'].CONF_STOP_READ = 252+8+read_width
            self.dut['data_rx'].CONF_STOP_FREEZE = 252+8+read_width+(27+delay-1)+8
            self.dut['data_rx'].CONF_STOP = 252+8+read_width+(27+delay-1)+16

            self.util_startHIT()
            hitin=self.util_nextHit(n_data="all")
            raw=self.dut.get_data_now()
            for i in range(100):
                raw=np.append(raw,self.dut.get_data_now())
                if len(raw)==3*len(hitin):
                    break
                logging.info("reading data.. len={0:d}".format(len(raw)))
            dat=interpreter.raw2list(raw,delete_noise=False)
            logging.info("hitin={0:d} dat={1:d} {2:s}".format(len(hitin),len(dat),str(dat)))
            for i,h in enumerate(hitin):
                p=dat[np.bitwise_and(dat['col']==h['col'],dat['row']==h['row'])]
                if i==0:
                    le0=p[0]['le']
                self.assertEqual(len(p),1)
                self.assertEqual((p[0]["te"]-p[0]["le"]) & 0x3F, h['tot'] & 0x3F)
                self.assertEqual( (p[0]['le']-le0) & 0x3F, (h['bxid']-hitin[0]['bxid'])&0x3F)

    @unittest.skip('skip')
    def test_04randomhits(self): ##TODO write analysis!!
        self.util_startHIT()
        hitin=self.util_nextHit(n_data="all")
        t0=self.dut['tb'].TIMESTAMP
        raw=self.dut.get_data_now()
        print("=====sim=====",end="")
        for i in range(10000):
            t=self.dut['tb'].TIMESTAMP
            raw=np.append(raw,self.dut.get_data_now())
            if t-t0 > hitin[-1]['bxid']*16:
                break
            print("{0:d}-{1:d}".format((t-t0)>>4,len(raw)),end="")
        print("-",i)
        dat=interpreter.raw2list(raw,delete_noise=False)
        print("=====sim=====",len(hitin),len(dat),dat)
        np.save("/tmp/dat.npy",dat)  ##TODO write analysis!!
        #for i,h in enumerate(hitin):
        #    self.assertTrue(np.all(dat["col"]==5))
        #    self.assertTrue(np.all((dat["te"]-dat["le"]) & 0x3F == 128 & 0x3F))
        #    self.assertTrue(np.all(dat["row"]==20))
     

if __name__ == '__main__':
    if len(sys.argv)>1:
        TestReadCol.extra_defines=[sys.argv.pop()]
    unittest.main()



