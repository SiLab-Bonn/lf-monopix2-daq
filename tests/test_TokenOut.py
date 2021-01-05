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

class TestTokenOut(test_Monopix2.TestMonopix2):
    hit_file=[HIT_FILE0,
              HIT_FILE0[:-4]+"02.csv",
              HIT_FILE0[:-4]+"03.csv",
              HIT_FILE0[:-4]+"04.csv",
              HIT_FILE0[:-4]+"05.csv", #test05 (debug max)
              ]
    extra_defines= ["_CLK_HIT_160MHZ_"] #["_GATE_LEVEL_NETLIST_","_CLK_HIT_160MHZ_"]

    def test_00init(self):
        self.dut.init()
        #self.dut.set_inj_all(inj_n=inj_n,inj_delay=inj_delay,inj_width=inj_width)
        ##########################
        #### set all preamp ON
        self.dut.PIXEL_CONF["EnPre"].fill(True)
        self.util_set_pixel(bit="EnPre",defval=True)
        ## short proceedure
        read_width=8
        self.dut.set_monoread(sync_timestamp=False,start_freeze=16,start_read=32,
                              stop_read=32+read_width,stop_freeze=32+read_width+27+4+32,
                              stop=32+read_width+27+4+32+32,
                              read_shift=(27+4-1)*2+1,decode=True)

    #@unittest.skip('skip')
    def test_01pix(self):
        self.util_startHIT()
        hitin=self.util_nextHit(n_data="all")
        t0=self.dut['tb'].TIMESTAMP
        raw=self.dut.get_data_now()
        for i in range(100):
            t=self.dut['tb'].TIMESTAMP
            raw=np.append(raw,self.dut.get_data_now())
            if len(raw)==len(hitin)*3:
                break
            logging.info("reading data.. time={0:d} len={1:d}".format(t-t0,len(raw)) )
        raw=np.append(raw,self.dut.get_data_now())
        dat=interpreter.raw2list(raw,delete_noise=False)
        logging.info("hitin={0:d} dat={1:d} {2:s}".format(len(hitin),len(dat),str(dat)))
        for i,h in enumerate(hitin):
            self.assertEqual(dat[i]['col'],h['col'])
            self.assertEqual(dat[i]['row'],h['row'])
            hitin_le=(h['bxid'])//4 ## +1 is for !CLK40, note that it is not +2
            if (h['bxid'])%4==0:
                hitin_le=hitin_le
            hitin_te=(h['bxid']+h['tot'])//4
            if (h['bxid']+h['tot'])%4==0:
                hitin_te=hitin_te
            hitin_tot=(hitin_te-hitin_le) & 0x3F
            print("=====sim=====",i, "mod",(h['bxid'])%4,(h['bxid']+h['tot'])%4, end=" " )
            print("tot",(dat[i]["te"]-dat[i]["le"]) & 0x3F,hitin_le,hitin_te,"hitin_tot",hitin_tot)
            ##self.assertEqual((dat[i]["te"]-dat[i]["le"]) & 0x3F, hitin_tot)

    #@unittest.skip('skip')
    def test_05twopix(self):      
        self.util_startHIT()
        hitin=self.util_nextHit(n_data="all")
        t0=self.dut['tb'].TIMESTAMP
        raw=self.dut.get_data_now()
        for i in range(100):
            t=self.dut['tb'].TIMESTAMP
            raw=np.append(raw,self.dut.get_data_now())
            if len(raw)==len(hitin)*3:
                break
            logging.info("reading data.. time={0:d} len={1:d}".format(t-t0,len(raw)) )
        raw=np.append(raw,self.dut.get_data_now())
        dat=interpreter.raw2list(raw,delete_noise=False)
        logging.info("hitin={0:d} dat={1:d}".format(len(hitin),len(dat)))
        print("=====sim=====",str(dat))
        for i,h in enumerate(hitin):
            self.assertEqual(dat[i]['col'],h['col'])
            self.assertEqual(dat[i]['row'],h['row'])
            hitin_le=(h['bxid'])//4
            #if (h['bxid'])%4==0:
            #    hitin_le=hitin_le
            hitin_te=(h['bxid']+h['tot'])//4
            #if (h['bxid']+h['tot'])%4==0:
            #    hitin_te=hitin_te
            hitin_tot=(hitin_te-hitin_le) & 0x3F
            #print("=====sim=====",i, "mod",(h['bxid'])%4,(h['bxid']+h['tot'])%4, end=" " )
            print("=====sim===== tot",i,(dat[i]["te"]-dat[i]["le"]) & 0x3F,"hitin_tot",hitin_tot)
            self.assertTrue((dat[i]["te"]-dat[i]["le"]) & 0x3F in  [hitin_tot, hitin_tot+1,] )

    #@unittest.skip('skip')
    def test_02twopix(self):
        self.dut.set_monoread(sync_timestamp=False,start_freeze=16,start_read=32,stop_read=34,
            stop_freeze=34+27+3+20,stop=34+27+3+20+16,read_shift=(27+4-1)*2+1,)
        self.util_startHIT()
        hitin=self.util_nextHit(n_data="all")
        t0=self.dut['tb'].TIMESTAMP
        raw=self.dut.get_data_now()
        for i in range(100):
            t=self.dut['tb'].TIMESTAMP
            raw=np.append(raw,self.dut.get_data_now())
            if len(raw)==len(hitin)*3:
                break
            logging.info("reading data.. time={0:d} len={1:d}".format(t-t0,len(raw)) )
        raw=np.append(raw,self.dut.get_data_now())
        dat=interpreter.raw2list(raw,delete_noise=False)
        logging.info("hitin={0:d} dat={1:d}".format(len(hitin),len(dat)))
        print("=====sim=====",str(dat))
        for i,h in enumerate(hitin):
            self.assertEqual(dat[i]['col'],h['col'])
            self.assertEqual(dat[i]['row'],h['row'])
            hitin_le=(h['bxid'])//4
            #if (h['bxid'])%4==0:
            #    hitin_le=hitin_le
            hitin_te=(h['bxid']+h['tot'])//4
            #if (h['bxid']+h['tot'])%4==0:
            #    hitin_te=hitin_te
            hitin_tot=(hitin_te-hitin_le) & 0x3F
            #print("=====sim=====",i, "mod",(h['bxid'])%4,(h['bxid']+h['tot'])%4, end=" " )
            print("=====sim===== tot",i,(dat[i]["te"]-dat[i]["le"]) & 0x3F,"hitin_tot",hitin_tot)
            self.assertTrue((dat[i]["te"]-dat[i]["le"]) & 0x3F in  [hitin_tot, hitin_tot+1,] )

    #@unittest.skip('skip')
    def test_03read(self):
        self.util_startHIT()
        hitin=self.util_nextHit(n_data="all")
        t0=self.dut['tb'].TIMESTAMP
        raw=self.dut.get_data_now()
        flg=0
        pre_len=len(raw)
        for i in range(100):
            t=self.dut['tb'].TIMESTAMP
            raw=np.append(raw,self.dut.get_data_now())
            if len(raw)==len(hitin)*3:
                break
            elif flg>10:
                break
            elif len(raw)==pre_len:
                flg=flg+1
            else:
                flg=0
                pre_len=len(raw)
            logging.info("reading data.. time={0:d} len={1:d}".format(t-t0,len(raw)) )
        dat=interpreter.raw2list(raw, delete_noise=False)
        logging.info("hitin={0:d} dat={1:d}".format(len(hitin),len(dat)))
        print("=====sim=====read",str(dat))
        for i in range(0,len(hitin)):
            if i in [12]:
                j=i+1
            elif i in [13]:
                j=i-1
            else:
                j=i
            print("=====sim=====i",i,"col",dat[j]['col'],hitin[i]['col'],"row",dat[j]['row'],hitin[i]['row'])
            self.assertEqual(dat[j]['col'],hitin[i]['col'])
            self.assertEqual(dat[j]['row'],hitin[i]['row'])
            hitin_le=(hitin[i]['bxid'])//4
            hitin_te=(hitin[i]['bxid']+hitin[i]['tot'])//4
            hitin_tot=(hitin_te-hitin_le) & 0x3F
            #print("=====sim=====",i, "mod",(h['bxid'])%4,(h['bxid']+h['tot'])%4, end=" " )
            print("=====sim===== tot",(dat[j]["te"]-dat[j]["le"]) & 0x3F,"hitin_tot",hitin_tot)
            self.assertTrue((dat[j]["te"]-dat[j]["le"]) & 0x3F in  [hitin_tot, hitin_tot+1,] )

    #@unittest.skip('skip')
    def test_04freeze(self):
        self.util_startHIT()
        hitin=self.util_nextHit(n_data="all")
        t0=self.dut['tb'].TIMESTAMP
        raw=self.dut.get_data_now()
        flg=0
        pre_len=len(raw)
        for i in range(100):
            t=self.dut['tb'].TIMESTAMP
            raw=np.append(raw,self.dut.get_data_now())
            if len(raw)==len(hitin)*3:
                break
            elif flg>10:
                break
            elif len(raw)==pre_len:
                flg=flg+1
            else:
                flg=0
                pre_len=len(raw)
            logging.info("reading data.. time={0:d} len={1:d}".format(t-t0,len(raw)) )
        dat=interpreter.raw2list(raw, delete_noise=False)
        logging.info("hitin={0:d} dat={1:d}".format(len(hitin),len(dat)))
        print("=====sim=====read",str(dat))
        for i in range(0,len(hitin)):
            if i in [8,10,12,14, 24,26,28,30]:
                j=i+1
            elif i in [9,11,13,15, 25,27,29,31]:
                j=i-1
            else:
                j=i
            print("=====sim=====i",i,"col",dat[j]['col'],hitin[i]['col'],"row",dat[j]['row'],hitin[i]['row'])
            self.assertEqual(dat[j]['col'],hitin[i]['col'])
            self.assertEqual(dat[j]['row'],hitin[i]['row'])
            hitin_le=(hitin[i]['bxid'])//4
            hitin_te=(hitin[i]['bxid']+hitin[i]['tot'])//4
            hitin_tot=(hitin_te-hitin_le) & 0x3F
            #print("=====sim=====",i, "mod",(h['bxid'])%4,(h['bxid']+h['tot'])%4, end=" " )
            print("=====sim===== tot",(dat[j]["te"]-dat[j]["le"]) & 0x3F,"hitin_tot",hitin_tot)
            self.assertTrue((dat[j]["te"]-dat[j]["le"]) & 0x3F in  [hitin_tot, hitin_tot+1,] )
     
if __name__ == '__main__':
    if len(sys.argv)>1:
        TestTokenOut.extra_defines.append(sys.argv.pop())
    unittest.main()
