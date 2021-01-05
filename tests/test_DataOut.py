#
# ------------------------------------------------------------
# Copyright (c) All rights reserved
# SiLab, Institute of Physics, University of Bonn
# ------------------------------------------------------------
#
from __future__ import print_function
import unittest
import os
from monopix2_daq.sim.utils import cocotb_compile_and_run, cocotb_compile_clean ## TODO this can be from basil..
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

class TestDataOut(test_Monopix2.TestMonopix2):

    def test_00init(self):
        self.dut.init()
        #############
        ## all preamp row0,rowmax0 ON injON encol-ON
        self.dut['CONF_SR']['EnTestPattern'] = 0
        self.dut['CONF_SR']['InjEnCol'] = 0x0 ## active low
        self.dut.PIXEL_CONF["EnInj"].fill(True)
        self.util_set_pixel(bit="EnInj",defval=True)
        self.dut.PIXEL_CONF["EnPre"].fill(False)
        self.dut.PIXEL_CONF["EnPre"][:,0]=True
        self.dut.PIXEL_CONF["EnPre"][:,self.dut.ROW-1]=True
        self.util_set_pixel(bit="EnPre",defval=0)
        self.dut.PIXEL_CONF["EnMonitor"].fill(True)  ## HIT_OR except colmax
        self.dut.PIXEL_CONF["EnMonitor"][self.dut.COL-1,:]=False
        self.util_set_pixel(bit="EnMonitor",defval=True)

        self.dut.set_inj_all(inj_n=1,inj_width=2,inj_delay=10)
        #self.dut.set_timestamp640(src="mon")
        self.dut.set_monoread(sync_timestamp=False)

    #@unittest.skip('skip')
    def test_01all1(self):
        ######
        ## EnColRO all ON
        self.dut.start_inj()
        hitin=np.argwhere(np.bitwise_and(self.dut.PIXEL_CONF["EnInj"],self.dut.PIXEL_CONF["EnPre"]))
        print("=====sim=====hitin",hitin)
        raw=self.dut.get_data_now()
        pre_len=len(raw)
        flg=0
        for i in range(1000):
            raw=np.append(raw,self.dut.get_data_now())
            if len(raw) == 3*len(hitin):
                break
            print(len(raw),"/",3*len(hitin))
            if len(raw)==pre_len:
                flg=flg+1
            else:
                pre_len=len(raw)
                flg=0
            if flg>10:
                break
        print("-",i)
        dat=interpreter.raw2list(raw)
        print("=====sim=====dat",dat)
        pix=dat[dat['col']<self.dut.COL]
        self.assertEqual(len(pix), len(hitin))
        for h in hitin:
            p=pix[np.bitwise_and(pix['col']==h[0],pix['row']==h[1])]
            tot=(p['te']-p['le']) & 0x3F
            print(h,tot)
            self.assertEqual(len(p),1)
            self.assertEqual(tot[0],2)

    #@unittest.skip('skip')
    def test_02all0(self):
        ######
        ## EnColRO all OFF
        self.dut['CONF_SR']['EnColRO'] = 0x0
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
        size=self.dut['fifo'].get_FIFO_SIZE()
        self.assertEqual(size,0)
        
        ## reset hits in pixels
        self.dut['CONF']['Rst'] = 1        
        self.dut["CONF"].write()
        self.dut['CONF']['Rst'] = 0        
        self.dut["CONF"].write()

    #@unittest.skip('skip')
    def test_04default(self):
        #############
        ## 4.1 set EnColRO defualt(EnColRO ON, EnInjCol OFF)
        ## send READ signal without TOKEN and get test pattern
        self.dut['CONF']['Def_Conf'] = 1
        self.dut['CONF'].write()
        self.dut["data_rx"].DISSABLE_GRAY_DECODER=1
        self.dut['data_rx'].FORCE_READ=1
        self.dut['data_rx'].FORCE_READ=0
        for i in range(10):
            size=self.dut["fifo"].FIFO_INT_SIZE
            print(size,end='')
            if size == 3:
                break
        ## get data
        raw=self.dut.get_data_now()
        print("=====sim=====default",len(raw))
        for r in raw:
            print(hex(r),end='')
        ## test
        self.assertEqual(len(raw), 3)
        self.assertEqual(raw[0], 0x4aacc0F)

        ########
        ## 4.2 set defalt=0 and send READ without TOKEN, 
        ##     random (or unknown) number will be readout
        self.dut['CONF']['Def_Conf'] = 0
        self.dut['data_rx'].FORCE_READ=1
        self.dut['data_rx'].FORCE_READ=0
        for i in range(10):
            size=self.dut["fifo"].FIFO_INT_SIZE
            print(size,end='')
            if size == 3:
                break
        print("=====sim=====no default",size)
        raw=self.dut["intf"].read_str(addr=self.dut["fifo"]._conf["base_data_addr"], size=size*4)
        dat=''
        for r in raw:
            dat=dat+r[::-1]
        self.assertEqual(size, 3)
        self.assertTrue(np.any(np.array([
                dat[:27]!="0011101010101100110000001111",
                dat[:27]=="xxxxxxxxxxxxxxxxxxxxxxxxxxxx",
                dat[:27]=="zzzzzzzzzzzzzzzzzzzzzzzzzzzz"],dtype=bool)
                ))
        self.dut["data_rx"].DISSABLE_GRAY_DECODER=0

    #@unittest.skip("skip")
    def test_05pattern(self):
        self.dut['CONF_SR']['EnColRO'] = 32
        self.dut['CONF_SR']['EnTestPattern'] = 1
        self.dut['CONF']['ClkOut'] = 0
        self.dut['CONF']['ClkBX'] = 0
        self.dut['CONF'].write()        
        self.dut['CONF_SR'].write()
        while not self.dut['CONF_SR'].is_ready:
            pass
        self.dut['CONF']['ClkOut'] = 1
        self.dut['CONF']['ClkBX'] = 1
        self.dut['CONF'].write()
        
        ###################
        ## 5.1 inject but get testpattern
        self.dut["data_rx"].DISSABLE_GRAY_DECODER=1
        self.dut.start_inj()
        raw=self.dut.get_data_now()
        pre_len=len(raw)
        flg=0
        print("=====sim====pattern",end='')
        for i in range(100):
            raw=np.append(raw,self.dut.get_data_now())
            if len(raw)==6: 
                break
            print(len(raw),end='')
        print("-",hex(raw[0]))
        self.assertEqual(raw[0], 0x4aacc0F)
        self.assertEqual(raw[3], 0x4aacc0F)

        ###################
        ## 5.2 get testpattern witout Token
        self.dut["data_rx"].FORCE_READ=1
        self.dut["data_rx"].FORCE_READ=0
        raw=self.dut.get_data_now()
        pre_len=len(raw)
        flg=0
        for i in range(100):
            raw=np.append(raw,self.dut.get_data_now())
            if len(raw)==3:
                break
        print("=====sim====",hex(raw[0]))
        self.assertEqual(raw[0], 0x4aacc0F)

        ###################
        ## inject and get normal data
        self.dut["data_rx"].DISSABLE_GRAY_DECODER=0
        self.dut['CONF_SR']['EnTestPattern'] = 0
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
        raw=self.dut.get_data_now()
        pre_len=len(raw)
        flg=0
        for i in range(100):
            raw=np.append(raw,self.dut.get_data_now())
            if len(raw)==6:
                break
        dat=interpreter.raw2list(raw)
        pix=dat[dat['col']<self.dut.COL]
        print("=====sim=====05 inj",pix)
        self.assertEqual(len(pix), 2)
        for i,p in enumerate(pix):
            if i!=0:
                self.assertEqual(p['row'],0)
            else:
                self.assertEqual(p['row'],339)
            self.assertEqual(p['col'],5)
            self.assertEqual((p['te']-p['le']) & 0x3F,2)

        ## reset hits in pixels
        self.dut['CONF']['Rst'] = 1        
        self.dut["CONF"].write()
        self.dut['CONF']['Rst'] = 0        
        self.dut["CONF"].write()
    
    #@unittest.skip("skip")
    def test_06doublehit(self):
        ###########################
        ###### 6.1 enable COLmax ON (preamp of row0,55=ON others=oFF)
        ###### inject 2 pulses to each pixel and scan interval of the 2 pulses
        self.dut['CONF_SR']['EnColRO'] = 0x80000000000000
        self.dut['CONF']['ClkOut'] = 0
        self.dut['CONF']['ClkBX'] = 0
        self.dut['CONF'].write()        
        self.dut['CONF_SR'].write()
        while not self.dut['CONF_SR'].is_ready:
            pass
        self.dut['CONF']['ClkOut'] = 1
        self.dut['CONF']['ClkBX'] = 1
        self.dut['CONF'].write()
        print("=====sim=====double SR",self.dut['fifo'].get_FIFO_SIZE())

        self.dut.set_inj_all(inj_n=2,inj_width=1,inj_delay=1)
        self.dut.set_timestamp640(src="mon")
        stop_freeze=self.dut['data_rx'].CONF_STOP_FREEZE
        stop=self.dut['data_rx'].CONF_STOP
        stop_read=self.dut['data_rx'].CONF_STOP_READ
        for delay in range(1,stop//4+10,1):
            self.dut['inj'].DELAY=delay
            self.dut.start_inj()
            print("=====sim=====double",end='')
            raw=self.dut.get_data_now()
            pre_len=len(raw)
            flg=0
            for i in range(1000):
                raw=np.append(raw,self.dut.get_data_now())
                print(len(raw),end='')
                if len(raw)==12+12:
                    break
                if len(raw)==pre_len:
                    flg=flg+1
                else:
                    pre_len=len(raw)
                    flg=0
                if flg>10:
                    break
            print("-",i,end='')
            dat=interpreter.raw2list(raw)
            pix=dat[dat['col']<self.dut.COL]
            print(pix)
            mon=dat[dat['col']==interpreter.COL_MON]
            le=mon[mon["row"]==1]['timestamp']
            te=mon[mon["row"]==0]['timestamp']
            print("=====sim=====",le,te,"2hits",(stop_read-1)//4+1,"3hits",(stop_freeze+2-1)//4+3)
            print("=====sim=====delay", delay, pix, le[1]-le[0],end='')
            print("ts", hex(pix[0]["timestamp"]-te[0]),end='')
            self.assertEqual(len(le), 2)
            self.assertEqual(le[1]-le[0], (delay+1)*16)
            self.assertTrue(te[0]-le[0] in [16,17])  
            self.assertTrue(te[1]-le[1] in [16,17]) 
            for p in pix:
                self.assertTrue(p['row'] in [0, self.dut.ROW-1])
                self.assertEqual(p['col'],self.dut.COL-1)
                if delay == (stop_read-1)//4+1 or delay == (stop_freeze+2-1)//4+3 :
                    print("tot", (p['te']-p['le']) & 0x3F)
                else:
                    self.assertEqual((p['te']-p['le']) & 0x3F,1)
            if delay < (stop_read-1)//4+1:
                self.assertEqual(len(pix), 2)
            elif delay < (stop_freeze+2-1)//4+3:
                #if self.option=="max":
                #    self.assertEqual(len(pix), 2)  #####TODO check whether this is ok or not
                #else:
                    self.assertEqual(len(pix), 3)
            else:
                self.assertEqual(len(pix), 4)

            if len(pix)>2:
                print("ts1", hex(te[1]-pix[2]["timestamp"])) ## I dont understand why this goes negative????
            else:
                print()

    #@unittest.skip("skip")
    def test_07doublehit(self):
        ###########################
        ###### 7. enable COL0, max ON (preamp of row0=ON others=oFF)
        ###### inject 2 pulses to each pixel and scan interval of the 2 pulses
        ###### col-wise version of test06
        self.dut.PIXEL_CONF["EnPre"].fill(False)
        self.dut.PIXEL_CONF["EnPre"][:,0]=True
        self.util_set_pixel(bit="EnPre",defval=0)
        self.dut['CONF_SR']['EnColRO'] = 0x80000000000001
        self.dut['CONF']['ClkOut'] = 0
        self.dut['CONF']['ClkBX'] = 0
        self.dut['CONF']['Rst'] = 1 
        self.dut['CONF'].write()        
        self.dut['CONF_SR'].write()
        while not self.dut['CONF_SR'].is_ready:
            pass
        ## reset hits in pixels
        self.dut['CONF']['ClkOut'] = 1
        self.dut['CONF']['ClkBX'] = 1
        self.dut['CONF']['Rst'] = 0        
        self.dut['CONF'].write()
        print("=====sim=====2col SR",self.dut['fifo'].get_FIFO_SIZE())

        self.dut.set_inj_all(inj_n=2,inj_width=1,inj_delay=1)
        self.dut.set_timestamp640(src="mon")
        stop_freeze=self.dut['data_rx'].CONF_STOP_FREEZE
        stop=self.dut['data_rx'].CONF_STOP
        stop_read=self.dut['data_rx'].CONF_STOP_READ
        for delay in range(80,stop//4+30,1):
            self.dut['inj'].DELAY=delay
            self.dut.start_inj()
            print("=====sim=====2col",end="")
            raw=self.dut.get_data_now()
            pre_len=len(raw)
            flg=0
            for i in range(1000):
                raw=np.append(raw,self.dut.get_data_now())
                print(len(raw),end='')
                if len(raw)==12+12:
                    break
                if len(raw)==pre_len:
                    flg=flg+1
                else:
                    pre_len=len(raw)
                    flg=0
                if flg>10:
                    break
            print("-",i,end="")
            dat=interpreter.raw2list(raw)
            pix=dat[dat['col']<self.dut.COL]
            print(pix)
            mon=dat[dat['col']==interpreter.COL_MON]
            le=mon[mon["row"]==1]['timestamp']
            te=mon[mon["row"]==0]['timestamp']
            print("=====sim=====",le,te,end="")
            self.assertEqual(len(le), 2)
            self.assertEqual(le[1]-le[0], (delay+1)*16)
            self.assertTrue(te[0]-le[0] in [16,17])
            self.assertTrue(te[1]-le[1] in [16,17])
            print("=====sim=====delay", delay, len(pix), pix, le[1]-le[0],end="")
            print("ts", hex(pix[0]["timestamp"]-te[0]),end='')
            print("tot",(pix['te']-pix['le']) & 0x3F,"3hits",(stop_read-1)//4+3, "4hits",(stop_freeze+2-1)//4+3)
            for p in pix:
                self.assertEqual(p['row'], 0)
                self.assertTrue(p['col'] in [0,self.dut.COL-1])
                if delay == (stop_read-1)//4+1 or delay == (stop_freeze+2-1)//4+3 :
                    pass
                else:
                    self.assertEqual((p['te']-p['le']) & 0x3F,1)
            if delay <= (stop_read-1)//4+3:
                self.assertEqual(len(pix), 2)
            elif delay<= 89:
                self.assertEqual(len(pix), 3)
            else:
                self.assertEqual(len(pix), 4)

            if len(pix)>2:
                print("ts1", hex(te[1]-pix[2]["timestamp"])) ## I dont understand why this goes negative????
            else:
                print()

if __name__ == '__main__':
    if len(sys.argv)>1:
        TestDataOut.extra_defines=[sys.argv.pop()]
    unittest.main()