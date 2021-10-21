import copy
import time

import numpy as np
from matplotlib import cm

from PyQt5 import Qt
import pyqtgraph as pg
from pyqtgraph.Qt import QtGui
import pyqtgraph.ptime as ptime
from pyqtgraph.dockarea import DockArea, Dock

from online_monitor.utils import utils
from online_monitor.receiver.receiver import Receiver


def generateColorMapLut(cm_name):
    # https://github.com/pyqtgraph/pyqtgraph/issues/561
    colormap = copy.copy(cm.get_cmap(cm_name))
    colormap._init()
    lut = (colormap._lut[:-3] * 255).astype(np.uint8)
    return lut


class LFMonopix2(Receiver):

    def setup_receiver(self):
        # We want to change converter settings
        self.set_bidirectional_communication()

    def setup_widgets(self, parent, name):
        dock_area = DockArea()
        parent.addTab(dock_area, name)

        # Docks
        dock_occcupancy = Dock("Occupancy", size=(400, 400))
        dock_tot = Dock("Time over threshold values (TOT)", size=(400, 400))
        # dock_tdc = Dock("TDC", size=(400, 400)) # no need for TDC so far
        dock_status = Dock("Status", size=(800, 40))
        dock_area.addDock(dock_occcupancy, 'left')
        dock_area.addDock(dock_tot, 'right', dock_occcupancy)
        # dock_area.addDock(dock_tdc, 'right', dock_tot)
        dock_area.addDock(dock_status, 'top')

        # Status dock on top
        cw = QtGui.QWidget()
        cw.setStyleSheet("QWidget {background-color:white}")
        layout = QtGui.QGridLayout()
        cw.setLayout(layout)
        self.rate_label = QtGui.QLabel("Readout Rate\n0 Hz")
        self.hit_rate_label = QtGui.QLabel("Hit Rate\n0 Hz")
        self.timestamp_label = QtGui.QLabel("Data Timestamp\n")
        self.plot_delay_label = QtGui.QLabel("Plot Delay\n")
        self.scan_parameter_label = QtGui.QLabel("Parameter ID\n")
        self.spin_box = Qt.QSpinBox(value=0)
        self.spin_box.setMaximum(1000000)
        self.spin_box.setSuffix(" Readouts")
        self.col = Qt.QSpinBox(value=-1)
        self.col.singleStep()
        self.col.setRange(-1, 56)
        self.col.setSuffix(" Col")
        self.col.setValue(-1)
        self.row = Qt.QSpinBox(value=-1)
        self.row.singleStep()
        self.row.setRange(-1, 340)
        self.row.setSuffix(" Row")
        self.row.setValue(-1)
        self.reset_button = QtGui.QPushButton('Reset')
        self.noisy_checkbox = QtGui.QCheckBox('Mask noisy pixels')
        self.occ_invertY = QtGui.QCheckBox('invertY')
        self.occ_invertY.setCheckState(2)
        self.occ_invertX = QtGui.QCheckBox('invertX')
        layout.addWidget(self.timestamp_label, 0, 0, 0, 1)
        layout.addWidget(self.plot_delay_label, 0, 1, 0, 1)
        layout.addWidget(self.rate_label, 0, 2, 0, 1)
        layout.addWidget(self.hit_rate_label, 0, 3, 0, 1)
        layout.addWidget(self.scan_parameter_label, 0, 5, 0, 1)
        layout.addWidget(self.spin_box, 0, 6, 0, 1)
        layout.addWidget(self.noisy_checkbox, 0, 7, 0, 1)
        layout.addWidget(self.col, 0, 8, 0, 1)
        layout.addWidget(self.row, 0, 9, 0, 1)
        layout.addWidget(self.occ_invertX, 0, 10, 0, 1)
        layout.addWidget(self.occ_invertY, 0, 11, 0, 1)
        layout.addWidget(self.reset_button, 0, 12, 0, 1)
        dock_status.addWidget(cw)

        # Connect widgets
        self.reset_button.clicked.connect(lambda: self.send_command('RESET'))
        self.spin_box.valueChanged.connect(lambda value: self.send_command(str(value)))
        self.col.valueChanged.connect(lambda value: self.send_command('COL %d' % value))
        self.row.valueChanged.connect(lambda value: self.send_command('ROW %d' % value))
        self.noisy_checkbox.stateChanged.connect(lambda value: self.send_command('MASK %d' % value))

        # Different plot docks
        occupancy_graphics = pg.GraphicsLayoutWidget()
        occupancy_graphics.show()
        view = occupancy_graphics.addViewBox()
        view.invertY(True)
        self.occupancy_img = pg.ImageItem(border='w')
        # Set colormap from matplotlibs
        lut = generateColorMapLut("viridis")

        self.occupancy_img.setLookupTable(lut, update=True)
        # view.addItem(self.occupancy_img)
        self.plot = pg.PlotWidget(viewBox=view, labels={'bottom': 'Column', 'left': 'Row'})
        self.plot.addItem(self.occupancy_img)

        dock_occcupancy.addWidget(self.plot)

        tot_plot_widget = pg.PlotWidget(background="w", labels={'bottom': 'ToT', 'left': '#hits'})
        self.tot_plot = tot_plot_widget.plot(np.linspace(-0.5, 15.5, 17),
                                             np.zeros((16)), stepMode=True)
        tot_plot_widget.showGrid(y=True)
        dock_tot.addWidget(tot_plot_widget)

        # tdc_widget = pg.PlotWidget()
        # self.tdc_plot = tdc_widget.plot(np.linspace(-0.5, 500 - 0.5, 500 + 1),
        #                                np.zeros((500)), stepMode=True)
        # tdc_widget.showGrid(y=True)
        # dock_tdc.addWidget(tdc_widget)

        self.plot_delay = 0

    def deserialize_data(self, data):
        return utils.simple_dec(data)[1]

    def _update_rate(self, fps, hps, recent_total_hits):
        self.rate_label.setText("Readout Rate\n%d Hz" % fps)
        if self.spin_box.value() == 0:  # show number of hits, all hits are integrated
            self.hit_rate_label.setText("Total Hits\n%d" % int(recent_total_hits))
        else:
            self.hit_rate_label.setText("Hit Rate\n%d Hz" % int(hps))

    def _update_inverted_axis(self):
        '''Inverts occupancy map x or y axis if box is checked'''
        if self.occ_invertX.checkState() == 0:
            self.plot.getViewBox().invertX(False)
        else:
            self.plot.getViewBox().invertX(True)

        if self.occ_invertY.checkState() == 0:
            self.plot.getViewBox().invertY(False)
        else:
            self.plot.getViewBox().invertY(True)

    def handle_data(self, data):
        # Histogram data
        self.occupancy_img.setImage(data['occupancy'][:, :],
                                    autoDownsample=True)
        self.tot_plot.setData(x=np.arange(-0.5, 64.5, 1),
                              y=data['tot_hist'], fillLevel=0,
                              brush=(0, 0, 255, 150))
        # self.tdc_plot.setData(x=np.linspace(-0.5, data['tdc_hist'].shape[0] - 0.5, data['tdc_hist'].shape[0] + 1),
        #                       y=data['tdc_hist'],
        #                       stepMode=True,
        #                       fillLevel=0, brush=(0, 0, 255, 150))

        # Meta data
        self._update_rate(data['meta_data']['fps'],
                          data['meta_data']['hps'],
                          data['meta_data']['total_hits'])
        self._update_inverted_axis()
        self.timestamp_label.setText("Data Timestamp\n%s" % time.asctime(time.localtime(data['meta_data']['timestamp_stop'])))
        self.scan_parameter_label.setText("Parameter ID\n%d" % data['meta_data']['scan_par_id'])
        now = ptime.time()
        self.plot_delay = self.plot_delay * 0.9 + (now - data['meta_data']['timestamp_stop']) * 0.1
        self.plot_delay_label.setText("Plot Delay\n%s" % 'not realtime' if abs(self.plot_delay) > 5 else "Plot Delay\n%1.2f ms" % (self.plot_delay * 1.e3))
