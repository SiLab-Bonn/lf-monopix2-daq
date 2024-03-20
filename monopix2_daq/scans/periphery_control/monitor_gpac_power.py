import time
import tables as tb
from basil.dut import Dut 

class DataTable(tb.IsDescription):
    timestamp = tb.Int64Col(pos=0)
    voltage = tb.Float16Col(pos=1)
    current = tb.Float16Col(pos=2)

MONITORING_RATE = 5  # in s
OUTPUT_FILE = '/home/lars/mnt/ceph/lschall/lfmonopix2/TID_irradiation/test/gpac_power_monitor'

# Initialize SourceMeter Unit (SMU) and turn off HV
devices = Dut('/home/lars/git/lf-monopix2-daq/monopix2_daq/periphery.yaml')
devices.init()

output_file = tb.open_file(OUTPUT_FILE + '.h5', mode='w', title='GPAC_mon')
data = output_file.create_table(output_file.root, name='gpac_power', description=DataTable, title='gpac_power')

failed_data_read = 0
try:
    while True:
        try:
            data.row['timestamp'] = time.time()
            data.row['voltage'] = devices['LV'].get_voltage(channel=2)
            data.row['current'] = devices['LV'].get_current(channel=2)
            data.row.append()
            data.flush()
        except:
            failed_data_read += 1
            pass

        time.sleep(MONITORING_RATE)
except KeyboardInterrupt:
    pass

print('Amount of failed data reads: ', failed_data_read)
