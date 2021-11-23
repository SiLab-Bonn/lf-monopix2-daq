import numpy as np
import tables as tb
import math
import matplotlib
import logging
import copy
import yaml
import matplotlib.pyplot as plt

from scipy.optimize import curve_fit
from matplotlib import colors, cm
from matplotlib.backends.backend_pdf import PdfPages
from matplotlib.figure import Figure
from matplotlib.artist import setp
from matplotlib.backends.backend_agg import FigureCanvasAgg as FigureCanvas
from mpl_toolkits.axes_grid1 import make_axes_locatable

COL_SIZE = 56 
ROW_SIZE = 340

logging.basicConfig(format="%(asctime)s - [%(name)-8s] - %(levelname)-7s %(message)s")
loglevel = logging.INFO

TITLE_COLOR = '#07529a'
OVERTEXT_COLOR = '#07529a'


class Plotting(object):

    def __init__(self, analyzed_data_file,  cal_factor=1, pdf_file=None, save_png=False, save_single_pdf=False):
        self.logger = logging.getLogger('Plotting')
        self.logger.setLevel(loglevel)

        self.save_png = save_png
        self.save_single_pdf = save_single_pdf
        self.clustered = False

        self.calibration = {'e_conversion_slope': cal_factor, 'e_conversion_offset': 0, 'e_conversion_slope_error': 0, 'e_conversion_offset_error': 0}
        self.qualitative = False

        if pdf_file is None:
            self.filename = '.'.join(analyzed_data_file.split('.')[:-1]) + '.pdf'
        else:
            self.filename = pdf_file
        self.out_file = PdfPages(self.filename)

        self.cb_side = ROW_SIZE > COL_SIZE

        with tb.open_file(analyzed_data_file, 'r') as in_file:
            try:
                self.HistOcc = in_file.root.HistOcc[:]
                self.HitData = in_file.root.Dut[:]
            except:
                pass
            self.scan_kwargs = yaml.full_load(in_file.root.kwargs[0])
            self.run_config={}
            try:
                for value in in_file.root.Dut.attrs._v_attrnamesuser:
                    self.run_config[value] = yaml.full_load(in_file.root.Dut.attrs[value])
            except tb.NoSuchNodeError:
                for value in in_file.root.meta_data.attrs._v_attrnamesuser:
                    self.run_config[value] = yaml.full_load(in_file.root.meta_data.attrs[value])

            if self.run_config['scan_id'] in ['scan_threshold', 'global_threshold_tuning', 'local_threshold_tuning']:
                self.HistSCurve = in_file.root.HistSCurve[:]
                self.ThresholdMap = in_file.root.ThresholdMap[:, :]
                self.Chi2Map = in_file.root.Chi2Map[:, :]
                self.NoiseMap = in_file.root.NoiseMap[:]
                # self.n_failed_scurves = self.n_enabled_pixels - len(self.ThresholdMap[self.ThresholdMap != 0])
               
            try:
                self.EnPre = in_file.root.pixel_conf.EnPre[:]
                self.EnInj = in_file.root.pixel_conf.EnInj[:]
                self.EnMonitor = in_file.root.pixel_conf.EnMonitor[:]
                self.Trim = in_file.root.pixel_conf.Trim[:]
            except tb.NoSuchNodeError:
                self.logger.error("No pixel_conf node available in: {0} (Looking for pixel_conf_before...)".format(analyzed_data_file))

            try:
                self.EnPre_before = in_file.root.pixel_conf_before.EnPre[:]
                self.EnInj_before = in_file.root.pixel_conf_before.EnInj[:]
                self.EnMonitor_before = in_file.root.pixel_conf_before.EnMonitor[:]
                self.Trim_before = in_file.root.pixel_conf_before.Trim[:]
            except tb.NoSuchNodeError:
                self.logger.error("No pixel_conf_before node available in: {0}".format(analyzed_data_file))
            
            try:
                self.Cluster = in_file.root.Cluster[:]
                self.HistClusterSize = in_file.root.HistClusterSize[:]
                self.HistClusterShape = in_file.root.HistClusterShape[:]
                self.HistClusterTot = in_file.root.HistClusterTot[:]
                self.clustered = True
            except tb.NoSuchNodeError:
                pass

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_value, traceback):
        if self.out_file is not None and isinstance(self.out_file, PdfPages):
            self.logger.info('Closing output PDF file: %s',
                             str(self.out_file._file.fh.name))
            self.out_file.close()

    def create_standard_plots(self):
        self.create_occupancy_map()
        self.create_fancy_occupancy()
        self.create_tot_hist()
        self.create_pixel_conf_maps()

        if self.clustered:
            self.create_cluster_tot_plot()
            self.create_cluster_shape_plot()
            self.create_cluster_size_plot()

    def create_config_table(self):
        try:
            dat=self.run_config["power_status"]
            dat.update(self.run_config["dac_status"])
            self.table_values(dat=dat, title="Chip configuration")
        except Exception:
            self.logger.error('Not possible to make a table for the final configuration values.')

        try:
            dat=self.run_config["power_status_before"]
            dat.update(self.run_config["dac_status_before"])
            self.table_values(dat=dat, title="Chip configuration (Initial)")
        except Exception:
            self.logger.error('Not possible to make a table for the initial configuration values.')

    def create_occupancy_map(self):
        try:
            if self.run_config['scan_id'] in ['scan_threshold', 'threshold_tuning']:
                title = 'Integrated occupancy'
            else:
                title = 'Occupancy'

            self._plot_occupancy(hist=self.HistOcc[:].T, suffix='occupancy', title=title, z_max=np.ceil(1.1 * np.amax(self.HistOcc[:])))  # TODO: get mask and enable here
        except Exception:
            self.logger.error('Could not create occupancy map!')

    def create_fancy_occupancy(self):
        try:
            self._plot_fancy_occupancy(hist=self.HistOcc[:].T)
        except Exception:
            self.log.error('Could not create fancy occupancy plot!')

    def create_tot_hist(self):
        try:
            tot_data = np.zeros(64)
            for i in np.argwhere(np.logical_and(self.HitData['cnt'] < 2, self.HitData['col'] < 60)).ravel():
                tot_data[(self.HitData['te'][i] - self.HitData['le'][i]) & 0x3F] += 1

            self._plot_tot_hist(hist=tot_data)
        except Exception:
            self.log.error('Could not create ToT histogram!')

    def create_pixel_conf_maps(self):
        try:
            self._plot_occupancy(hist=self.EnPre[:].T, suffix='EnPre__', title="EnPre", z_max=1, z_min=0, z_label="Enable Bit", scale_mode="binary")
            self._plot_occupancy(hist=self.EnInj[:].T, suffix='EnInj__', title="EnInj", z_max=1, z_min=0, z_label="Enable Bit", scale_mode="binary")
            self._plot_occupancy(hist=self.EnMonitor[:].T, suffix='EnMon__', title="EnMonitor", z_max=1, z_min=0,  z_label="Enable Bit", scale_mode="binary")
            self._plot_occupancy(hist=self.Trim[:].T, suffix='Trim__', title="Trim", z_max=15, z_min=0, z_label="TRIM DAC value", scale_mode="integer")
        except Exception:
            self.logger.error('There is not a pixel_conf available')

        try:
            self._plot_occupancy(hist=self.EnPre_before[:].T, suffix='EnPre__', title="EnPre (Initial)", z_max=1, z_min=0, z_label="Enable Bit", scale_mode="binary")
            self._plot_occupancy(hist=self.EnInj_before[:].T, suffix='EnInj__', title="EnInj (Initial)", z_max=1, z_min=0, z_label="Enable Bit", scale_mode="binary")
            self._plot_occupancy(hist=self.EnMonitor_before[:].T, suffix='EnMon__', title="EnMonitor (Initial)", z_max=1, z_min=0, z_label="Enable Bit", scale_mode="binary")
            self._plot_occupancy(hist=self.Trim_before[:].T, suffix='Trim__', title="Trim (Initial)", z_max=15, z_min=0, z_label="TRIM DAC value", scale_mode="integer")
        except Exception:
            self.logger.error('There is not a pixel_conf_before available')
        
    def create_threshold_map(self, electron_axis = False):
        try:
            mask = np.full((COL_SIZE, ROW_SIZE), False)
            sel = self.Chi2Map[:] > 0.  # Mask not converged fits (chi2 = 0)
            mask[~sel] = True

            self._plot_occupancy(hist=np.ma.masked_array(self.ThresholdMap, mask).T,
                                    electron_axis=electron_axis,
                                    z_label='Threshold',
                                    title='Threshold Map',
                                    show_sum=False,
                                    suffix='threshold_map',
                                    z_max='maximum',
                                    scale_mode=None)
        except Exception:
            self.logger.error('Could not create threshold map!')

    def create_noise_map(self, electron_axis = False):
        try:
            mask = np.full((COL_SIZE, ROW_SIZE), False)
            sel = self.Chi2Map[:] > 0.  # Mask not converged fits (chi2 = 0)
            mask[~sel] = True

            self._plot_occupancy(hist=np.ma.masked_array(self.NoiseMap, mask).T,
                                 electron_axis=electron_axis,
                                 z_label='ENC',
                                 title='ENC Map',
                                 show_sum=False,
                                 suffix='enc_map',
                                 z_max='maximum',
                                 scale_mode=None)
        except Exception:
            self.logger.error('Could not create noise map!')

    def create_scurves_plot(self, scan_parameter_name='Scan parameter', electron_axis = False, max_occ=None):
        try:
            if self.run_config['scan_id'] == 'scan_threshold':
                scan_parameter_name = 'Injection [V]'
                electron_axis = electron_axis

                self._plot_scurves(scurves=self.HistSCurve[:,:,:],
                                    scan_parameters=np.arange(self.scan_kwargs["injlist_param"][0],
                                                    self.scan_kwargs["injlist_param"][1],
                                                    self.scan_kwargs["injlist_param"][2]),
                                    electron_axis=electron_axis,
                                    scan_parameter_name=scan_parameter_name,
                                    max_occ=self.scan_kwargs["inj_n_param"],
                                    title="S-Curves")
        except Exception:
            self.logger.error('Could not create scurve plot!')

    def create_single_scurves(self, scan_parameter_name='Scan parameter', electron_axis = False, max_occ=None):
        try:
            if self.run_config['scan_id'] == 'scan_threshold':
                scan_parameter_name = 'Injection [V]'
                electron_axis = electron_axis

                self._plot_single_scurves(scurves=self.HistSCurve[:,:,:],
                                    scan_parameters=np.arange(self.scan_kwargs["injlist_param"][0],
                                                    self.scan_kwargs["injlist_param"][1],
                                                    self.scan_kwargs["injlist_param"][2]),
                                    electron_axis=electron_axis,
                                    scan_parameter_name=scan_parameter_name,
                                    max_occ=self.scan_kwargs["inj_n_param"],
                                    title="S-Curves")
        except Exception:
            self.logger.error('Could not create single scurve plot!')

    def create_threshold_plot(self, logscale=False, scan_parameter_name='Scan parameter', electron_axis=False):
        try:
            title = 'Threshold distribution'
            if self.run_config['scan_id'] in ['scan_threshold']:
                #plot_range = np.arange(0.5, 80.5, 1)  # TODO: Get from scan
                plot_range = None
            # elif self.run_config['scan_id'] == 'fast_threshold_scan':
            #     plot_range = np.array(self.scan_params[:]['vcal_high'] - self.scan_params[:]['vcal_med'], dtype=np.float)
            #     scan_parameter_name = '$\Delta$ DU'
            #     electron_axis = True
            # elif self.run_config['scan_id'] == 'global_threshold_tuning':
            #     plot_range = range(self.run_config['VTH_stop'],
            #                        self.run_config['VTH_start'],
            #                        self.run_config['VTH_step'])
            #     scan_parameter_name = self.run_config['VTH_name']
            #     electron_axis = False
            # elif self.run_config['scan_id'] == 'injection_delay_scan':
            #     scan_parameter_name = 'Finedelay [LSB]'
            #     electron_axis = False
            #     plot_range = range(0, 16)
            #     title = 'Fine delay distribution for enabled pixels'

            mask = np.full((COL_SIZE, ROW_SIZE), False)
            sel = np.logical_and(self.Chi2Map > 0., self.ThresholdMap > 0)  # Mask not converged fits (chi2 = 0)
            mask[~sel] = True

            data = np.ma.masked_array(self.ThresholdMap, mask)
            data_th = data[:,:]

            self._plot_distribution(data_th.T,
                                    plot_range=plot_range,
                                    electron_axis=electron_axis,
                                    x_axis_title=scan_parameter_name,
                                    title="Threshold distribution",
                                    log_y=logscale,
                                    print_failed_fits=False,
                                    suffix='threshold_distribution')                    
        except Exception as e:
            self.logger.error('Could not create threshold plot! ({0})'.format(e))

    def create_stacked_threshold_plot(self, scan_parameter_name='Scan parameter', electron_axis=False):
        try:
            plot_range = None

            mask = np.full((COL_SIZE, ROW_SIZE), False)
            sel = np.logical_and(self.EnPre[:] == 1, self.Trim[:] < 17)
            mask[~sel] = True
            tdac_map = np.ma.masked_array(self.Trim, mask)
            th_map = np.ma.masked_array(self.ThresholdMap, mask)

            self._plot_stacked_threshold(data=th_map.T,
                                         tdac_mask=tdac_map.T,
                                         plot_range=plot_range,
                                         electron_axis=electron_axis,
                                         x_axis_title=scan_parameter_name,
                                         y_axis_title='# of pixels',
                                         title='Threshold distribution for enabled pixels',
                                         suffix='tdac_threshold_distribution',
                                         min_tdac=0, max_tdac=15,
                                         range_tdac=16)
        except Exception:
            self.log.error('Could not create stacked threshold plot!')

    def create_noise_plot(self, logscale=False, scan_parameter_name='Scan parameter', electron_axis=False):
        try:
            title = 'Threshold distribution'
            if self.run_config['scan_id'] in ['scan_threshold']:
                #plot_range = np.arange(0.5, 80.5, 1)  # TODO: Get from scan
                plot_range = None
            # elif self.run_config['scan_id'] == 'fast_threshold_scan':
            #     plot_range = np.array(self.scan_params[:]['vcal_high'] - self.scan_params[:]['vcal_med'], dtype=np.float)
            #     scan_parameter_name = '$\Delta$ DU'
            #     electron_axis = True
            # elif self.run_config['scan_id'] == 'global_threshold_tuning':
            #     plot_range = range(self.run_config['VTH_stop'],
            #                        self.run_config['VTH_start'],
            #                        self.run_config['VTH_step'])
            #     scan_parameter_name = self.run_config['VTH_name']
            #     electron_axis = False
            # elif self.run_config['scan_id'] == 'injection_delay_scan':
            #     scan_parameter_name = 'Finedelay [LSB]'
            #     electron_axis = False
            #     plot_range = range(0, 16)
            #     title = 'Fine delay distribution for enabled pixels'

            mask = np.full((COL_SIZE, ROW_SIZE), False)
            sel = self.Chi2Map[:] > 0.  # Mask not converged fits (chi2 = 0)
            mask[~sel] = True

            data = np.ma.masked_array(self.NoiseMap, mask)
            data_th = data[:,:]

            self._plot_distribution(data_th.T,
                                    plot_range=plot_range,
                                    electron_axis=electron_axis,
                                    x_axis_title=scan_parameter_name,
                                    title="ENC distribution",
                                    log_y=logscale,
                                    print_failed_fits=False,
                                    suffix='enc_distribution')
        except Exception as e:
            self.logger.error('Could not create noise plot! ({0})'.format(e))

    def create_tdac_plot(self, logscale=False, scan_parameter_name='Scan parameter', electron_axis=False):
        try:
            title = 'TRIM distribution'
            if self.run_config['scan_id'] in ['tune_threshold_inj', 'tune_threshold_noise', 'scan_threshold']:
                plot_range = np.arange(0,16,1)
            # elif self.run_config['scan_id'] == 'fast_threshold_scan':
            #     plot_range = np.array(self.scan_params[:]['vcal_high'] - self.scan_params[:]['vcal_med'], dtype=np.float)
            #     scan_parameter_name = '$\Delta$ DU'
            #     electron_axis = True
            # elif self.run_config['scan_id'] == 'global_threshold_tuning':
            #     plot_range = range(self.run_config['VTH_stop'],
            #                        self.run_config['VTH_start'],
            #                        self.run_config['VTH_step'])
            #     scan_parameter_name = self.run_config['VTH_name']
            #     electron_axis = False
            # elif self.run_config['scan_id'] == 'injection_delay_scan':
            #     scan_parameter_name = 'Finedelay [LSB]'
            #     electron_axis = False
            #     plot_range = range(0, 16)
            #     title = 'Fine delay distribution for enabled pixels'

            mask = np.full((COL_SIZE, ROW_SIZE), False)
            cnt=0
            for i in np.ravel(self.Trim[self.Trim[:]== 8]):
                cnt+=1
            #print ("Counts in trim", str(cnt))

            cnt=0
            for i in np.ravel(self.Trim[self.EnPre[:]== 1]):
                cnt+=1
            #print ("Counts in preamp", str(cnt))

            sel = np.logical_and(self.EnPre[:] == 1, self.Trim[:] < 17)  
            mask[~sel] = True
            cnt=0
            for i in np.ravel(mask[mask[:]== False]):
                cnt+=1
            #print ("Counts in mask", str(cnt))


            data = np.ma.masked_array(self.Trim, mask)
            data_tdac = np.ravel(data[sel])
            #print (len(data_tdac))

            self._plot_distribution(data_tdac,
                                    plot_range=plot_range,
                                    electron_axis=electron_axis,
                                    x_axis_title=scan_parameter_name,
                                    title="TDAC distribution",
                                    log_y=logscale,
                                    print_failed_fits=False,
                                    suffix='tdac_distribution',
                                    unit_raw="TRIM"
                                    )
        except Exception as e:
            self.logger.error('Could not create TDAC distribution plot! ({0})'.format(e))

    def create_cluster_size_plot(self):
        try:
            self._plot_cl_size(self.HistClusterSize)
        except Exception:
            self.logger.error('Could not create cluster size plot!')

    def create_cluster_tot_plot(self):
        try:
            self._plot_cl_tot(self.HistClusterTot)
        except Exception:
            self.logger.error('Could not create cluster TOT plot!')

    def create_cluster_shape_plot(self):
        try:
            self._plot_cl_shape(self.HistClusterShape)
        except Exception:
            self.logger.error('Could not create cluster shape plot!')

    def _plot_cl_size(self, hist):
        ''' Create 1D cluster size plot w/wo log y-scale '''
        self._plot_1d_hist(hist=hist, title='Cluster size',
                           log_y=False, plot_range=range(0, 10),
                           x_label='Cluster size',
                           y_label='# of clusters', suffix='cluster_size')
        self._plot_1d_hist(hist=hist, title='Cluster size (log)',
                           log_y=True, plot_range=range(0, 100),
                           x_label='Cluster size',
                           y_label='# of clusters', suffix='cluster_size_log')

    def _plot_cl_tot(self, hist):
        ''' Create 1D cluster size plot w/wo log y-scale '''
        self._plot_1d_hist(hist=hist, title='Cluster ToT',
                           log_y=False, plot_range=range(0, 64),
                           x_label='Cluster ToT [25 ns]',
                           y_label='# of clusters', suffix='cluster_tot')

    def _plot_tot_hist(self, hist):
        ''' Create 1D ToT histrogram '''
        self._plot_1d_hist(hist=hist, title='ToT Distribution',
                           x_label='ToT Values', y_label='# of Hits',
                           plot_range=range(0, 64), suffix='tot_hist')

    def _plot_cl_shape(self, hist):
        ''' Create a histogram with selected cluster shapes '''
        x = np.arange(12)
        fig = Figure()
        _ = FigureCanvas(fig)
        ax = fig.add_subplot(111)

        selected_clusters = hist[[1, 3, 5, 6, 9, 13, 14, 7, 11, 19, 261, 15]]
        ax.bar(x, selected_clusters, align='center')
        ax.xaxis.set_ticks(x)
        fig.subplots_adjust(bottom=0.2)
        ax.set_xticklabels([u"\u2004\u2596",
                            # 2 hit cluster, horizontal
                            u"\u2597\u2009\u2596",
                            # 2 hit cluster, vertical
                            u"\u2004\u2596\n\u2004\u2598",
                            u"\u259e",  # 2 hit cluster
                            u"\u259a",  # 2 hit cluster
                            u"\u2599",  # 3 hit cluster, L
                            u"\u259f",  # 3 hit cluster
                            u"\u259b",  # 3 hit cluster
                            u"\u259c",  # 3 hit cluster
                            # 3 hit cluster, horizontal
                            u"\u2004\u2596\u2596\u2596",
                            # 3 hit cluster, vertical
                            u"\u2004\u2596\n\u2004\u2596\n\u2004\u2596",
                            # 4 hit cluster
                            u"\u2597\u2009\u2596\n\u259d\u2009\u2598"])
        ax.set_title('Cluster shapes', color=TITLE_COLOR)
        ax.set_xlabel('Cluster shape')
        ax.set_ylabel('# of clusters')
        ax.grid(True)
        ax.set_yscale('log')
        ax.set_ylim(ymin=1e-1)

        self._save_plots(fig, suffix='cluster_shape')

    def _plot_1d_hist(self, hist, yerr=None, plot_range=None, x_label=None, y_label=None, title=None, x_ticks=None, color='C0', log_y=False, suffix=None):
        fig = Figure()
        FigureCanvas(fig)
        ax = fig.add_subplot(111)

        hist = np.array(hist)
        if plot_range is None:
            plot_range = range(0, len(hist))
        plot_range = np.array(plot_range)
        plot_range = plot_range[plot_range < len(hist)]
        if yerr is not None:
            ax.bar(x=plot_range, height=hist[plot_range],
                   color=color, align='center', yerr=yerr)
        else:
            ax.bar(x=plot_range,
                   height=hist[plot_range], color=color, align='center')
        ax.set_xlim((min(plot_range) - 0.5, max(plot_range) + 0.5))

        ax.set_title(title, color=TITLE_COLOR)
        if x_label is not None:
            ax.set_xlabel(x_label)
        if y_label is not None:
            ax.set_ylabel(y_label)
        if x_ticks is not None:
            ax.set_xticks(plot_range)
            ax.set_xticklabels(x_ticks)
            ax.tick_params(which='both', labelsize=8)
        if np.allclose(hist, 0.0):
            ax.set_ylim((0, 1))
        else:
            if log_y:
                ax.set_yscale('log')
                ax.set_ylim((1e-1, np.amax(hist) * 2))
        ax.grid(True)

        self._save_plots(fig, suffix=suffix)

    def _plot_distribution(self, data, plot_range=None, x_axis_title=None, electron_axis=False, use_electron_offset=False, y_axis_title='N. of hits', 
                        log_y=False, align='edge', title=None, print_failed_fits=False, suffix=None, unit_raw="V", unit_cal="e^-"):
        if plot_range is None:
            diff = np.amax(data) - np.amin(data)
            #if (np.amax(data)) > np.median(data) * 5:
            #    plot_range = np.arange(np.amin(data), np.median(data) * 2, np.median(data) / 100.)
            #else:
            plot_range = np.arange(np.amin(data)- diff / 10., np.amax(data) + diff / 10., diff / 100.)

        diff = np.amax(data) - np.amin(data)
        tick_size = np.diff(plot_range)[0]

        #hist, bins = np.histogram(np.ravel(data), bins=plot_range)
        #total_counts = len(np.ravel(data))

        hist, bins = np.histogram(data, bins=plot_range)
        total_counts = len(data)

        bin_centers = (bins[:-1] + bins[1:]) / 2
        p0 = (np.amax(hist), np.nanmean(bins),
              (max(plot_range) - min(plot_range)) / 3)

        try:
            coeff, _ = curve_fit(self._gauss, bin_centers, hist, p0=p0)
        except Exception as e:
            coeff = None
            self.logger.warning('Gauss fit failed!')
            self.logger.error(e)

        if coeff is not None:
            points = np.linspace(min(plot_range), max(plot_range), 500)
            gau = self._gauss(points, *coeff)

        fig = Figure()
        FigureCanvas(fig)
        ax = fig.add_subplot(111)

        ax.step(bin_centers, hist, color='C0', where='mid', linewidth=1)

        if coeff is not None:
            ax.plot(points, gau, "r-", label='Normal distribution')

        if log_y:
            if title is not None:
                title += ' (logscale)'
            ax.set_yscale('log')

        ax.set_xlim(min(plot_range-(diff/4)), max(plot_range+(diff/4)))
        ax.set_title(title, color=TITLE_COLOR, pad=40)
        if x_axis_title is not None:
            ax.set_xlabel(x_axis_title)
        if y_axis_title is not None:
            ax.set_ylabel(y_axis_title)
        ax.grid(True)

        if not self.qualitative:
            mean = np.nanmean(data)
            rms = np.nanstd(data)
            if np.nanmean(data) < 10:
                if electron_axis:
                    textright = '$\mu={0:1.3f}\;{1:s}$\n$\;\;\;\;\;\;({2:d} \; {3:s})$\n\n$\sigma={4:1.3f}\;{5:s}$\n$\;\;\;\;\;\;({6:d} \; {7:s})$'.format(
                        mean, 
                        unit_raw,
                        int(self._convert_to_e(mean, use_offset=use_electron_offset)[0]), 
                        unit_cal,
                        rms, 
                        unit_raw,
                        int(self._convert_to_e(rms, use_offset=False)[0]),
                        unit_cal)
                else:
                    textright = '$\mu={0:1.3f}\;{1:s}$\n$\sigma={2:1.3f}\;{3:s}$'.format(
                        mean, 
                        unit_raw,
                        rms,
                        unit_raw)
            else:
                if electron_axis:
                    textright = '$\mu={0:1.3f}\;{1:s}$\n$\;\;\;\;\;\;({2:d} \; {3:s})$\n\n$\sigma={4:1.3f}\;{5:s}$\n$\;\;\;\;\;\;({6:d} \; {7:s})$'.format(
                        mean, 
                        unit_raw,
                        int(self._convert_to_e(mean, use_offset=use_electron_offset)[0]), 
                        unit_cal,
                        rms, 
                        unit_raw,
                        int(self._convert_to_e(rms, use_offset=False)[0]),
                        unit_cal)
                else:
                    textright = '$\mu={0:1.3f}\;{1:s}$\n$\sigma={2:1.3f}\;{3:s}$'.format(
                        mean, 
                        unit_raw,
                        rms,
                        unit_raw)

            # Fit results
            if coeff is not None:
                textright += '\n\nFit results:\n'
                if coeff[1] < 10:
                    if electron_axis:
                        textright += '$\mu={0:1.3f}\;{1:s}$\n$\;\;\;\;\;\;({2:d} \; {3:s})$\n\n$\sigma={4:1.3f}\;{5:s}$\n$\;\;\;\;\;\;({6:d} \; {7:s})$'.format(
                            abs(coeff[1]), 
                            unit_raw,
                            int(self._convert_to_e(abs(coeff[1]), use_offset=use_electron_offset)[0]), 
                            unit_cal,
                            abs(coeff[2]), 
                            unit_raw,
                            int(self._convert_to_e(abs(coeff[2]), use_offset=False)[0]),
                            unit_cal)
                    else:
                        textright += '$\mu={0:1.3f}\;{1:s}$\n$\sigma={2:1.3f}\;{3:s}$'.format(
                            abs(coeff[1]),
                            unit_raw, 
                            abs(coeff[2]),
                            unit_raw)
                else:
                    if electron_axis:
                        textright += '$\mu={0:1.3f}\;{1:s}$\n$\;\;\;\;\;\;({2:d} \; {3:s})$\n\n$\sigma={4:1.3f}\;{5:s}$\n$\;\;\;\;\;\;({6:d} \; {7:s})$'.format(
                            abs(coeff[1]), 
                            unit_raw,
                            int(self._convert_to_e(abs(coeff[1]), use_offset=use_electron_offset)[0]), 
                            unit_cal,
                            abs(coeff[2]), 
                            unit_raw,
                            int(self._convert_to_e(abs(coeff[2]), use_offset=False)[0]),
                            unit_cal)
                    else:
                        textright += '$\mu={0:1.3f}\;{1:s}$\n$\sigma={2:1.3f}\;{3:s}$'.format(
                            abs(coeff[1]), 
                            unit_raw,
                            abs(coeff[2]),
                            unit_raw)
                if print_failed_fits:
                    textright += '\n\nFailed fits: {0}'.format(self.n_failed_scurves)

            textright += '\n\nTotal counts:\n{0}'.format(total_counts)

            props = dict(boxstyle='round', facecolor='gray', alpha=0.3)
            ax.text(0.80, 0.96, textright, transform=ax.transAxes, fontsize=8, verticalalignment='top', bbox=props)

        if electron_axis:
            self._add_electron_axis(fig, ax, use_electron_offset=use_electron_offset)

        if self.qualitative:
            ax.xaxis.set_major_formatter(matplotlib.pyplot.NullFormatter())
            ax.xaxis.set_minor_formatter(matplotlib.pyplot.NullFormatter())
            ax.yaxis.set_major_formatter(matplotlib.pyplot.NullFormatter())
            ax.yaxis.set_minor_formatter(matplotlib.pyplot.NullFormatter())

        self._save_plots(fig, suffix=suffix, tight=True)


    def _plot_histogram2d(self, hist, z_min=None, z_max=None, suffix=None, xlabel='', ylabel='', title='', z_label='N. of hits'):
        x_bins = np.arange(-0.5, hist.shape[0] - 0.5)
        y_bins = np.arange(-0.5, hist.shape[1] - 0.5)

        if z_max == 'median':
            z_max = 2.0 * np.ma.median(hist[hist>0])
        elif z_max == 'maximum':
            z_max = np.ma.max(hist)
        elif z_max is None:
            z_max = np.percentile(hist, q=90)
            if np.any(hist > z_max):
                z_max = 1.1 * z_max
        if hist.all() is np.ma.masked:
            z_max = 1.0

        if z_min is None:
            z_min = np.ma.min(hist)
        if z_min == z_max or hist.all() is np.ma.masked:
            z_min = 0

        fig = Figure()
        FigureCanvas(fig)
        ax = fig.add_subplot(111)

        fig.patch.set_facecolor('white')
        cmap = cm.get_cmap('cool')
        if np.allclose(hist, 0.0) or hist.max() <= 1:
            z_max = 1.0
        else:
            z_max = hist.max()
        # for small z use linear scale, otherwise log scale
        if z_max <= 10.0:
            bounds = np.linspace(start=0.0, stop=z_max, num=255, endpoint=True)
            norm = colors.BoundaryNorm(bounds, cmap.N)
        else:
            bounds = np.linspace(start=1.0, stop=z_max, num=255, endpoint=True)
            norm = colors.LogNorm()

        im = ax.pcolormesh(x_bins, y_bins, hist.T, norm=norm, rasterized=True)
        ax.set_title(title, color=TITLE_COLOR)
        ax.set_xlabel(xlabel)
        ax.set_ylabel(ylabel)

        if z_max <= 10.0:
            cb = fig.colorbar(im, ticks=np.linspace(start=0.0, stop=z_max, num=min(
                11, math.ceil(z_max) + 1), endpoint=True), fraction=0.04, pad=0.05,format=matplotlib.ticker.FormatStrFormatter('%.3f'))
        else:
            cb = fig.colorbar(im, fraction=0.04, pad=0.05, format=matplotlib.ticker.FormatStrFormatter('%.3f') )
        cb.set_label(z_label)

        self._save_plots(fig, suffix=suffix)

    def _plot_occupancy(self, hist, 
                        electron_axis=False, 
                        title='Occupancy', z_label='N. of Hits', 
                        z_min=None, z_max=None, 
                        show_sum=True, suffix=None,
                        scale_mode=None):

        if z_max == 'median':
            z_max = 2.0 * np.ma.median(hist[hist>0])
        elif z_max == 'maximum':
            z_max = np.ma.max(hist)
        elif z_max is None:
            z_max = np.percentile(hist, q=90)
            if np.any(hist > z_max):
                z_max = 1.1 * z_max
        if hist.all() is np.ma.masked:
            z_max = 1.0

        if z_min is None:
            z_min = np.ma.min(hist)
        if z_min == z_max or hist.all() is np.ma.masked:
            z_min = 0

        fig = Figure()
        FigureCanvas(fig)
        ax = fig.add_subplot(111)
        ax.set_adjustable('box')

        if scale_mode == 'binary':
            bounds = np.linspace(start=z_min, stop=z_max, num=3, endpoint=True)
        elif scale_mode == 'integer':
            bounds = np.linspace(start=z_min, stop=z_max, num=255, endpoint=True)
        else:  
            bounds = np.linspace(start=z_min, stop=z_max, num=255, endpoint=True)
        
        cmap = copy.copy(cm.get_cmap('viridis'))
        cmap.set_bad('k')
        cmap.set_under('w')
        norm = colors.BoundaryNorm(bounds, cmap.N)

        im = ax.imshow(hist, interpolation='none', 
                        aspect="auto", cmap=cmap,
                        norm=norm) 

        ax.set_ylim((-0.5, ROW_SIZE-0.5))
        ax.set_xlim((-0.5, COL_SIZE-0.5))
        ax.set_title(title + r' ($\Sigma$ = {0:.4f})'.format(
            (0 if hist.all() is np.ma.masked else np.ma.sum(hist))), color=TITLE_COLOR)
        ax.set_xlabel('Column')
        ax.set_ylabel('Row')

        divider = make_axes_locatable(ax)
        if electron_axis:
            pad = 0.8
        else:
            pad = 0.4
        cax = divider.append_axes("right", size="5%", pad=pad)

        if scale_mode == 'binary':
            ticks=np.linspace(start=z_min, stop=z_max, num=2, endpoint=True)
            cb = fig.colorbar(im, cax=cax, ticks=ticks, orientation='vertical', format=matplotlib.ticker.FormatStrFormatter('%d'))
        elif scale_mode == 'integer':
            ticks=np.linspace(start=z_min, stop=z_max, num=10, endpoint=True)
            cb = fig.colorbar(im, cax=cax, ticks=ticks, orientation='vertical', format=matplotlib.ticker.FormatStrFormatter('%d'))
        else:
            ticks=np.linspace(start=z_min, stop=z_max, num=10, endpoint=True)
            cb = fig.colorbar(im, cax=cax, ticks=ticks, orientation='vertical', format=matplotlib.ticker.FormatStrFormatter('%.3f'))

        cax.set_xticklabels([int(round(float(x.get_text())))
                             for x in cax.xaxis.get_majorticklabels()])
        
        cb.set_label('{0} [V]'.format(z_label))

        if electron_axis:
        
            def f(x):
                return np.array([self._convert_to_e(x, use_offset=True)[0] for x in x])

            if self.cb_side:
                ax2 = cb.ax.secondary_yaxis('left', functions=(lambda x: x, lambda x: x))
                e_ax = ax2.yaxis
            else:
                ax2 = cb.ax.secondary_xaxis('top', functions=(lambda x: x, lambda x: x))
                e_ax = ax2.xaxis
            e_ax.set_ticks(ticks)
            e_ax.set_ticklabels(f(ticks).round().astype(int))
            e_ax.set_label_text('{0} [e-]'.format(z_label))


        self._save_plots(fig, suffix=suffix, tight=True)

    def _plot_fancy_occupancy(self, hist, title='Occupancy', z_label='#', z_min=None, z_max=None, log_z=True, norm_projection=False, show_sum=True, suffix='fancy_occupancy'):
        if log_z:
            title += '\n(logarithmic scale)'
        title += '\nwith projections'

        if z_min is None:
            z_min = np.ma.min(hist)
        if log_z and z_min == 0:
            z_min = 0.1
        if z_max is None:
            z_max = np.ma.max(hist)

        fig = Figure()
        FigureCanvas(fig)
        ax = fig.add_subplot(111)

        self.plot_box_bounds = [0.5, COL_SIZE + 0.5, ROW_SIZE + 0.5, 0.5]
        extent = self.plot_box_bounds
        if log_z:
            bounds = np.logspace(start=np.log10(z_min), stop=np.log10(z_max), num=255, endpoint=True)
        else:
            bounds = np.linspace(start=z_min, stop=z_max, num=int((z_max - z_min) + 1), endpoint=True)
        cmap = copy.copy(cm.get_cmap('viridis'))
        cmap.set_bad('w')
        norm = colors.BoundaryNorm(bounds, cmap.N)

        im = ax.imshow(hist, interpolation='none', aspect='auto', cmap=cmap, norm=norm, extent=extent)  # TODO: use pcolor or pcolormesh
        ax.set_ylim((self.plot_box_bounds[2], self.plot_box_bounds[3]))
        ax.set_xlim((self.plot_box_bounds[0], self.plot_box_bounds[1]))
        ax.set_xlabel('Column')
        ax.set_ylabel('Row')

        # create new axes on the right and on the top of the current axes
        # The first argument of the new_vertical(new_horizontal) method is
        # the height (width) of the axes to be created in inches.
        divider = make_axes_locatable(ax)
        axHistx = divider.append_axes("top", 1.2, pad=0.2, sharex=ax)
        axHisty = divider.append_axes("right", 1.2, pad=0.2, sharey=ax)

        cax = divider.append_axes("right", size="5%", pad=0.1)
        if log_z:
            cb = fig.colorbar(im, cax=cax, ticks=np.logspace(start=np.log10(z_min), stop=np.log10(z_max), num=9, endpoint=True))
        else:
            cb = fig.colorbar(im, cax=cax, ticks=np.linspace(start=z_min, stop=z_max, num=int((z_max - z_min) + 1), endpoint=True))
        cb.set_label(z_label)
        # make some labels invisible
        setp(axHistx.get_xticklabels() + axHisty.get_yticklabels(), visible=False)
        if norm_projection:
            hight = np.ma.mean(hist, axis=0)
        else:
            hight = np.ma.sum(hist, axis=0)

        axHistx.bar(x=range(1, hist.shape[1] + 1), height=hight, align='center', linewidth=0)
        axHistx.set_xlim((self.plot_box_bounds[0], self.plot_box_bounds[1]))
        if hist.all() is np.ma.masked:
            axHistx.set_ylim((0, 1))
        axHistx.locator_params(axis='y', nbins=3)
        axHistx.ticklabel_format(style='sci', scilimits=(0, 4), axis='y')
        axHistx.set_ylabel(z_label)
        if norm_projection:
            width = np.ma.mean(hist, axis=1)
        else:
            width = np.ma.sum(hist, axis=1)

        axHisty.barh(y=range(1, hist.shape[0] + 1), width=width, align='center', linewidth=0)
        axHisty.set_ylim((self.plot_box_bounds[2], self.plot_box_bounds[3]))
        if hist.all() is np.ma.masked:
            axHisty.set_xlim((0, 1))
        axHisty.locator_params(axis='x', nbins=3)
        axHisty.ticklabel_format(style='sci', scilimits=(0, 4), axis='x')
        axHisty.set_xlabel(z_label)

        if not show_sum:
            ax.set_title(title, color=TITLE_COLOR, x=1.35, y=1.2)
        else:
            ax.set_title(title + '\n($\\Sigma$ = {0})'.format((0 if hist.all() is np.ma.masked else np.ma.sum(hist))), color=TITLE_COLOR, x=1.35, y=1.2)

        self._save_plots(fig, suffix=suffix)

    def _plot_2d_pixelmasks(self, hist, 
                        page_title="Pixel Masks", 
                        title=["EnPre","EnInj","EnMon","TRIM (TDAC)"], 
                        z_min=[0,0,0,0], z_max=[1,1,1,15]
                        ):
        fig = Figure()
        FigureCanvas(fig)
        for i in range(4):
            ax = fig.add_subplot(221+i)
            
            cmap = cm.get_cmap('plasma')
            cmap.set_bad('w')
            cmap.set_over('r')  # Make noisy pixels red

            im=ax.imshow(np.transpose(hist[i]),origin='lower',aspect="auto",
                     vmax=z_max[i]+1,vmin=z_min[i], interpolation='none',
                     cmap=cmap #, norm=norm
                     )
            ax.set_title(title[i])
            ax.set_ylim((-0.5, ROW_SIZE-0.5))
            ax.set_xlim((-0.5, COL_SIZE-0.5))

            ax.set_xlabel('Column')
            ax.set_ylabel('Row')

            divider = make_axes_locatable(ax)
            cax = divider.append_axes("right", size="5%", pad=0.1)
            cb = fig.colorbar(im, cax=cax)
            cb.set_label(title[i])
        if page_title is not None and len(page_title)>0:
            fig.suptitle(page_title, fontsize=12,color=OVERTEXT_COLOR, y=1.05)
        self._save_plots(fig)

    def _plot_scurves(self, scurves, scan_parameters, electron_axis=False, max_occ=None, scan_parameter_name=None, title='S-curves', ylabel='Occupancy'):
        # TODO: get n_pixels and start and stop columns from run_config
        # start_column = self.run_config['start_column']
        # stop_column = self.run_config['stop_column']
        # start_row = self.run_config['start_row']
        # stop_row = self.run_config['stop_row']
        #x_bins = np.arange(-0.5, max(scan_parameters) + 1.5, scan_parameters[1]-scan_parameters[0])
        x_step=scan_parameters[1]-scan_parameters[0]
        x_bins = np.arange(min(scan_parameters)-0.5*x_step, max(scan_parameters) + 0.5*x_step, x_step)
        if max_occ is None:
            max_occ=int(np.max(scurves))
        y_max=int(max_occ*1.10)
        y_bins = np.arange(-0.5, y_max + 0.5)

        param_count = scurves.shape[2]
        hist = np.empty([param_count, y_max], dtype=np.uint32)

        # Reformat scurves array as one long list of scurves
        # For very noisy or not properly masked devices, ignore all s-curves where any data
        # is larger than given threshold (max_occ)
        scurves = scurves.reshape((scurves.shape[0] * scurves.shape[1], scurves.shape[2]))

        scurves_masked = scurves[~np.any(scurves >= y_max, axis=1)]
        n_pixel = scurves_masked.shape[0]

        for param in range(param_count):
            hist[param] = np.bincount(scurves_masked[:, param], minlength=y_max)[:y_max]

        fig = Figure()
        FigureCanvas(fig)
        ax = fig.add_subplot(111)

        fig.patch.set_facecolor('white')
        cmap = cm.get_cmap('cool')
        if np.allclose(hist, 0.0) or hist.max() <= 1:
            z_max = 1.0
        else:
            z_max = hist.max()
        # for small z use linear scale, otherwise log scale
        if z_max <= 10.0:
            bounds = np.linspace(start=0.0, stop=z_max, num=255, endpoint=True)
            norm = colors.BoundaryNorm(bounds, cmap.N)
        else:
            bounds = np.linspace(start=1.0, stop=z_max, num=255, endpoint=True)
            norm = colors.LogNorm()

        im = ax.pcolormesh(x_bins, y_bins, hist.T, norm=norm, rasterized=True, shading='auto')

        if z_max <= 10.0:
            cb = fig.colorbar(im, ticks=np.linspace(start=0.0, stop=z_max, num=min(
                11, math.ceil(z_max) + 1), endpoint=True), fraction=0.04, pad=0.05)
        else:
            cb = fig.colorbar(im, fraction=0.04, pad=0.05 )

        cb.set_label("N. of pixels")
        ax.set_title(title + ' for %d pixel(s)' % (n_pixel), color=TITLE_COLOR)
        if scan_parameter_name is None:
            ax.set_xlabel('Scan parameter')
        else:
            ax.set_xlabel(scan_parameter_name)
        ax.set_ylabel(ylabel)

        if electron_axis:
            self._add_electron_axis(fig, ax)

        self._save_plots(fig, suffix='scurves')

    def _plot_stacked_threshold(self, data, tdac_mask, plot_range=None, electron_axis=False, x_axis_title=None, y_axis_title='# of hits', z_axis_title='TDAC',
                                title=None, suffix=None, min_tdac=15, max_tdac=0, range_tdac=16,
                                fit_gauss=True, plot_legend=True, centered_ticks=False):

        if plot_range is None:
            diff = np.amax(data) - np.amin(data)
            if (np.amax(data)) > np.median(data) * 5:
                plot_range = np.arange(
                    np.amin(data), np.median(data) * 5, diff / 100.)
            else:
                plot_range = np.arange(np.amin(data), np.amax(data) + diff / 100., diff / 100.)

        tick_size = plot_range[1] - plot_range[0]

        hist, bins = np.histogram(np.ravel(data), bins=plot_range)

        bin_centres = (bins[:-1] + bins[1:]) / 2
        p0 = (np.amax(hist), np.nanmean(bins), (max(plot_range) - min(plot_range)) / 3)

        if fit_gauss:
            try:
                coeff, _ = curve_fit(self._gauss, bin_centres, hist, p0=p0)
            except Exception:
                coeff = None
                self.log.warning('Gauss fit failed!')
        else:
            coeff = None

        if coeff is not None:
            points = np.linspace(min(plot_range), max(plot_range), 500)
            gau = self._gauss(points, *coeff)

        fig = Figure()
        FigureCanvas(fig)
        ax = fig.add_subplot(111)

        cmap = copy.copy(cm.get_cmap('viridis', (range_tdac)))
        # create dicts for tdac data
        data_thres_tdac = {}
        hist_tdac = {}
        tdac_bar = {}

        # select threshold data for different tdac values according to tdac map
        for tdac in range(range_tdac):
            data_thres_tdac[tdac] = data[tdac_mask == tdac - abs(min_tdac)]
            # histogram threshold data for each tdac
            hist_tdac[tdac], _ = np.histogram(np.ravel(data_thres_tdac[tdac]), bins=bins)

            if tdac == 0:
                tdac_bar[tdac] = ax.bar(bins[:-1], hist_tdac[tdac], width=tick_size, align='edge', color=cmap(.9 / range_tdac * tdac), linewidth=0)
            elif tdac == 1:
                tdac_bar[tdac] = ax.bar(bins[:-1], hist_tdac[tdac], bottom=hist_tdac[0], width=tick_size, align='edge', color=cmap(1. / range_tdac * tdac), linewidth=0)
            else:
                tdac_bar[tdac] = ax.bar(bins[:-1], hist_tdac[tdac], bottom=np.sum([hist_tdac[i] for i in range(tdac)], axis=0), width=tick_size, align='edge', color=cmap(1. / range_tdac * tdac), linewidth=0)

        fig.subplots_adjust(right=0.85)
        cax = fig.add_axes([0.89, 0.11, 0.02, 0.645])
        if centered_ticks:
            ctick_size = (max_tdac - min_tdac) / (range_tdac - 1)
            sm = plt.cm.ScalarMappable(cmap=cmap, norm=colors.Normalize(vmin=min_tdac - ctick_size / 2, vmax=max_tdac + ctick_size / 2))
        else:
            sm = plt.cm.ScalarMappable(cmap=cmap, norm=colors.Normalize(vmin=min_tdac, vmax=max_tdac))
        sm.set_array([])
        cb = fig.colorbar(sm, cax=cax, ticks=np.linspace(start=min_tdac, stop=max_tdac, num=range_tdac, endpoint=True))
        cb.set_label(z_axis_title)

        if coeff is not None:
            ax.plot(points, gau, "r-", label='Normal distribution')

        ax.set_xlim((min(plot_range), max(plot_range)))
        ax.set_title(title, color=TITLE_COLOR)
        if x_axis_title is not None:
            ax.set_xlabel(x_axis_title)
        if y_axis_title is not None:
            ax.set_ylabel(y_axis_title)
        ax.grid(True)

        if plot_legend:
            sel = (data < 1e5)
            mean = np.nanmean(data[sel])
            rms = np.nanstd(data[sel])
            if electron_axis:
                textright = '$\\mu={0:1.3f}\\;$V\n$\\;\\;\\,=({1[0]:1.0f} \\pm {1[1]:1.0f}) \\; e^-$\n\n$\\sigma={2:1.3f}\\;$V\n$\\;\\;\\,=({3[0]:1.0f} \\pm {3[1]:1.0f}) \\; e^-$'.format(mean, self._convert_to_e(mean), rms, self._convert_to_e(rms, use_offset=False))
            else:
                textright = '$\\mu={0:1.3f}\\;$V\n$\\sigma={1:1.3f}\\;$V'.format(mean, rms)

            # Fit results
            if coeff is not None:
                textright += '\n\nFit results:\n'
                if electron_axis:
                    textright += '$\\mu={0:1.3f}\\;$V\n$\\;\\;\\,=({1[0]:1.0f} \\pm {1[1]:1.0f}) \\; e^-$\n\n$\\sigma={2:1.3f}\\;$V\n$\\;\\;\\,=({3[0]:1.0f} \\pm {3[1]:1.0f}) \\; e^-$'.format(abs(coeff[1]), self._convert_to_e(abs(coeff[1])), abs(coeff[2]), self._convert_to_e(abs(coeff[2]), use_offset=False))
                else:
                    textright += '$\\mu={0:1.3f}\\;$V\n$\\sigma={1:1.3f}\\;$V'.format(abs(coeff[1]), abs(coeff[2]))

                props = dict(boxstyle='round', facecolor='wheat', alpha=0.5)
                ax.text(0.745, 0.95, textright, transform=ax.transAxes, fontsize=8, verticalalignment='top', bbox=props)

        if electron_axis:
            self._add_electron_axis(fig, ax)

        self._save_plots(fig, suffix=suffix)

    def _plot_single_scurves(self, scurves, scan_parameters, electron_axis=False, max_occ=None, scan_parameter_name=None, title='S-curves', ylabel='Hits'):
        
        x_step=scan_parameters[1]-scan_parameters[0]
        if max_occ is None:
            max_occ=int(np.max(scurves))
        y_max=int(max_occ*1.10)

        param_count = scurves.shape[2]

        # Reformat scurves array as one long list of scurves
        # For very noisy or not properly masked devices, ignore all s-curves where any data
        # is larger than given threshold (max_occ)
        for p_i,p in enumerate(np.argwhere(self.EnPre)):
            fig = Figure()
            FigureCanvas(fig)
            ax = fig.add_subplot(111)

            if scan_parameter_name is None:
                ax.set_xlabel('Scan parameter')
            else:
                ax.set_xlabel(scan_parameter_name)
            ax.set_ylabel(ylabel)
            
            ax.set_title("Pixel [%d,%d], Mean=%.3f, Sigma=%.3f"%(p[0],p[1], self.ThresholdMap[p[0],p[1]], self.NoiseMap[p[0],p[1]]), color=TITLE_COLOR)
            
            ax.plot(scan_parameters, scurves[p[0],p[1]], "o")

            if electron_axis:
                self._add_electron_axis(fig, ax)

            self._save_plots(fig, suffix='scurves') 

    def table_values(self,dat,n_row=30,n_col=3,
                        title="Chip configuration"):
        keys=dat.keys()
        cellText=[["" for i in range(n_col*2)] for j in range(n_row)]
        for i,k in enumerate(keys):
            str_k_val = ""
            if isinstance(dat[k], float):
                str_k_val="{:.4f}".format(dat[k])
            elif isinstance(dat[k], str):
                # If the parameter value is a string, check if it is binary and convert it to int.
                binary_set = {'0','1'}
                string_set = set(dat[k])    
                if binary_set == string_set or string_set == {'0'} or string_set == {'1'}:
                    str_k_val=int(dat[k],2)
                else:
                    str_k_val=dat[k]
            else:
                str_k_val=int(dat[k])
            cellText[i%n_row][int(i/n_row)*2]=k
            cellText[i%n_row][(int(i/n_row)*2)+1]=str_k_val
        colLabels=[]
        colWidths=[]
        for i in range(n_col):
            colLabels.append("Parameter")
            colWidths.append(0.2) ## width for param name
            colLabels.append("Value")
            colWidths.append(0.15) ## width for value
        fig = Figure()
        FigureCanvas(fig)
        ax = fig.add_subplot(111)
        fig.patch.set_visible(False)
        ax.set_adjustable('box')
        ax.axis('off')
        ax.axis('tight')

        tab=ax.table(cellText=cellText,
                colLabels=colLabels,
                colWidths = colWidths,
                loc='upper center')
        tab.auto_set_font_size(False)
        tab.set_fontsize(4)
        for key, cell in tab.get_celld().items():
            cell.set_linewidth(0.1)
        if title is not None and len(title)>0:
            ax.set_title(title, color=TITLE_COLOR)
        tab.scale(1,0.7)
        self._save_plots(fig, suffix='values')

    def _save_plots(self, fig, suffix=None, tight=False):
        increase_count = False
        bbox_inches = 'tight' if tight else ''
        if suffix is None:
            suffix = str(self.plot_cnt)
        if not self.out_file:
            fig.show()
        else:
            self.out_file.savefig(fig, bbox_inches=bbox_inches)
        if self.save_png:
            fig.savefig(self.filename[:-4] + '_' + suffix + '.png', bbox_inches=bbox_inches)
            increase_count = True
        if self.save_single_pdf:
            fig.savefig(self.filename[:-4] + '_' + suffix + '.pdf', bbox_inches=bbox_inches)
            increase_count = True
        if increase_count:
            self.plot_cnt += 1

    def _convert_to_e(self, dac, use_offset=False):
        if use_offset:
            e = dac * self.calibration['e_conversion_slope'] + self.calibration['e_conversion_offset']
            de = math.sqrt((dac * self.calibration['e_conversion_slope_error'])**2 + self.calibration['e_conversion_offset_error']**2)
        else:
            e = dac * self.calibration['e_conversion_slope']
            de = dac * self.calibration['e_conversion_slope_error']
        return e, de

    def _add_electron_axis(self, fig, ax, use_electron_offset=True):
        fig.subplots_adjust(top=0.75)
        ax.title.set_position([.5, 1.15])

        fig.canvas.draw()
        ax2 = ax.twiny()

        xticks = []
        for t in ax.get_xticks(minor=False):
            xticks.append(int(self._convert_to_e(float(t), use_offset=use_electron_offset)[0]))

        l1 = ax.get_xlim()
        l2 = ax2.get_xlim()

        def f(x):
            return l2[0] + (x - l1[0]) / (l1[1] - l1[0]) * (l2[1] - l2[0])

        ticks = f(ax.get_xticks())
        ax2.xaxis.set_major_locator(matplotlib.ticker.FixedLocator(ticks))
        ax2.set_xticklabels(xticks)
        ax2.set_xlabel('Charge [e-]', labelpad=7)
        return ax2

    def _gauss(self, x, *p):
        amplitude, mu, sigma = p
        return amplitude * np.exp(- (x - mu)**2.0 / (2.0 * sigma**2.0))

    def _double_gauss(self, x, a1, a2, m1, m2, sd1, sd2):
        return self._gauss(x, a1, m1, sd1) + self._gauss(x, a2, m2, sd2)

    def _lin(self, x, *p):
        m, b = p
        return m * x + b
