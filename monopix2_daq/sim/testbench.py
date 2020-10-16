#
# ------------------------------------------------------------
# Copyright (c) All rights reserved
# SiLab, Institute of Physics, University of Bonn
# ------------------------------------------------------------
#

from basil.HL.RegisterHardwareLayer import RegisterHardwareLayer


class testbench(RegisterHardwareLayer):
    '''
    '''
    _registers = {'VERSION': {'descr': {'addr': 0, 'size': 8, 'offset': 0}},
          'DAC_DRIVER': {'descr': {'addr': 1, 'size': 6, 'offset': 0}},
          'DAC_TDAC_LSB': {'descr': {'addr': 2, 'size': 6,  'offset': 0}},
          'DAC_VSF': {'descr': {'addr': 3, 'size': 6, 'offset': 0}},
          'DAC_VPLOAD': {'descr': {'addr': 53, 'size': 6, 'offset': 0}},
          'DAC_VNLOAD': {'descr': {'addr': 4, 'size': 6, 'offset': 0}},
          'DAC_VNFOLL': {'descr': {'addr': 5, 'size': 6, 'offset': 0}},
          'DAC_VPFOLL': {'descr': {'addr': 6, 'size': 6, 'offset': 0}},
          'DAC_VPFB': {'descr': {'addr': 7, 'size': 6, 'offset': 0}},
          'DAC_VAMP2': {'descr': {'addr': 49, 'size': 6, 'offset': 0}},
          'DAC_VAMP1': {'descr': {'addr': 50, 'size': 6, 'offset': 0}},
          'DAC_BLRES': {'descr': {'addr': 51, 'size': 6, 'offset': 0}},
          'MON_DRIVER':   {'descr': {'addr': 1, 'size': 1, 'offset': 6}},
          'MON_TDAC_LSB':    {'descr': {'addr': 2, 'size': 1, 'offset': 6}},
          'MON_VSF':    {'descr': {'addr': 3, 'size': 1, 'offset': 6}},
          'MON_VPLOAD':   {'descr': {'addr': 53, 'size': 1, 'offset': 6}},
          'MON_VNLOAD':   {'descr': {'addr': 4, 'size': 1, 'offset': 6}},
          'MON_VNFOLL':   {'descr': {'addr': 5, 'size': 1, 'offset': 6}},
          'MON_VPFOLL': {'descr': {'addr': 6, 'size': 1, 'offset': 6}},
          'MON_VPFB':     {'descr': {'addr': 7, 'size': 1, 'offset': 6}},
          'MON_VAMP2':   {'descr': {'addr': 49, 'size': 1, 'offset': 6}},
          'MON_VAMP1': {'descr': {'addr': 50, 'size': 1, 'offset': 6}},
          'MON_BLRES': {'descr': {'addr': 51, 'size': 1, 'offset': 6}},

          'READY_HIT': {'descr': {'addr': 48, 'size': 1, 'offset': 0}},
          'RESET_HIT': {'descr': {'addr': 8, 'size': 1, 'offset': 1}},
          'CLK_HIT_GATE': {'descr': {'addr': 8, 'size': 1, 'offset': 0}},
          'CLK_HIT_PHASE': {'descr': {'addr': 8, 'size': 1, 'offset': 2}},

          'TOKOUT_PAD': {'descr': {'addr': 9, 'size': 1, 'offset': 0}},
          'DATAOUT_PAD': {'descr': {'addr': 10, 'size': 1, 'offset': 0}},
          'ENDATACMOS': {'descr': {'addr': 10, 'size': 1, 'offset': 1}},
          'LVDS_OUT_PAD': {'descr': {'addr': 11, 'size': 2, 'offset': 0}},
          'ENDATALVDS': {'descr': {'addr': 11, 'size': 1, 'offset': 2}},
          'ENANABUFFER': {'descr': {'addr': 52, 'size': 1, 'offset': 0}},

          'TIMESTAMP': {'descr': {'addr': 12, 'size': 64}},
          'ENMONITORCOL': {'descr': {'addr': 27, 'size': 56}},
          'NRSTCOL': {'descr': {'addr': 34, 'size': 56}},
          'FREEZECOL': {'descr': {'addr': 41, 'size': 56}},
          }

    _require_version = "==1"

    def __init__(self, intf, conf):
        super(testbench, self).__init__(intf, conf)

    def get_TokOut_PAD(self):
        return self._intf.read_str(
            self._conf['base_addr']+self._registers['TOKOUT_PAD']['descr']['addr'], 
            size=1)[0][7-self._registers['TOKOUT_PAD']['descr']['offset']]

    def get_DataOut_PAD(self):
        return self._intf.read_str(
            self._conf['base_addr']+self._registers['DATAOUT_PAD']['descr']['addr'], 
            size=1)[0][7-self._registers['DATAOUT_PAD']['descr']['offset']]

    def get_EnDataCMOS(self):
        return self._intf.read_str(
            self._conf['base_addr']+self._registers['ENDATACMOS']['descr']['addr'], 
            size=1)[0][7-self._registers['ENDATACMOS']['descr']['offset']]

    def get_EnDataLVDS(self):
        return self._intf.read_str(
            self._conf['base_addr']+self._registers['ENDATALVDS']['descr']['addr'], 
            size=1)[0][7-self._registers['ENDATALVDS']['descr']['offset']]

    def get_READY_HIT(self):
        return self._intf.read_str(
            self._conf['base_addr']+self._registers['READY_HIT']['descr']['addr'], 
            size=1)[0][7-self._registers['READY_HIT']['descr']['offset']]

