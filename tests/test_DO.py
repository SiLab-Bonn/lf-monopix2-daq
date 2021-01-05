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

class TestDO(test_Monopix2.TestMonopix2):
    hit_file=[
            HIT_FILE0,     ## test07     
            ]

    def test_00init(self):
        self.dut.init()
        ### set 0 to spi read-buffer
        self.dut['CONF']['Ld_Cnfg'] = 0
        self.dut['CONF'].write()
        self.dut['CONF_SR'].set_size(self.dut["CONF_SR"]._conf['size']+8)
        self.dut['CONF_SR'].setall(False)
        self.dut['CONF_SR'].write()
        while not self.dut['CONF_SR'].is_ready:
            pass
        self.dut['CONF_SR'].write()
        while not self.dut['CONF_SR'].is_ready:
            pass
        self.dut['CONF_SR'].set_size(self.dut["CONF_SR"]._conf['size'])
        
        ### set init values from yaml
        self.dut['CONF_SR'].init()
        self.dut['CONF_SR']['EnMonitorCol']=0xFFFFFFFFFFFFFF
        self.dut['CONF_SR']['InjEnCol']=0 # active low
        self.dut['CONF_SR']['EnSRDCol']=0
        self.dut['CONF_SR'].write() 
        i=0
        t0=time.time()
        while not self.dut['CONF_SR'].is_ready:
            i=i+1
        self.dut.logger.info("=====sim===== CONF_SR {0:.2f}s,{1}".format(time.time()-t0,i))

        #############################
        ## set readout, injection
        self.dut.set_inj_all(inj_n=1,inj_width=2,inj_delay=100)
        self.dut.set_timestamp640(src="mon")
        #self.dut.set_monoread(sync_timestamp=False)

    #@unittest.skip('skip')
    def test_01gl(self):
        ####
        ## 1.1 write initial global data(from yaml) twice 
        d0=self.dut.get_conf_sr("w")

        self.dut['CONF'].setall(False)
        self.dut['CONF_SR'].write() 
        while not self.dut['CONF_SR'].is_ready:
            pass
        d1=self.dut.get_conf_sr("rw")
        print("=====sim=====d0,d1",d0['write_reg'][:],d1['read_reg'][:])
        self.assertEquals(d0['write_reg'][:],d1['read_reg'][:])

        self.dut['CONF_SR'].setall(True)
        self.dut['CONF_SR']['EnSRDCol']=0
        self.dut['CONF_SR'].write() 
        while not self.dut['CONF_SR'].is_ready:
            pass
        d2=self.dut.get_conf_sr("rw")
        self.assertEquals(d1['write_reg'][:],d2['read_reg'][:])
        ###############
        ## 1.2 set random value and read when all CONF_SR=0
        set_values={}
        for dac_name in ["BLRes","VAmp1","VAmp2","VPFB","VNFoll","VPFoll","VNLoad","VPLoad","TDAC_LSB","Vsf","Driver"]:
             set_values[dac_name]=random.randint(0,0x3F)
             set_values["Mon_{0:s}".format(dac_name)]=0
        set_values["Mon_VAmp2"]=1
        for dac_name in set_values.keys():
             self.dut['CONF_SR'][dac_name]=set_values[dac_name]
        set_values["EnAnaBuffer"]=0
        self.dut["CONF_SR"]["EnAnaBuffer"] =set_values["EnAnaBuffer"]
        set_values["EnDataCMOS"]=0
        self.dut["CONF_SR"]["EnDataCMOS"] =set_values["EnDataCMOS"]
        set_values["EnDataLVDS"]=1
        self.dut["CONF_SR"]["EnDataLVDS"] =set_values["EnDataLVDS"]
        set_values["InjEnCol"]=random.randint(0,0xFFFFFFFFFFFFFF)
        self.dut["CONF_SR"]["InjEnCol"] =set_values["InjEnCol"]
        set_values["EnMonitorCol"]=random.randint(0,0xFFFFFFFFFFFFFF)
        self.dut["CONF_SR"]["EnMonitorCol"]=set_values["EnMonitorCol"]

        self.dut['CONF_SR'].write() 
        while not self.dut['CONF_SR'].is_ready:
            pass
        d3=self.dut.get_conf_sr("rw")
        self.assertEquals(d2['write_reg'][:],d3['read_reg'][:])
        self.dut['CONF_SR'].setall(False)
        self.dut['CONF_SR'].write() 
        while not self.dut['CONF_SR'].is_ready:
            pass
        d4=self.dut.get_conf_sr("r")
        self.assertEquals(d3['write_reg'][:],d4['read_reg'][:])   

    #@unittest.skip('skip')
    def test_02Col5(self):
        ######
        ## 5. write random data to col4,5 of pixel register
        bit="EnMonitor" #### jist use it as buffer
        self.dut.PIXEL_CONF[bit] = (np.random.randint(2, size=(self.dut.COL, self.dut.ROW)) == 1)
        w0=np.zeros_like(self.dut.PIXEL_CONF[bit])
        r1=np.zeros_like(self.dut.PIXEL_CONF[bit])
        dcol=2
        self.dut['CONF_SR']['EnSRDCol'].setall(False)
        self.dut['CONF_SR']['EnSRDCol'][dcol]=True
        self.dut['CONF_SR']['EnSoDCol']=dcol
        self.dut['CONF']['Ld_Cnfg'] = 0
        self.dut['CONF'].write()
        self.dut['CONF_SR'].write()
        while not self.dut['CONF_SR'].is_ready:
            pass
        ## write a random data to col4,5
        self.dut['CONF_DC']['Col0'] = bitarray.bitarray(list(self.dut.PIXEL_CONF[bit][dcol*2+1,:]))
        self.dut['CONF_DC']['Col1'] = bitarray.bitarray(list(self.dut.PIXEL_CONF[bit][dcol*2,::-1]))
        self.dut['CONF']['Ld_Cnfg'] = 1 ## we dont need Ld but this is required to select FPGA
        self.dut['CONF'].write()
        self.dut['CONF_DC'].write()
        while not self.dut['CONF_DC'].is_ready:
            pass
        self.dut['CONF']['Ld_Cnfg'] = 0
        dat=self.dut.get_conf_sr("cw")
        w0[dcol*2+1,:]=dat['write_reg']["Col0"][:].tolist()
        w0[dcol*2,:]=dat['write_reg']["Col1"][:].tolist()[::-1]
        print("=====sim=====w",dat['write_reg']["Col0"][:])

        self.dut['CONF_SR']['EnSRDCol'].setall(False)
        self.dut['CONF_SR']['EnSRDCol'][dcol]=True
        self.dut['CONF']['Ld_Cnfg'] = 0
        self.dut['CONF'].write()
        self.dut['CONF_SR'].write()
        while not self.dut['CONF_SR'].is_ready:
            pass
        ## write another random data to col4,5
        self.dut['CONF_DC']['Col0'] = bitarray.bitarray(list(self.dut.PIXEL_CONF[bit][3*2,:]))
        self.dut['CONF_DC']['Col1'] = bitarray.bitarray(list(self.dut.PIXEL_CONF[bit][3*2+1,::-1]))
        self.dut['CONF']['Ld_Cnfg'] = 1
        self.dut['CONF'].write()
        self.dut['CONF_DC'].write()
        while not self.dut['CONF_DC'].is_ready:
            pass
        self.dut['CONF']['Ld_Cnfg'] = 0
        dat=self.dut.get_conf_sr("cr")
        r1[dcol*2+1,:]=dat['read_reg']["Col0"][:].tolist()
        r1[dcol*2,:]=dat['read_reg']["Col1"][:].tolist()[::-1]
        print("=====sim=====r",dat['read_reg']["Col0"][:])
        print("=====sim=====", np.argwhere(r1!=w0))
        self.assertTrue(np.all(r1==w0))

    #@unittest.skip('skip')
    def test_03Cnfg(self):
        bit="EnMonitor" #### jist use this as for dummy
        self.dut.PIXEL_CONF[bit] = (np.random.randint(2, size=(self.dut.COL, self.dut.ROW)) == 1)
        w0=np.empty_like(self.dut.PIXEL_CONF[bit])
        #################
        ### setting random number to all pixel register
        for dcol in np.arange(self.dut.COL//2):
            self.dut['CONF_SR']['EnSRDCol'].setall(False)
            self.dut['CONF_SR']['EnSRDCol'][dcol]=True
            self.dut['CONF_SR']['EnSoDCol']=dcol
            self.dut['CONF_SR']['EnMonitorLd']=0  ## set all mon on
            self.dut['CONF']['Ld_Cnfg'] = 0
            self.dut['CONF'].write()
            self.dut['CONF_SR'].write()
            while not self.dut['CONF_SR'].is_ready:
                pass
            self.dut['CONF_SR']['EnMonitorLd']=1
            ## set pix_config
            self.dut['CONF_DC']['Col0'] = bitarray.bitarray(list(self.dut.PIXEL_CONF[bit][dcol*2+1,:]))
            self.dut['CONF_DC']['Col1'] = bitarray.bitarray(list(self.dut.PIXEL_CONF[bit][dcol*2,::-1]))
            self.dut['CONF']['Ld_Cnfg'] = 1 
            self.dut['CONF'].write()
            self.dut['CONF_DC'].write()
            while not self.dut['CONF_DC'].is_ready:
                pass
            self.dut['CONF']['Ld_Cnfg'] = 0
            dat=self.dut.get_conf_sr("cw")
            w0[dcol*2+1,:]=dat['write_reg']["Col0"][:].tolist()
            w0[dcol*2,:]=dat['write_reg']["Col1"][:].tolist()[::-1]
        self.assertTrue(np.all(self.dut.PIXEL_CONF[bit]==w0))

        ############
        ## 3.1 setall0 and readout random data
        self.dut.PIXEL_CONF[bit].fill(False)
        r1=np.empty_like(self.dut.PIXEL_CONF[bit])
        for dcol in np.arange(self.dut.COL//2):
            self.dut['CONF_SR']['EnSRDCol'].setall(False)
            self.dut['CONF_SR']['EnSRDCol'][dcol]=True
            self.dut['CONF_SR']['EnSoDCol']=dcol
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
            dat=self.dut.get_conf_sr("cr")
            r1[dcol*2+1,:]=dat['read_reg']["Col0"][:].tolist()
            r1[dcol*2,:]=dat['read_reg']["Col1"][:].tolist()[::-1]
        print("=====sim=====pix_reg random",w0,r1)
        self.assertTrue(np.all(w0==r1))  ## r is random

        ############
        ## 3.2 setall1 and readout all0
        self.dut.PIXEL_CONF[bit].fill(True)
        r2=np.empty_like(self.dut.PIXEL_CONF[bit])

        for dcol in np.arange(self.dut.COL//2):
            self.dut['CONF_SR']['EnSRDCol'].setall(False)
            self.dut['CONF_SR']['EnSRDCol'][dcol]=True
            self.dut['CONF_SR']['EnSoDCol']=dcol
            self.dut['CONF_SR']['EnInjLd']=0
            self.dut['CONF_SR']['EnPreLd']=0
            self.dut['CONF']['Ld_Cnfg'] = 0
            self.dut['CONF'].write()
            self.dut['CONF_SR'].write()
            while not self.dut['CONF_SR'].is_ready:
                pass
            self.dut['CONF_SR']['EnInjLd']=1 
            self.dut['CONF_SR']['EnPreLd']=1
            ## set pix_config
            self.dut['CONF_DC']['Col0'] = bitarray.bitarray(list(self.dut.PIXEL_CONF[bit][dcol*2+1,:]))
            self.dut['CONF_DC']['Col1'] = bitarray.bitarray(list(self.dut.PIXEL_CONF[bit][dcol*2,::-1]))
            self.dut['CONF']['Ld_Cnfg'] = 1
            self.dut['CONF'].write()
            self.dut['CONF_DC'].write()
            while not self.dut['CONF_DC'].is_ready:
                pass
            self.dut['CONF']['Ld_Cnfg'] = 0
            dat=self.dut.get_conf_sr("cr")
            r2[dcol*2+1,:]=dat['read_reg']["Col0"][:].tolist()
            r2[dcol*2,:]=dat['read_reg']["Col1"][:].tolist()[::-1]
        print("=====sim=====pix_reg all0",r2)
        self.assertFalse(np.any(r2))  ## r is all False

        ############
        ## 3.3 set 0 again and readout all1
        self.dut.PIXEL_CONF[bit].fill(False)
        r3=np.empty_like(self.dut.PIXEL_CONF[bit])
        for dcol in np.arange(self.dut.COL//2):
            self.dut['CONF_SR']['EnSRDCol'].setall(False)
            self.dut['CONF_SR']['EnSRDCol'][dcol]=True
            self.dut['CONF_SR']['EnSoDCol']=dcol
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
            dat=self.dut.get_conf_sr("cr")
            r3[dcol*2+1,:]=dat['read_reg']["Col0"][:].tolist()
            r3[dcol*2,:]=dat['read_reg']["Col1"][:].tolist()[::-1]
        print("=====sim=====pix_reg all0",r3)
        self.assertTrue(np.all(r3))  ## r is all True

    #@unittest.skip('skip')
    def test_06Default(self):
        #####
        ## write random number one more time
        set_values={}
        for dac_name in ["BLRes","VAmp1","VAmp2","VPFB","VNFoll","VPFoll","VNLoad","TDAC_LSB","Vsf","Driver"]:
             set_values[dac_name]=random.randint(0,0x3F)
             set_values["Mon_{0:s}".format(dac_name)]=0
        set_values["Mon_TDAC_LSB"]=1
        for dac_name in set_values.keys():
             self.dut['CONF_SR'][dac_name]=set_values[dac_name]
        set_values["EnAnaBuffer"]=0
        self.dut["CONF_SR"]["EnAnaBuffer"] =set_values["EnAnaBuffer"]
        set_values["EnDataCMOS"]=0
        self.dut["CONF_SR"]["EnDataCMOS"] =set_values["EnDataCMOS"]
        set_values["EnDataLVDS"]=1
        self.dut["CONF_SR"]["EnDataLVDS"] =set_values["EnDataLVDS"]
        set_values["InjEnCol"]=random.randint(0,0xFFFFFFFFFFFFFF)
        self.dut["CONF_SR"]["InjEnCol"] =set_values["InjEnCol"]
        set_values["EnMonitorCol"]=random.randint(0,0xFFFFFFFFFFFFFF)
        self.dut["CONF_SR"]["EnMonitorCol"]=set_values["EnMonitorCol"]

        self.dut['CONF']['Ld_Cnfg'] = 0
        self.dut['CONF'].write()
        self.dut['CONF_SR'].write() 
        while not self.dut['CONF_SR'].is_ready:
            pass
        d0=self.dut.get_conf_sr("w")
        #####
        ## Def_Conf on-->should be no change
        self.dut['CONF']['Def_Conf'] = 1
        self.dut['CONF'].write()
        self.dut['CONF_SR'].setall(True)
        self.dut['CONF_SR'].write() 
        while not self.dut['CONF_SR'].is_ready:
            pass
        d1=self.dut.get_conf_sr("rw")
        self.assertEquals(d0['write_reg'][:],d1['read_reg'][:])  

        #####
        ## Def_Conf off again-->should be no change
        self.dut['CONF']['Def_Conf'] = 1
        self.dut['CONF'].write()
        self.dut['CONF_SR'].setall(False)
        self.dut['CONF_SR'].write() 
        while not self.dut['CONF_SR'].is_ready:
            pass
        d2=self.dut.get_conf_sr("r")
        self.assertEquals(d1['write_reg'][:],d2['read_reg'][:])  
        self.assertTrue(np.all(d2['read_reg'][:].tolist()))

if __name__ == '__main__':
    if len(sys.argv)>1:
        TestDO.extra_defines=[sys.argv.pop()]
    unittest.main()

