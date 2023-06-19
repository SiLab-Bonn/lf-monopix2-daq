import os
import time
import logging
import numpy as np
import tables as tb

from matplotlib.backends import backend_pdf
from matplotlib.figure import Figure
from matplotlib.backends.backend_agg import FigureCanvasAgg as FigureCanvas

from basil.dut import Dut 
import monopix2_daq.monopix2 as monopix2


scan_config = {
    'wait_cycle': 0.2,  # Min. delay between current measurements
    'n_meas': 5,  # Number of current measurements per voltage step
    'reg_start': 0,  # Start value for register setting
    'reg_stop': 64,  # Stop value for register setting
    'reg_step': 1,  # Register setting step size

    # Chip info
    'sensor_id': 'W02-01_unirr',
}


DACs = {
    'Vsf': {'Mon_Vsf': 1},
    'VPFB': {'Mon_VPFB': 1},
    'VPLoad': {'Mon_VPLoad': 1},
    'VNLoad': {'Mon_VNLoad': 1},
    'VNFoll': {'Mon_VNFoll': 1},
    'VPFoll': {'Mon_VPFoll': 1},
    'VAmp1': {'Mon_VAmp1': 1},
    'VAmp2': {'Mon_VAmp2': 1},
    'TDAC_LSB': {'Mon_TDAC_LSB': 1},
    'BLRes': {'Mon_BLRes': 1},
    'Driver': {'Mon_Driver': 1},
}


class DataTable(tb.IsDescription):
    dac_setting = tb.Int8Col(pos=0)
    current = tb.Float64Col(pos=1)
    current_err = tb.Float64Col(pos=2)
    n_meas = tb.Int8Col(pos=3)


class DAC_linearity_scan(object):
    scan_id = 'DAC_linearity'

    def __init__(self, sensor_id, **kwargs):

        # Create and open output file
        output_folder = os.path.join(os.getcwd(), "output_data", sensor_id)
        scan_name = "DAClinearity_%s" % (sensor_id)
        self.output_filename = os.path.join(output_folder, scan_name)
        self.output_file = tb.open_file(self.output_filename + '.h5', mode='w', title=self.scan_id)

        # Initialize SourceMeter Unit (SMU) and turn off HV
        self.smu = Dut('../periphery.yaml')
        self.smu.init()
        self.smu['SensorBias'].off()
        time.sleep(0.1)

        # Initialize and power DUT (LF-Monopix2) to prevent applying HV to unpowered chip
        self.m = monopix2.Monopix2(no_power_reset=True)
        self.m.init()
        self.m.set_preamp_en(pix='none', overwrite=True)

    def _scan(self, n_meas=5, wait_cycle=0.2, reg_start=0, reg_stop=64, reg_step=1, **kwargs):

        # Loop through registers
        for dac, monitor in DACs.items():
            logging.info('Scanning register {0}'.format(dac))
            self.m.set_global_reg(**monitor)
            # self.m.dac_status(log=True)
            # Create table in output file
            self.data = self.output_file.create_table(self.output_file.root, name=dac, description=DataTable, title=dac)

            # Loop through register settings
            for dac_setting in range(reg_start, reg_stop, reg_step):
                self.m.set_global_reg(**{dac: dac_setting})  # Needs to be like this because of monopix function definition
                time.sleep(.5)
                currents = []
                for _ in range(n_meas):
                    current = float(self.smu['Multimeter'].get_current())
                    currents.append(current)
                    time.sleep(wait_cycle)

                # Store data
                sel = np.logical_and(np.array(currents) / np.mean(np.array(currents)) < 2.0, np.array(currents) / np.mean(np.array(currents)) > 0.5)
                self.data.row['dac_setting'] = dac_setting
                self.data.row['current'] = np.mean(np.array(currents)[sel])
                self.data.row['current_err'] = np.std(currents)
                self.data.row['n_meas'] = n_meas
                self.data.row.append()
                self.data.flush()

        # Close output file
        self.output_file.close()

        logging.info('Scan complete!')

    def _plot(self):

        def _dac_linearity_plot(data, output_pdf):
            fig = Figure(tight_layout=True)
            FigureCanvas(fig)
            ax = fig.add_subplot(111)
            ax.errorbar(data[:]['dac_setting'], data[:]['current'] * 1e6, data[:]['current_err'] * 1e6, label=table.name, fmt='.')
            ax.grid()
            ax.set_xlabel('DAC setting')
            ax.set_ylabel('Reference Current / $\\mu$A')
            ax.legend(loc=2)
            output_pdf.savefig(fig)

        output_pdf = backend_pdf.PdfPages(self.output_filename + '.pdf')

        with tb.open_file(self.output_filename + '.h5', 'r') as in_file:
            for table in in_file.root:
                _dac_linearity_plot(table, output_pdf)

        output_pdf.close()


if __name__ == '__main__':
    scan = DAC_linearity_scan(**scan_config)
    scan._scan(**scan_config)
    scan._plot()
