import time
import numpy as np
from basil.dut import Dut 

# Initialize SourceMeter Unit (SMU) and turn off HV
devices = Dut('/home/lars/git/lf-monopix2-daq/monopix2_daq/periphery.yaml')
devices.init()
devices['SensorBias'].on()

hv_initial = round(float(devices['SensorBias'].get_voltage().split(',')[0]), 0)
print(hv_initial)
voltages = np.array(range(int(hv_initial), -20 - 1, -1))
if np.any(voltages > 0):
    raise ValueError('Voltage has to be negative! Abort to protect device.')

for voltage in voltages:
    devices['SensorBias'].set_voltage(voltage)
    time.sleep(0.2)
values = devices['SensorBias'].get_voltage()
print('V=', values.split(',')[0], ' I=', values.split(',')[1])