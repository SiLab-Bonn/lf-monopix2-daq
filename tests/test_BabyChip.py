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

class TestBabyChip(unittest.TestCase):

    extra_defines = ["MONOPIX2_DEFINES__SV","COLS=56","ROWS=2","USE_VAMS","NO_TRIM_TEST"]
    
    @classmethod
    def setUpClass(cls):
        daq_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__))) #../
        rtl_dir=os.path.join(os.path.dirname(daq_dir),"rtl/top")

        extra_defines = ["MONOPIX2_DEFINES__SV","COLS=56","ROWS=2","USE_VAMS","NO_TRIM_TEST"]
        os.environ['SIM'] = 'questa'
        os.environ['WAVES'] = '1'
        os.environ['GUI'] = '0'
        #os.environ['COCOTB_RESOLVE_X']="RANDOM" ##VALUE_ERROR

        hit_file = os.path.join(daq_dir, "tests/data/"+os.path.basename(os.path.abspath(__file__))[:-2]+"csv")
        cls.hit_file=[
            #hit_file,     ## test01
            #hit_file[:-4]+"02.csv",   ## reverse diagnal
            ]
        os.environ['SIMULATION_MODULES'] = yaml.dump({'tests.drivers.HitDataFile': {
                'filename': cls.hit_file
            }})
        cls.fcsv=None
        wave_file=os.path.join(daq_dir,
            "data_output/wave/"+os.path.basename(os.path.abspath(__file__))[:-3]+"03pix.wlf")
        #wave_file="/tmp/monopix2.wlf"
        logging.info("=====sim===== wave_file {0:s}".format(wave_file))
        cocotb_compile_and_run(
            sim_files = [daq_dir + '/tests/hdl/monopix2_tb.sv'],
            extra_defines = extra_defines,
            test_module='monopix2_daq.sim.Test',
            sim_bus = 'monopix2_daq.sim.SiLibUsbBusDriver',
            include_dirs = (daq_dir + "/tests/hdl",daq_dir, daq_dir + "/firmware/src",rtl_dir),
            extra = '\nVSIM_ARGS += -wlf {0}\n'.format(wave_file) #-no_autoacc
        )

        with open(daq_dir + '/monopix2_daq/monopix2_sim.yaml', 'r') as f:
            conf = yaml.safe_load(f)
        cls.dut = monopix2.Monopix2(conf=conf,no_power_reset=False)
        cls.hit_file.reverse()

    def setUp(self):
        pass

    def tearDown(self):
        self.dut.logger.info("tearDown for {0}".format(self._testMethodName))

    @classmethod
    def tearDownClass(cls):
        cls.dut.close()
        time.sleep(5)
        cocotb_compile_clean()

    def util_startHIT(self):
        self.dut['tb'].RESET_HIT = 1
        self.dut['tb'].CLK_HIT_GATE = 1
        for i in range(10000):
            start=self.dut['tb'].get_READY_HIT()
            if start == "1":
                break
        self.dut['tb'].RESET_HIT = 0
        fname=self.hit_file.pop()
        print("=====sim=====fname",fname)
        self.fcsv=open(fname)
        self.csv_reader = csv.reader(self.fcsv)

    def util_pauseHIT(self):
        self.dut['tb'].CLK_HIT_GATE = 0

    def util_resumeHIT(self):
        self.dut['tb'].CLK_HIT_GATE = 1

    def util_nextHit(self,n_data=1):
        """
        bxid, col, row, tot = self.util_nextHit()
        """
        if isinstance(n_data,str):
            if (n_data=='all'):
                hits=np.loadtxt(self.fcsv,
                    delimiter=",",
                    dtype=[("bxid",'i4'),("col",'i1'),("row",'i2'),("tot",'i4'),("comm","S64")])
                if len(hits)>0 and hits[-1]['col']==-1:
                    hits=hits[:-1]
                self.fcsv.close()
                return hits  
        while True:
            file_row=self.csv_reader.next()
            if len(file_row)==0:
                bxid = -1
                col = -1
                row = -1
                tot = -1
                break
            elif file_row[0][0]=="#":
                pass
            elif len(file_row)<3:
                bxid = -1
                col = -1
                row = -1
                tot = -1
                break
            else:
                bxid = int(file_row[0])
                col = int(file_row[1])
                row = int(file_row[2])
                tot = int(file_row[3])
                break
        if col==-1:
            self.fcsv.close()
        return bxid, col, row, tot

    def util_set_pixel(self,bit="EnPre",defval=False):
        ## Readout off
        ClkBX = self.dut['CONF']['ClkBX'].tovalue()
        ClkOut = self.dut['CONF']['ClkOut'].tovalue()
        self.dut['CONF']['ClkOut'] = 0 
        self.dut['CONF']['ClkBX'] = 0
        self.dut['CONF_SR']["{0:s}Ld".format(bit)] = 0 ## active low
        ## set defval
        if defval is None:
            uni=np.arange(self.dut.COL//2)
        elif isinstance(defval, list):
            uni=np.array(defval,int)//2
        else:
            if isinstance(defval,bool):
                self.dut['CONF_DC'].setall(defval)
            else:
                self.dut['CONF_DC']['Col0'] = bitarray.bitarray(list(self.dut.PIXEL_CONF[bit][defval*2+1,:]))
                self.dut['CONF_DC']['Col1'] = bitarray.bitarray(list(self.dut.PIXEL_CONF[bit][defval*2,::-1]))

            self.dut['CONF_SR']['EnSRDCol'].setall(True)
            self.dut['CONF']['Ld_Cnfg'] = 0
            self.dut['CONF'].write()
            self.dut['CONF_SR'].write()
            while not self.dut['CONF_SR'].is_ready:
                pass

            self.dut['CONF']["Def_Conf"]=0  ### this is good only for test_BabyChip
            self.dut['CONF']['Ld_Cnfg'] = 1
            self.dut['CONF'].write()
            self.dut['CONF_DC'].write()
            while not self.dut['CONF_DC'].is_ready:
                pass
            self.dut['CONF']['Ld_Cnfg'] = 0
            arg=np.argwhere(self.dut.PIXEL_CONF[bit]!=defval)
            uni=np.unique(arg[:,0]//2)
        ## set individual double col
        for dcol in uni:
            print("=====sim===== util_set_pixel() setting dcol",dcol)
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
        self.dut['CONF_SR']["{0:s}Ld".format(bit)] = 1
        self.dut['CONF']['ClkOut'] = ClkOut  ###Readout OFF
        self.dut['CONF']['ClkBX'] = ClkBX
        self.dut['CONF'].write()

    def util_set_tdac(self, defval=False): 
        ClkBX = self.dut['CONF']['ClkBX'].tovalue()
        ClkOut = self.dut['CONF']['ClkOut'].tovalue()
        self.dut['CONF']['ClkOut'] = 0  ###Readout OFF
        self.dut['CONF']['ClkBX'] = 0
        
        for i in range(0,4):
            tmp= (self.dut.PIXEL_CONF["Trim"] >>i ) & 0x1
            self.dut['CONF_SR']["TrimLd"]=15
            self.dut['CONF_SR']["TrimLd"][i] = 0 ## active low
            print("=====sim===== trimld",self.dut['CONF_SR']["TrimLd"])
            ## set defval
            if defval is None:
                uni=np.arange(self.dut.COL//2)
            else:
                self.dut['CONF_SR']['EnSRDCol'].setall(True)
                self.dut['CONF']['Ld_Cnfg'] = 0
                self.dut['CONF'].write()
                self.dut['CONF_SR'].write()
                while not self.dut['CONF_SR'].is_ready:
                    pass
                self.dut['CONF_DC'].setall(defval)
                self.dut['CONF']['Ld_Cnfg'] = 1
                self.dut['CONF'].write()
                self.dut['CONF_DC'].write()
                while not self.dut['CONF_DC'].is_ready:
                    pass
                self.dut['CONF']['Ld_Cnfg'] = 0
                arg=np.argwhere(tmp!=defval)
                uni=np.unique(arg[:,0]//2)
            ## set individual double col
            for dcol in uni:
                self.dut['CONF_SR']['EnSRDCol'].setall(False)
                self.dut['CONF_SR']['EnSRDCol'][dcol]=True
                self.dut['CONF']['Ld_Cnfg'] = 0
                self.dut['CONF'].write()
                self.dut['CONF_SR'].write()
                while not self.dut['CONF_SR'].is_ready:
                    pass
                ## set pix_config
                self.dut['CONF_DC']['Col0'] = bitarray.bitarray(list(tmp[dcol*2+1,:]))
                self.dut['CONF_DC']['Col1'] = bitarray.bitarray(list(tmp[dcol*2,::-1]))
                self.dut['CONF']['Ld_Cnfg'] = 1
                self.dut['CONF'].write()
                self.dut['CONF_DC'].write()
                while not self.dut['CONF_DC'].is_ready:
                    pass
                self.dut['CONF']['Ld_Cnfg'] = 0
                #print("=====sim=====tdac",dcol,self.dut['CONF_DC'][:]
        self.dut['CONF_SR']["TrimLd"] = 15
        self.dut['CONF']['ClkOut'] = ClkOut  ###Readout OFF
        self.dut['CONF']['ClkBX'] = ClkBX
        self.dut['CONF'].write()

    def test_00init(self):
        self.dut.init()
        self.dut['CONF_DC'].set_size(4)
        #self.dut.set_inj_all(inj_n=1,inj_width=1,inj_delay=100)
        #self.dut.set_monoread()

    #@unittest.skip("skip")
    def test_03pix(self):
        #########################
        ### init sequence (Pre ON, Trim=7, INJ=OFF)
        # pre on trim[2:0] on except [55,1] off
        self.dut['CONF_SR']["BLRes"]=32
        self.dut['CONF_SR']["VAmp1"]=35
        self.dut['CONF_SR']["VAmp2"]=35
        self.dut['CONF_SR']["VPFB"]=39
        self.dut['CONF_SR']["VNFoll"]=15
        self.dut['CONF_SR']["VPFoll"]=15
        self.dut['CONF_SR']["VNLoad"]=13
        self.dut['CONF_SR']["Vsf"]=32
        self.dut['CONF_SR']["TDAC_LSB"]=12
        self.dut['CONF_SR']["Driver"]=32
        self.dut['CONF_SR']["Vsf"]=32
        self.dut['CONF_SR']["Mon_Vsf"]= 0
        self.dut['CONF_SR']["Mon_VPFB"]= 0
        self.dut['CONF_SR']["Mon_VPLoad"]= 0
        self.dut['CONF_SR']["Mon_VNLoad"]= 0
        self.dut['CONF_SR']["Mon_VNFoll"]= 0
        self.dut['CONF_SR']["Mon_VPFoll"]= 0
        self.dut['CONF_SR']["Mon_VAmp1"]=1
        self.dut['CONF_SR']["Mon_VAmp2"]=0
        self.dut['CONF_SR']["Mon_TDAC_LSB"]= 0
        self.dut['CONF_SR']["Mon_BLRes"]= 0
        self.dut['CONF_SR']["Mon_Driver"]= 0
        self.dut['CONF_SR']["EnDataCMOS"]= 1
        self.dut['CONF_SR']["EnDataLVDS"]= 0
        self.dut['CONF_SR']["EnAnaBuffer"]= 1
        self.dut['CONF_SR']["EnTestPattern"]= 0
        self.dut['CONF_SR']["DelayROConf"]= 4
        self.dut['CONF_SR']["EnColRO"]= 0xFFFFFFFFFFFFFF
        self.dut['CONF_SR']["InjEnCol"]= 0x7FFFFFFFFFFFFE  # active low
        self.dut['CONF_SR']["EnMonitorCol"]=0x1
        self.dut['CONF_SR']["EnSoDCol"]=2
        self.dut['CONF']["Def_Conf"]=1
        self.dut['CONF']["ClkOut"]=0
        self.dut['CONF']['ClkBX'] = 0      
        self.dut['CONF']['Ld_Cnfg'] = 0
        self.dut['CONF'].write()

        self.dut.PIXEL_CONF["EnPre"].fill(True)
        self.dut.PIXEL_CONF["EnPre"][54,2]=False  ## this is [55,1]
        self.dut['CONF_SR']['TrimLd']=8      ## active low
        self.dut['CONF_SR']['EnInjLd']=1     ## active low
        self.dut['CONF_SR']['EnPreLd']=0     ## active low
        self.dut['CONF_SR']['EnMonitorLd']=1 ## active low
        self.util_set_pixel(bit="EnPre",defval=True)

        # set inj[0,1],[55,0],[55,1] on
        self.dut['CONF_SR']['TrimLd']=7  ## active low
        self.dut['CONF_SR']['EnInjLd']=0 ## active low
        self.dut['CONF_SR']['EnPreLd']=1 ## active low
        self.dut['CONF_SR']['EnMonitorLd']=0 ## active low
        self.dut.PIXEL_CONF["EnInj"].fill(False)
        self.dut.PIXEL_CONF["EnInj"][0,1]=True
        self.util_set_pixel(bit="EnInj",defval=False)
        ### keep MON col55 off, but INJ col55 on
        self.dut.PIXEL_CONF["EnInj"][54,2]=True  ## this is [55,1]
        self.dut.PIXEL_CONF["EnInj"][54,3]=True  ## this is [55,0] 
        self.dut['CONF_SR']['EnMonitorLd']=1 ## active low
        self.util_set_pixel(bit="EnInj",defval=[54])

        ## reset matrix and enable readout
        self.dut['CONF']['Rst'] = 1
        self.dut['CONF']['ResetBcid'] = 1
        self.dut['CONF']['ClkOut'] = 1
        self.dut['CONF']['ClkBX'] = 1
        self.dut['CONF'].write()
        self.dut['CONF']['Rst'] = 0
        self.dut['CONF']['ResetBcid'] = 0
        self.dut['CONF'].write()
        self.dut['data_rx'].set_en(True)
        self.dut.start_inj()
        print("=====sim=====",end=" ")
        raw=self.dut.get_data_now()
        for i in range(100):
            raw=np.append(raw,self.dut.get_data_now())
            if len(raw) == 3*2:
                break
            print(len(raw),end=" ")
        print(len(raw),"-",i)
        for r in raw:
            print(hex(r),end="")
        dat=interpreter.raw2list(raw,delete_noise=False)
        print("=====sim=====",dat)
        pix=dat[dat["col"]<self.dut.COL] 
        self.assertEqual(len(pix),2)
        self.assertEqual(pix[0]['col'],0)
        self.assertEqual(pix[0]['row'],1)
        self.assertEqual((pix[0]['te']-pix[0]['le'])&0x3F,1)
        self.assertEqual(pix[1]['col'],55)
        self.assertEqual(pix[1]['row'],0)
        self.assertEqual((pix[1]['te']-pix[1]['le'])&0x3F,1)        

    @unittest.skip("skip")
    def test_01gl(self):
        self.dut['CONF']["ClkOut"]=0
        self.dut['CONF']['ClkBX'] = 0      
        self.dut['CONF']["Def_Conf"]=1
        self.dut['CONF']['Ld_Cnfg'] = 0
        self.dut['CONF'].write()
        self.dut['CONF_SR'].write()
        while not self.dut['CONF_SR'].is_ready:
            pass
        self.dut['CONF']["ClkOut"]=1
        self.dut['CONF']['ClkBX'] = 1      
        self.dut['CONF']["Def_Conf"]=0
        self.dut['CONF']['Ld_Cnfg'] = 0
        self.dut['CONF'].write()

    @unittest.skip("skip")
    def test_02inj(self):
        #########################
        ### init sequence (Pre ON, Inj ON, Trim=15)
        self.dut['CONF_SR']["BLRes"]=32
        self.dut['CONF_SR']["VAmp1"]=35
        self.dut['CONF_SR']["VAmp2"]=35
        self.dut['CONF_SR']["VPFB"]=39
        self.dut['CONF_SR']["VNFoll"]=15
        self.dut['CONF_SR']["VPFoll"]=15
        self.dut['CONF_SR']["VNLoad"]=13
        self.dut['CONF_SR']["Vsf"]=32
        self.dut['CONF_SR']["TDAC_LSB"]=12
        self.dut['CONF_SR']["Driver"]=32
        self.dut['CONF_SR']["Vsf"]=32
        self.dut['CONF_SR']["Mon_Vsf"]= 0
        self.dut['CONF_SR']["Mon_VPFB"]= 0
        self.dut['CONF_SR']["Mon_VPLoad"]= 0
        self.dut['CONF_SR']["Mon_VNLoad"]= 0
        self.dut['CONF_SR']["Mon_VNFoll"]= 0
        self.dut['CONF_SR']["Mon_VPFoll"]= 0
        self.dut['CONF_SR']["Mon_VAmp1"]=1
        self.dut['CONF_SR']["Mon_VAmp2"]=0
        self.dut['CONF_SR']["Mon_TDAC_LSB"]= 0
        self.dut['CONF_SR']["Mon_BLRes"]= 0
        self.dut['CONF_SR']["Mon_Driver"]= 0
        self.dut['CONF_SR']["EnDataCMOS"]= 1
        self.dut['CONF_SR']["EnDataLVDS"]= 0
        self.dut['CONF_SR']["EnAnaBuffer"]= 1
        self.dut['CONF_SR']["EnTestPattern"]= 0
        self.dut['CONF_SR']["DelayROConf"]= 4
        self.dut['CONF_SR']["EnColRO"]= 0xFFFFFFFFFFFFFF
        self.dut['CONF_SR']["InjEnCol"]= 0xFFFFFFFFFFFFDF
        self.dut['CONF_SR']["EnMonitorCol"]=32
        self.dut['CONF_SR']["EnSoDCol"]=2
        self.dut['CONF_SR']['EnSRDCol'].setall(True)
        self.dut['CONF_SR']['TrimLd']=0 ## active low
        self.dut['CONF_SR']['EnInjLd']=0 ## active low
        self.dut['CONF_SR']['EnPreLd']=0 ## active low
        self.dut['CONF_SR']['EnMonitorLd']=0 ## active low
        self.dut['CONF']["Def_Conf"]=1
        self.dut['CONF']["ClkOut"]=0
        self.dut['CONF']['ClkBX'] = 0      
        self.dut['CONF']['Ld_Cnfg'] = 0
        self.dut['CONF'].write()
        self.dut['CONF_SR'].write()
        while not self.dut['CONF_SR'].is_ready:
            pass

        self.dut['CONF']["Def_Conf"]=0
        self.dut['CONF']['Ld_Cnfg'] = 1
        self.dut['CONF'].write()
        self.dut['CONF_DC'].setall(True)
        self.dut['CONF_DC'].write(size=self.dut['CONF_DC'].SIZE)
        while not self.dut['CONF_DC'].is_ready:
            pass

        ## reset matrix and enable readout
        self.dut['CONF']['Rst'] = 1
        self.dut['CONF']['ResetBcid'] = 1
        self.dut['CONF']['ClkOut'] = 1
        self.dut['CONF']['ClkBX'] = 1
        self.dut['CONF'].write()
        self.dut['CONF']['Rst'] = 0
        self.dut['CONF']['ResetBcid'] = 0
        self.dut['CONF'].write()
        self.dut['data_rx'].set_en(True)
        self.dut.start_inj()
        print("=====sim=====",end=" ")
        raw=self.dut.get_data_now()
        for i in range(100):
            raw=np.append(raw,self.dut.get_data_now())
            if len(raw) == 3*2:
                break
            print(len(raw),end=" ")
        print(len(raw),"-",i)
        for r in raw:
            print(hex(r),end="")
        dat=interpreter.raw2list(raw,delete_noise=False)
        print("=====sim=====",dat)
        pix=dat[dat["col"]<self.dut.COL] 
        self.assertEqual(len(pix),2)
        self.assertEqual(pix[0]['col'],5)
        self.assertEqual(pix[0]['row'],1)
        self.assertEqual((pix[0]['te']-pix[0]['le'])&0x3F,1)
        self.assertEqual(pix[1]['col'],5)
        self.assertEqual(pix[1]['row'],0)
        self.assertEqual((pix[1]['te']-pix[1]['le'])&0x3F,1)        

if __name__ == '__main__':
    unittest.main()