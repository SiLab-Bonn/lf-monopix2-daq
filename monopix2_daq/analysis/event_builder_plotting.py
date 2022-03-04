import numpy as np
import analysis_utils as mono_utils
from matplotlib import colors
from matplotlib.backends.backend_pdf import PdfPages
import matplotlib.pyplot as plt

class event_Builder_Plotting(object):
    def __init__(self, fout, cal_factor=1, save_png=False, save_single_pdf=False):

        self.fout=fout
        self.cal_factor=cal_factor
        self.save_png = save_png
        self.save_single_pdf = save_single_pdf
        
        # Initialize a counter to keep track of the number of plots created 
        self.PLOT_N_COUNTER=0

        #self.calibration = {'e_conversion_slope': cal_factor, 'e_conversion_offset': 0, 'e_conversion_slope_error': 0, 'e_conversion_offset_error': 0}
        self.pdf_filename = '.'.join(fout.split('.')[:-1]) + '.pdf'
        self.out_pdf_file = PdfPages(self.pdf_filename)

    def _close_pdf(self):
        if self.out_pdf_file is not None and isinstance(self.out_pdf_file, PdfPages):
            #self.logger.info('Closing output PDF file: %s',
            #                 str(self.out_pdf_file._file.fh.name))
            print('Closing output PDF file: %s',
                             str(self.out_pdf_file._file.fh.name))
            self.out_pdf_file.close()

    def _save_plots(self, fig, plot_n_counter, suffix=None, tight=False, save_png=False, save_single_pdf=False):
        increase_count = False
        bbox_inches = 'tight' if tight else ''
        if suffix is None:
            suffix = str(plot_n_counter)
        if not self.out_pdf_file:
            pass
        else:
            self.out_pdf_file.savefig(fig, bbox_inches=bbox_inches, dpi=600)
        if save_png:
            fig.savefig(self.out_pdf_file._file.fh.name[:-4] + '_' + suffix + '.png', bbox_inches=bbox_inches, dpi=600)
            increase_count = True
        if save_single_pdf:
            fig.savefig(self.out_pdf_file._file.fh.name[:-4] + '_' + suffix + '.pdf', bbox_inches=bbox_inches, dpi=600)
            increase_count = True
        if increase_count:
            plot_n_counter += 1                                                                     

    def plot_TLUvsRX1(self, hist, boxfit_params, diff_offset, lower_lim, upper_lim):        
        """
        Plots the raw difference between the TLU_HR/640 and LE timestamps, fit for the largest peak and cuts performed to filter mismatched data
        """
        x=hist[1][:-1]
        y=hist[0]
        width=boxfit_params[2]
        sigma=boxfit_params[3]
        
        plt.clf()
        fig = plt.figure()
        plt.step(x, y)
        plt.plot(hist[1][:-1], mono_utils.boxfc(hist[1][:-1], *boxfit_params), label="Amp=%.2E\nMean=%.2E\nWidth=%.2f\nSigma_Box=%.2f"%(boxfit_params[0],boxfit_params[1],boxfit_params[2],boxfit_params[3]))

        plt.title("TLU-Scintillator(RX1) [640MHz]")
        plt.xlabel("TLU-RX1 [640MHz Clk]")
        plt.ylabel("Events")
        plt.axvline(diff_offset-np.abs(sigma), color='g', linestyle='--', label='In-time')
        plt.axvline(diff_offset+np.abs(width)+np.abs(sigma), color='g', linestyle='--')
        plt.axvline(lower_lim, color='r', linestyle='--', label='TLU cut')
        plt.axvline(upper_lim, color='r', linestyle='--')
        plt.yscale("log")
        plt.legend(loc=1)
        plt.ylim(bottom=1E0)

        self._save_plots(fig, self.PLOT_N_COUNTER, suffix="TLU-Rx1_HR_full_range", tight=False, save_png=self.save_png, save_single_pdf=self.save_single_pdf)
        plt.xlim(lower_lim-1000,upper_lim+1000)
        self._save_plots(fig, self.PLOT_N_COUNTER, suffix="TLU-Rx1_HR_medium_range", tight=False, save_png=self.save_png, save_single_pdf=self.save_single_pdf)
        plt.xlim(lower_lim-50,upper_lim+50)
        self._save_plots(fig, self.PLOT_N_COUNTER, suffix="TLU-Rx1_HR_short_range", tight=False, save_png=self.save_png, save_single_pdf=self.save_single_pdf)

    def plot_correlation(self, corr_str_orientation, corr_dut, corr_ref, dim_str_dut, dim_str_ref, dim_size_dut,  dim_size_ref):
        """
        Plots the correlation between the Monopix DUT and FE-I4 in the direction of corr_str_orientation
        """
        plt.clf()
        fig = plt.figure()
        plt.hist2d(corr_dut,corr_ref,bins=[np.arange(0,dim_size_dut),np.arange(0,dim_size_ref)], norm=colors.LogNorm())
        plt.title("{0} correlation".format(corr_str_orientation))
        plt.xlabel("DUT {0}".format(dim_str_dut))
        plt.ylabel("Reference Plane {0}".format(dim_str_ref))
        plt.colorbar(label="N. Hits")
        self._save_plots(fig, self.PLOT_N_COUNTER, suffix="corr_{0}".format(dim_str_ref), tight=False, save_png=self.save_png, save_single_pdf=self.save_single_pdf)              

    def plot_phase_fraction(self, monopix_phase_fraction):
        """
        Plots the correlation between the Monopix DUT and FE-I4 in the direction of corr_str_orientation
        """
        # Generate a plot with the distribution of hits across all phases (Equally likely in an untriggered device)
        plt.clf()
        fig = plt.figure()
        plt.plot(monopix_phase_fraction, 'o')
        plt.title("Percentage of hits in a single BXID")
        plt.xlabel("Phase [640MHz Clk]")
        plt.ylabel("Percentage of hits in largest BXID")
        plt.ylim(0,1.1)
        plt.axhline(0.95, color='r', linestyle='--', label="95%")
        plt.grid()
        plt.legend()
        self._save_plots(fig, self.PLOT_N_COUNTER, suffix="phase_fraction", tight=False, save_png=self.save_png, save_single_pdf=self.save_single_pdf)              

    def plot_LEvsRX1(self, hist, boxfit_params, diff_offset, lower_lim, upper_lim):        
        """
        Plots the raw difference between the LE and RX1 timestamps, fit for the largest peak and cuts performed to filter mismatched data
        """
        x=hist[1][:-1]
        y=hist[0]
        width=boxfit_params[2]
        sigma=boxfit_params[3]

        plt.clf()
        fig = plt.figure()
        plt.step(x, y)
        plt.plot(hist[1][:-1], mono_utils.boxfc(hist[1][:-1], *boxfit_params), label="Amp=%.2E\nMean=%.2E\nWidth=%.2f\nSigma_Box=%.2f"%(boxfit_params[0],boxfit_params[1],boxfit_params[2],boxfit_params[3]))

        plt.title("LE-Scintillator(RX1) [640MHz]")
        plt.xlabel("LE-RX1 [640MHz Clk]")
        plt.ylabel("Events")
        plt.axvline(diff_offset-np.abs(sigma), color='g', linestyle='--', label='In-time')
        plt.axvline(diff_offset+np.abs(width)+np.abs(sigma), color='g', linestyle='--')
        plt.axvline(lower_lim, color='r', linestyle='--', label='TLU cut')
        plt.axvline(upper_lim, color='r', linestyle='--')
        plt.yscale("log")
        plt.legend(loc=1)
        plt.ylim(bottom=1E0)

        self._save_plots(fig, self.PLOT_N_COUNTER, suffix="LE-Rx1_HR_full_range", tight=False, save_png=self.save_png, save_single_pdf=self.save_single_pdf)
        plt.xlim(lower_lim-1000,upper_lim+1000)
        self._save_plots(fig, self.PLOT_N_COUNTER, suffix="LE-Rx1_HR_medium_range", tight=False, save_png=self.save_png, save_single_pdf=self.save_single_pdf)
        plt.xlim(lower_lim-50,upper_lim+50)
        self._save_plots(fig, self.PLOT_N_COUNTER, suffix="LE-Rx1_HR_short_range", tight=False, save_png=self.save_png, save_single_pdf=self.save_single_pdf)

    def plot_built_events(self, event_table, pix_calibration):
        """
        This function plots some elements of the final event distribution for data quality checking. 
        """
        # Plot Frame (Time-walk) distribution of events before TBA
        diff=np.int64(event_table["frame"])
        hist=np.histogram(diff, bins=np.arange(-0x10000,0x10000,0x1))
        x=hist[1][:-1]
        y=hist[0]

        print("Fitting a box function to FRAME distribution...")
        boxfit_params=mono_utils.fit_boxfc(x, y)
        print ("Values found: Amp=%.2E, Mean=%.2E, Width=%.2f, Sigma_Box=%.2f"%(boxfit_params[0],boxfit_params[1],boxfit_params[2],boxfit_params[3]))

        width=boxfit_params[2]
        sigma=boxfit_params[3]

        diff_offset=boxfit_params[1]-boxfit_params[2]/2.0
        lower_lim=round(diff_offset-1*np.abs(width)-5*np.abs(sigma),0)
        upper_lim=round(diff_offset+6*np.abs(width)+5*np.abs(sigma),0)
        print("Rising edge of the main peak (TLU-RX1 offset @ 640MHz Clocks) located at %s"%str(diff_offset))

        plt.clf()
        fig = plt.figure()
        plt.step(x, y)
        plt.plot(hist[1][:-1], mono_utils.boxfc(hist[1][:-1], *boxfit_params), label="Amp=%.2E\nMean=%.2E\nWidth=%.2f\nSigma_Box=%.2f"%(boxfit_params[0],boxfit_params[1],boxfit_params[2],boxfit_params[3]))

        plt.title("Frame in built events [640MHz]")
        plt.xlabel("Frame (LE-RX1) [640MHz Clk]")
        plt.ylabel("Events")
        plt.axvline(diff_offset-np.abs(sigma), color='g', linestyle='--', label='In-time')
        plt.axvline(diff_offset+np.abs(width)+np.abs(sigma), color='g', linestyle='--')
        #plt.axvline(lower_lim, color='r', linestyle='--', label='TLU cut')
        #plt.axvline(upper_lim, color='r', linestyle='--')
        plt.yscale("log")
        plt.legend(loc=1)
        plt.ylim(bottom=1E0)

        plt.xlim(lower_lim-50,upper_lim+50)
        self._save_plots(fig, self.PLOT_N_COUNTER, suffix="events_Frame", tight=False, save_png=self.save_png, save_single_pdf=self.save_single_pdf)

        # Plot ToT/charge distribution of events before TBA
        plt.clf()
        fig = plt.figure()
        plt.hist(event_table["tot"], bins=np.arange(0,64,1),histtype='step')
        plt.title("ToT distribution of hits in built events")
        plt.xlabel("ToT [40MHz Clk]")
        plt.ylabel("Events")
        self._save_plots(fig, self.PLOT_N_COUNTER, suffix="events_ToT", tight=False, save_png=self.save_png, save_single_pdf=self.save_single_pdf)

        if pix_calibration is not None:
            plt.clf()
            fig = plt.figure()
            plt.hist(event_table["charge"], bins=np.arange(0,20000,172),histtype='step')
            plt.title("Charge distribution of hits in built events")
            plt.xlabel("Charge [e-]")
            plt.ylabel("Events")
            plt.xlim(0,20000)
            self._save_plots(fig, self.PLOT_N_COUNTER, suffix="events_Charge", tight=False, save_png=self.save_png, save_single_pdf=self.save_single_pdf)
        else:
            pass

        # Plot Phase distribution of events before TBA
        plt.clf()
        fig = plt.figure()
        plt.hist(event_table["phase"], bins=np.arange(0,17,1),histtype='step')
        plt.title("Phase distribution of hits in built events")
        plt.xlabel("Phase [640MHz Clk]")
        plt.ylabel("Events")
        self._save_plots(fig, self.PLOT_N_COUNTER, suffix="events_Phase", tight=False, save_png=self.save_png, save_single_pdf=self.save_single_pdf)
