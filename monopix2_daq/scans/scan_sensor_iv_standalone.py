import os
import time
import logging
import numpy as np
import tables as tb
from tqdm import tqdm
import matplotlib.pyplot as plt

from basil.dut import Dut  # 4567.9 um z
import monopix2_daq.monopix2 as monopix2

iv_curve_config = {
    'V_start': -0,  # Start value for bias voltage
    'V_stop': -310,  # Stop value for bias voltage
    'V_step': -5,  # Stepsize of bias voltage
    'V_final': 0,  # Return to V_final bias after measurement
    'V_max': -341,  # Max. value allowed for bias voltage
    'max_leakage': 20e-6,  # Max. leakage current allowed before aborting scan
    'wait_cycle': 0.5,  # Min. delay between current measurements
    'n_meas': 5,  # Number of current measurements per voltage step

    # Chip and output file info
    'chip_id': 'LF-Monopix2',
    'sensor_id': 'W02-02',
    'set_preamp': False,
}


class DataTable(tb.IsDescription):
    voltage = tb.Float64Col(pos=0)
    current = tb.Float64Col(pos=1)
    current_err = tb.Float64Col(pos=2)
    n_meas = tb.Float64Col(pos=3)


class IV_Curve_Scan(object):
    scan_id = 'IV_curve'

    def __init__(self, set_preamp, chip_id, sensor_id, max_leakage, **_):

        # Create and open output file
        output_folder = os.path.join(os.getcwd(), "output_data/IV_curves")
        if set_preamp:
            scan_name = "IVcurve_%s_%s_preamp" % (chip_id, sensor_id)
        else:
            scan_name = "IVcurve_%s_%s" % (chip_id, sensor_id)
        self.output_filename = os.path.join(output_folder, scan_name)
        self.output_file = tb.open_file(self.output_filename + '.h5', mode='w', title=self.scan_id)

        self.data = self.output_file.create_table(self.output_file.root, name='IV_data', description=DataTable, title='IVcurve')

        # Initialize SourceMeter Unit (SMU) and turn off HV
        self.smu = Dut('../periphery.yaml')
        self.smu.init()
        self.smu['SensorBias'].off()
        self.smu['SensorBias'].set_current_limit(1.15 * max_leakage)
        time.sleep(0.1)
        logging.info('Initialized sourcemeter: %s' % self.smu['SensorBias'].get_name())

        # Initialize and power DUT (LF-Monopix2) to prevent applying HV to unpowered chip
        m = monopix2.Monopix2(no_power_reset=False)
        m.init()
        if set_preamp:
            m.set_preamp_en(pix='all', overwrite=True)
        time.sleep(5)

    def _scan(self, V_start=-0, V_stop=-10, V_step=-1, V_final=-10, V_max=-100, max_leakage=20e-6, wait_cycle=0.5, n_meas=5, **_):
        ''' Loop through voltage range and measure current at each step n_meas times
        '''

        voltages = range(V_start, V_stop, V_step)
        logging.info('Measure IV for V from %i to %i' % (voltages[0], voltages[-1]))

        self.smu['SensorBias'].set_voltage(0)
        self.smu['SensorBias'].on()

        for voltage in tqdm(voltages, unit='Voltage step'):
            if voltage > 0:
                RuntimeError('Voltage has to be negative! Abort to protect device.')
            if abs(voltage) <= abs(V_max):
                self.smu['SensorBias'].set_voltage(voltage)
                time.sleep(wait_cycle * 10)
                V_currently = voltage
            else:
                logging.info('Maximum voltage with %f V reached, abort', voltage)
                break

            # Measure current
            currents = []
            try:
                current = float(self.smu['SensorBias'].get_current().split(',')[1])
            except Exception:
                logging.warning('Could not measure current, skipping this voltage step!')
                continue

            # Check leakage current limit
            if abs(current) > abs(max_leakage):
                logging.info('Maximum current with %e I reached, abort', current)
                break

            # Take mean over several measuerements
            for _ in range(n_meas):
                current = float(self.smu['SensorBias'].get_current().split(',')[1])
                currents.append(current)
                time.sleep(wait_cycle)

            # Store data
            sel = np.logical_and(np.array(currents) / np.mean(np.array(currents)) < 2.0, np.array(currents) / np.mean(np.array(currents)) > 0.5)
            self.data.row['voltage'] = voltage
            self.data.row['current'] = np.mean(np.array(currents)[sel])
            self.data.row['current_err'] = np.std(currents)
            self.data.row['n_meas'] = n_meas
            self.data.row.append()
            self.data.flush()

        # Close output file
        self.output_file.close()

        # Ramp bias voltage down
        if V_currently != V_final:
            logging.info('Ramping bias voltage down from %f V to %f V', V_currently, V_final)
            for voltage in tqdm(range(V_currently, V_final - V_step, -V_step)):
                self.smu['SensorBias'].set_voltage(voltage)
                time.sleep(0.5)

        logging.info('Scan complete, turning off SMU')
        self.smu['SensorBias'].off()

    def _plot(self, chip_id, sensor_id, **_):

        logging.info('Analyze and plot results')
        with tb.open_file(self.output_filename + '.h5', 'r+') as in_file_h5:
            data = in_file_h5.root.IV_data[:]

        x, y, yerr = data['voltage'] * (-1), data['current'] * (-1), data['current_err'] * (-1)
        plt.clf()
        plt.errorbar(x, y, yerr, fmt=',', ls='', label='IV Data')
        plt.title('IV curve of %s (Sensor ID %s)' % (chip_id, sensor_id))
        plt.yscale('log')
        plt.ylabel('Current / A')
        plt.xlabel('Voltage / V')
        plt.grid()
        plt.legend()
        plt.savefig(self.output_filename + '.pdf')


if __name__ == '__main__':
    scan = IV_Curve_Scan(**iv_curve_config)
    scan._scan(**iv_curve_config)
    scan._plot(**iv_curve_config)
