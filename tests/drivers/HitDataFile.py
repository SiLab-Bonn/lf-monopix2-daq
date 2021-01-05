

#---------------------------------------------------------------------
#  Take data file and inteprets hits and triggers, passes them to chip
#--------------------------------------------------------------------
# Author/s: T. Hemperek

import cocotb
import logging
from cocotb.binary import BinaryValue
from cocotb.triggers import RisingEdge, ReadOnly, Timer, ReadWrite
from cocotb.drivers import BusDriver
from cocotb.result import ReturnValue
from cocotb.clock import Clock

from basil.utils.BitLogic import BitLogic

import csv
import requests
import sys
import numpy as np
import time

COLS=56
ROWS=340

class HitDataFile(BusDriver):

    _signals = ['CLK_HIT', 'HIT', 'READY_HIT','RESET_HIT']

    def __init__(self, entity, filename):
        BusDriver.__init__(self, entity, "", entity.CLK_HIT)

        val = '0' * len(self.bus.HIT)
        self.hit = BinaryValue(n_bits=len(self.bus.HIT), value=val)
        self.filename = filename
        if isinstance(self.filename,str):
            self.filename=[self.filename]
        logging.info('HitDataFile: Loading file... ' + str(filename))

    @cocotb.coroutine
    def run(self):
        self.bus.HIT <= self.hit
        self.bus.READY_HIT <= 0
        total_hits = 0
        for f in self.filename:
            logging.info('HitDataFile: filename={0}'.format(f))
            while 1:
                yield RisingEdge(self.clock)
                yield ReadWrite()
                res = self.bus.RESET_HIT.value.integer
                if(res == 1):
                    break
            self.bus.READY_HIT <= 1
            while 1:
                yield RisingEdge(self.clock)
                yield ReadWrite()
                res = self.bus.RESET_HIT.value.integer
                if(res == 0):
                    break
            self.bus.READY_HIT <= 0
            bv = BitLogic(len(self.hit))
            tot_hist = np.full([len(self.hit)], 0, dtype=np.uint16)
            bx = -1
            with open(f) as csvfile:
                csv_reader =  csv.reader(csvfile, delimiter=',')
                logging.info('HitDataFile: starting hits {0}'.format(f))
                for file_row in csv_reader:
                    if file_row[0][0] =="#":
                        continue
                    bxid = int(file_row[0])
                    col = int(file_row[1])
                    row = int(file_row[2])
                    tot = int(file_row[3])

                    logging.info('loading bxid={0:d} col={1:d} row={2:d} tot={3:d} bx={4:d}'.format(bxid,col,row,tot,bx))

                    while bxid > bx:
                        yield RisingEdge(self.clock)
                        yield Timer(5000)
                        bx += 1

                        for pix in np.where(tot_hist > 0)[0]:
                            bv[pix] = 1
                            total_hits += 1
                        self.hit.assign(str(bv))
                        self.bus.HIT <= self.hit
                        tot_hist[tot_hist > 0] -= 1
                        bv.setall(False)
                        
                    if bxid == bx:     
                        if((col >= 0) and (col < COLS) and (row >= 0) and (row < ROWS)):
                            pixn = col * ROWS + row
                            tot_hist[pixn] = tot_hist[pixn] + tot
                    else:
                        raise ValueError("Error,bxid={0:d},bx={0:d}".format(bxid,bx))
                    #res=self.bus.RESET_HIT.value.integer
                    #if res==1:
                    #    break
            self.bus.HIT <= 0
            logging.info('HitDataFile: bx={0:d} End of filename {1:s}'.format(bx,f))
        yield RisingEdge(self.clock)
        yield Timer(5000)
        logging.info('=====================HitDataFile: %u hits sent to DUT', total_hits)
