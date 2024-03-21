import time
import yaml
import tables as tb
from basil.dut import Dut 


class DataTable(tb.IsDescription):
    timestamp = tb.Int64Col(pos=0)
    voltage = tb.Float16Col(pos=1)
    current = tb.Float16Col(pos=2)

with open('../../testbench.yaml') as tb_file:
    bench = yaml.full_load(tb_file)

MONITORING_RATE = 5  # in s
OUTPUT_FILE = bench['general']['output_directory'] + 'gpac_power_monitor'

# Initialize SourceMeter Unit (SMU) and turn off HV
devices = Dut('../../periphery.yaml')
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
    output_file.close()

print('Amount of failed data reads: ', failed_data_read)
