import os
import tables as tb
import numpy as np
import matplotlib.pyplot as plt
from scipy.special import erf
from scipy.optimize import curve_fit, leastsq
import numba
import math
import logging

COL_SIZE = 56 
ROW_SIZE = 340

def scurve(x, A, mu, sigma):
    return 0.5*A*erf((x-mu)/(np.sqrt(2)*sigma))+0.5*A

def scurve_rev(x, A, mu, sigma):
    return 0.5*A*erf((mu-x)/(np.sqrt(2)*sigma))+0.5*A

def gauss_func(x_data, *parameters):
    """Gauss function"""
    A_gauss, mu_gauss, sigma_gauss = parameters
    return A_gauss*np.exp(-(x_data-mu_gauss)**2/(2.*sigma_gauss**2))

def fit_scurve1(xarray,yarray,A=None,cut_ratio=0.05,reverse=True,debug=0):
    if A is None:
        A=np.max(yarray)
        
    if reverse==True:
        arg=np.argsort(xarray)[::-1]
    else:
        arg=np.argsort(xarray)
    yarray=yarray[arg]
    xarray=xarray[arg]
    if debug==1:
        plt.plot(xarray,yarray,".")
        
    no_cut=np.argwhere(yarray==A)
    if len(no_cut)>0:
        no0=no_cut[0][0]
        for n in no_cut[1:]:
           if n[0]==no0+1:
              no0=n[0]
           else:
              break
        no_cut=min(max(no_cut[0][0]+5,no0),len(yarray))
    else:
        no_cut=len(xarray)
    cut_low=np.argwhere(yarray[:]>=A*(1-cut_ratio))
    if len(cut_low)>0:
        cut=min(no_cut,cut_low[-1][0])
    else:
        cut=len(xarray)
    cut_high=np.argwhere(yarray[:]>=A*(1+cut_ratio))
    if len(cut_high)>0:
        cut=min(cut_high[0][0],cut)
    yarray=yarray[:cut]
    xarray=xarray[:cut]
        
    mu=xarray[np.argmin(np.abs(yarray-A*0.5))]
    try:
        sig2=xarray[np.argwhere(yarray>A*cut_ratio)[0]][0]
        sig1=xarray[np.argwhere(yarray>A*(1-cut_ratio))[0]][0]
        sigma=abs(sig1-sig2)/3.5
    except:
        sigma=1
    if debug==1:
        print ("estimation",A,mu,sigma)

    if debug==1:
        plt.plot(xarray,yarray,"o")
        plt.plot(xarray,scurve_rev(xarray,A,mu,sigma),"--")
    try:
        if reverse:
            p,cov = curve_fit(scurve_rev, xarray, yarray, p0=[A,mu,sigma])
        else:
            p,cov = curve_fit(scurve, xarray, yarray, p0=[A,mu,sigma])
    except RuntimeError:
        if debug==2:
            print('fit did not work')
        return A,mu,sigma,float("nan"),float("nan"),float("nan")
    err=np.sqrt(np.diag(cov))
    return p[0],p[1],p[2],err[0],err[1],err[2]
    
def fit_scurve(xarray,yarray,A=None,cut_ratio=0.05,reverse=True,debug=0):
    if A is None:
        A=np.max(yarray)
        
    if reverse==True:
        arg=np.argsort(xarray)[::-1]
    else:
        arg=np.argsort(xarray)
    yarray=yarray[arg]
    xarray=xarray[arg]
    if debug==1:
        plt.plot(xarray,yarray,".")
        
    #### cut
    cut=len(xarray)
    cut_low=np.argwhere(yarray>=A*(1-cut_ratio))
    if len(cut_low)>0:
        no_cut=cut_low[0][0]
        if cut_low[-1][0] > 1:
            cut=cut_low[-1][0]

    cut_high=np.argwhere(yarray>=A*(1+cut_ratio))    
    if len(cut_high)>0:
        if cut_high[0][0] > no_cut:
            cut=min(cut_high[0][0], cut)
    yarray=yarray[:cut]
    xarray=xarray[:cut]
        
    mu=xarray[np.argmin(np.abs(yarray-A*0.5))]
    try:
        sig2=xarray[np.argwhere(yarray>A*cut_ratio)[0]][0]
        sig1=xarray[np.argwhere(yarray>A*(1-cut_ratio))[0]][0]
        sigma=abs(sig1-sig2)/3.5
    except:
        sigma=1
    if debug==1:
        print ("estimation",A,mu,sigma)

    if debug==1:
        plt.plot(xarray,yarray,"o")
        plt.plot(xarray,scurve_rev(xarray,A,mu,sigma),"--")
    try:
        if reverse:
            p,cov = curve_fit(scurve_rev, xarray, yarray, p0=[A,mu,sigma])
        else:
            p,cov = curve_fit(scurve, xarray, yarray, p0=[A,mu,sigma])
    except RuntimeError:
        if debug==2:
            print('fit did not work')
        return A,mu,sigma,float("nan"),float("nan"),float("nan")
    err=np.sqrt(np.diag(cov))
    return p[0],p[1],p[2],err[0],err[1],err[2]
    
def scurve_from_fit(th, A_fit,mu_fit,sigma_fit,reverse=True,n=500):
    th_min=np.min(th)
    th_max=np.max(th)
    
    x=np.arange(th_min,th_max,(th_max-th_min)/float(n))
    if reverse:
        return x,scurve_rev(x,A_fit,mu_fit,sigma_fit)
    else:
        return x,scurve(x,A_fit,mu_fit,sigma_fit)

def get_scurve(f_event,pixel,type="inj"):
    res={}
    dat=f_event.root.Cnts[:]
    fit=f_event.root.ScurveFit[:]
    
    if type=="inj":
        x=f_event.root.ScurveFit.attrs.injlist
    elif type=="th":
        x=f_event.root.ScurveFit.attrs.thlist
    else:
        print ("Unknown type of variable specified for pix=[%d %d]"%(pixel[0],pixel[1]))
    
    tmp=dat[np.bitwise_and(dat["col"]==pixel[0],dat["row"]==pixel[1])]
    cnt=np.zeros(len(x))
    for d in tmp:
        a=np.argwhere(np.isclose(x,d[type]))
        cnt[a[0][0]]=d["cnt"]
        res["x"]=x
        res["y"]=np.copy(cnt)
    tmp=fit[np.bitwise_and(fit["col"]==pixel[0],fit["row"]==pixel[1])]
    if len(tmp)==0:
        print ("onepix_scan.get_scurve() pix=[%d %d] has no fitted parameters"%(pixel[0],pixel[1]))
        res["x"]=x
        res["y"]=np.copy(cnt)
        res["A"]=float("nan")
        res["mu"]=float("nan")
        res["sigma"]=float("nan")
    else:
        res["A"]=tmp[0]["A"]
        res["mu"]=tmp[0]["mu"]
        res["sigma"]=tmp[0]["sigma"]
        if len(tmp)>1:
            print ("onepix_scan.get_scurve():error!! pix=[%d %d] has multiple fitting"%(pixel[0],pixel[1]))
    return res

def fit_gauss(x_data, y_data):
    """Fit gauss"""
    x_data = np.array(x_data)
    y_data = np.array(y_data)
    y_maxima=x_data[np.where(y_data[:]==np.max(y_data))[0]]    
    params_guess = np.array([np.max(y_data), y_maxima[0], np.std(x_data)])
    try:
        params_from_fit = curve_fit(gauss_func, x_data, y_data, p0=params_guess, maxfev=1000)
    except RuntimeError:
        logging.warning('Fit did not work (gauss): %s %s %s', str(np.max(y_data)), str(x_data[np.where(y_data[:] == np.max(y_data))[0]][0]), str(np.std(x_data)))
        return params_guess[0],params_guess[1],params_guess[2]
    A_fit = params_from_fit[0][0]
    mu_fit = params_from_fit[0][1]
    sigma_fit = np.abs(params_from_fit[0][2])
    return A_fit, mu_fit, sigma_fit


def get_latest_config_node_from_files(directory):
    ''' Returns the latest usable h5 file in the directory for the config.

        Usable means: file handel available and file not broken
    '''
    # Naming suffices of scans
    scan_pattern = ('scan_minGlobalTH', 'scan_threshold', 'tune_threshold_inj')
    files = []

    for f in os.listdir(directory):
        if (os.path.isfile(os.path.join(directory, f)) and
            f.lower().endswith('.h5') and
                f.split('.')[-2].endswith(scan_pattern)):
            files.append(os.path.join(directory, f))

    # Sort via time stamp in file name and put _interpreted files first
    files = sorted(files, reverse=True)

    # Get latest usable file
    for file in files:
        try:   # Check if file can be opened in read only mode (as the scan_base does)
            f = tb.open_file(file)
        except (ValueError, tb.exceptions.HDF5ExtError):  # file handle in use
            continue
        try:   # Check if file has a configuration_out node
            f.root.pixel_conf
            f.close()
            return file
        except tb.exceptions.NoSuchNodeError:
            pass
        try:   # Check if file has a configuration_in node
            f.root.pixel_conf_before
            f.close()
            return file
        except tb.exceptions.NoSuchNodeError:
            pass
        finally:  # always close the open file
            f.close()
