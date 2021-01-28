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
import monopix2_daq.monopix2 as monopix2
import monopix2_daq.analysis.interpreter_idx as interpreter

HIT_FILE0 = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
           "tests/data/"+os.path.basename(os.path.abspath(__file__))[:-2].split("_")[0]+"_"+os.path.basename(os.path.abspath(__file__))[:-2].split("_")[-1]+"csv")  

class TestMonopix2(unittest.TestCase):
    sim_file = "monopix2_tb.sv"
    extra_defines= [] #["_GATE_LEVEL_NETLIST_","_CLK_HIT_160MHZ_"]

    hit_file=[
        #HIT_FILE0,     ## test02     
        #HIT_FILE0[:-4]+"03.csv", ## test03  
        ]

    @classmethod
    def setUpClass(cls):
        daq_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__))) #../
        print("daq_dir", daq_dir)
        rtl_dir=os.path.join(os.path.dirname(os.path.abspath(__file__)),"rtl")
        print("rtl_dir", rtl_dir)

        os.environ['SIM'] = 'questa'
        #os.environ['SIM'] = 'icarus'
        if os.environ['SIM']=='icarus':
            cls.extra_defines.append('COLS=2')

        os.environ['WAVES'] = '1'
        os.environ['GUI'] = '0' # 1 for gui mode
        #os.environ['COCOTB_RESOLVE_X']="RANDOM" ##VALUE_ERROR
        os.environ['SIMULATION_MODULES'] = yaml.dump({'tests.drivers.HitDataFile': {
                'filename': cls.hit_file
            }})
        sdf_file=""
        cls.option="rtl"
        for exdef in cls.extra_defines:
            if "_GATE_LEVEL_NETLIST_" in exdef:
                if len(exdef.split("="))==2:
                    cls.option=exdef.split("=")[1]
                else:
                    cls.option="typ"
                print("=====sim=====",os.path.join(os.path.join(daq_dir, 'tests/hdl'),cls.sim_file))
                
                sdf_file="+sdf_verbose" + \
                         " -sdf{0:s} chip=/faust/user/thirono/workspace/lf-monopix2/lf-monopix2_mine/netlist/signoff_noAna.sdf +{0:s}delays".format(cls.option)
                break
        cocotb_compile_and_run(
            sim_files = [os.path.join(os.path.join(daq_dir, 'tests/hdl'),cls.sim_file)],
            extra_defines = cls.extra_defines,
            test_module='monopix2_daq.sim.Test',
            sim_bus = 'monopix2_daq.sim.SiLibUsbBusDriver',
            include_dirs = (daq_dir + "/tests/hdl",daq_dir, daq_dir + "/firmware/src",rtl_dir),
            extra = '\nVSIM_ARGS += -wlf /tmp/monopix2_{0:s}.wlf {1:s}\n'.format(cls.option, sdf_file) # -debugDB -t 1ps  for debugging
        )

        with open(daq_dir + '/monopix2_daq/monopix2.yaml', 'r') as f:
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
        self.dut.logger.info("hitin{}".format(fname))
        self.fcsv=open(fname)
        self.csv_reader = csv.reader(self.fcsv)

    def util_pauseHIT(self):
        self.dut['tb'].CLK_HIT_GATE = 0

    def util_resumeHIT(self):
        self.dut['tb'].CLK_HIT_GATE = 1

    def util_shiftphaseHIT(self,shift = 0):
        self.dut['tb'].CLK_HIT_PHASE = shift

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
        else:
            if isinstance(defval,bool):
                self.dut['CONF_DC'].setall(defval)
            else:
                self.dut['CONF_DC']['Col0'] = bitarray.bitarray(list(self.dut.PIXEL_CONF[bit][defval*2,:]))
                self.dut['CONF_DC']['Col1'] = bitarray.bitarray(list(self.dut.PIXEL_CONF[bit][defval*2+1,::-1]))

            self.dut['CONF_SR']['EnSRDCol'].setall(True)
            self.dut['CONF']['Ld_Cnfg'] = 0
            self.dut['CONF'].write()
            self.dut['CONF_SR'].write()
            while not self.dut['CONF_SR'].is_ready:
                pass
            
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
        self.dut['CONF_SR']["TrimLd"] = 15
        self.dut['CONF']['ClkOut'] = ClkOut  ###Readout OFF
        self.dut['CONF']['ClkBX'] = ClkBX
        self.dut['CONF'].write()

if __name__ == '__main__':
    if len(sys.argv)>1:
        TestMonopix2.extra_defines=[sys.argv.pop()]
    unittest.main()
