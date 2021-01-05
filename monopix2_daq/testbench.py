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
          'DAC_BLRES': {'descr': {'addr': 1, 'size': 6, 'offset': 0}},
          'DAC_VAMP': {'descr': {'addr': 2, 'size': 6,  'offset': 0}},
          'DAC_VPFB': {'descr': {'addr': 3, 'size': 6, 'offset': 0}},
          'DAC_VFOLL': {'descr': {'addr': 4, 'size': 6, 'offset': 0}},
          'DAC_VLOAD': {'descr': {'addr': 5, 'size': 6, 'offset': 0}},
          'DAC_TDAC_LSB': {'descr': {'addr': 6, 'size': 6, 'offset': 0}},
          'DAC_VSF': {'descr': {'addr': 7, 'size': 6, 'offset': 0}},
          'MON_BLRES':   {'descr': {'addr': 1, 'size': 1, 'offset': 6}},
          'MON_VAMP':    {'descr': {'addr': 2, 'size': 1, 'offset': 6}},
          'MON_VPFB':    {'descr': {'addr': 3, 'size': 1, 'offset': 6}},
          'MON_VFOLL':   {'descr': {'addr': 4, 'size': 1, 'offset': 6}},
          'MON_VLOAD':   {'descr': {'addr': 5, 'size': 1, 'offset': 6}},
          'MON_LSBDACL': {'descr': {'addr': 6, 'size': 1, 'offset': 6}},
          'MON_VSF':     {'descr': {'addr': 7, 'size': 1, 'offset': 6}},

          'HIT_STATE': {'descr': {'addr': 8, 'size': 2, 'offset': 0}},

          'TOKOUT_PAD': {'descr': {'addr': 9, 'size': 1, 'offset': 0}},
          'DATAOUT_PAD': {'descr': {'addr': 10, 'size': 1, 'offset': 0}},
          'ENDATACMOS': {'descr': {'addr': 10, 'size': 1, 'offset': 1}},
          'LVDS_OUT_PAD': {'descr': {'addr': 11, 'size': 2, 'offset': 0}},
          'ENDATALVDS': {'descr': {'addr': 11, 'size': 1, 'offset': 2}},

          'TIMESTAMP': {'descr': {'addr': 12, 'size': 64}},
          
          'INJENCOL': {'descr': {'addr': 20, 'size': 56}},
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

