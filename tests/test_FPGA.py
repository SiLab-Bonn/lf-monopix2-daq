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

class TestFPGA(test_Monopix2.TestMonopix2):

    def test_00init(self):
        self.dut.init()
        #############################
        ## set readout, injection, monitor
        #self.dut.set_inj_all(inj_n=1,inj_width=40,inj_delay=100)
        #self.dut.set_timestamp640(src="mon")
        #self.dut.set_monoread(sync_timestamp=False)
    def test_01(self):
        fpga_version=self.dut['intf'].read(0x10000,1)[0]
        self.assertEqual(fpga_version,1)

if __name__ == '__main__':
    if len(sys.argv)>1:
        TestFPGA.extra_defines=[sys.argv.pop()]
    unittest.main()
