###
### calculating correlation functions and information for MM and VM (simulation and analytic)
###

from pylab import *
#from lif import *
from hypergeometric import nu0, U, dU, d2U, C0, chiM, chiA, Sst, S_mono, MI
import fm
from AmAutoAll import auto_corr #, isi, get_isi2_parallel
#from AmCrossAll import corr
from corr_fun import corr
import multiprocessing
from joblib import Parallel, delayed
from scipy.integrate import cumtrapz

#import seaborn as sns
from scipy.stats import norm, rayleigh

#import pyximport
#pyximport.install()
import timecourse as tc


####
#ANALYTIC PART
########

######
#need to change to S_mono in hypergeometric first!
#####

def CcrossMM(R, theta, mu, sigN, tauM, Vr, sigS, tauS, w):  
    return abs(chiM(R, theta, mu, sigN, tauM, Vr, w))**2*Sst(sigS, tauS[0], w, tauS[1])

def CcrossAM(R, theta, mu, sigN, tauM, Vr, sigS, tauS, w):  
    return abs(chiA(R, theta, mu, sigN, tauM, Vr, w))**2*Sst(sigS*sigN**2, tauS[0], w, tauS[1])

def CautoAM(R, theta, mu, sigN, tauM, Vr, sigS, tauS, w): 
    return C0(R, theta, mu, sigN, tauM, Vr, w) +  abs(chiA(R, theta, mu, sigN, tauM, Vr, w))**2*Sst(sigS*sigN**2,tauS[0], w, tauS[1])

def corr_combined(R, theta, mu, sigN, tauM, Vr, sigS, tauS, w, method = 0):
    if method == 0:
        g = CcrossMM
    if method == 1:
        g = CcrossAM
    cross = g(R, theta, mu, sigN, tauM, Vr, sigS, tauS, w)
    c0 = C0(R, theta, mu, sigN, tauM, Vr, w)
    auto = cross + c0
    return auto, cross

def CV_ana(R, theta, mu, sigN, tauM, Vr, sigS, tauS, method = 0):
    a = corr_combined(R, theta, mu, sigN, tauM, Vr, sigS, tauS, 1e-7, method)[0]
    b = nu0(R, theta, mu, sigN, tauM, Vr)
    return b, sqrt(a/b)

def analytic_all(R=.04, theta = 15., mu = 300., sigN = 300, tM = 10, Vres = 0, sigS = .25*300, tS = [50., 10.], tauN = 0., n = 180, N = 5e5, dt = .02, method = 0, ns = 1, omega_start = 0, omega_end = 4.):
    fm.N = N
    fm.dt = dt
    tauM = tM
    omega_e = omega_end*fm.N*fm.dt/(2*pi) #choose Omega0+sqrt(prec)/sqrt(tauS)
    omega_s = omega_start*fm.N*fm.dt/(2*pi)+1
    num_cores = multiprocessing.cpu_count()
    t = [2*pi*x/(fm.N*fm.dt) for x in linspace(omega_s, omega_e, n)]
    print "analytic ACF/CCF"
    ana =  Parallel(n_jobs=num_cores)(delayed(corr_combined)(R, theta, mu, sigN, tauM, Vres, sigS, tS, x, method) for x in t)
    ac_ana, cc_ana = [x[0] for x in ana], [x[1] for x in ana]
    print "analytic ACF/CCF done"
    print "analytic MI (cumtrapz)"
    mi = cumtrapz(-.5*log2(double(1 - array(cc_ana)/array(ac_ana))), dx = t[1]-t[0])
    return double(ac_ana), double(cc_ana), double(t), mi

#only for correction; because too short range of omega had been chosen
def analytic_all2(R=.04, theta = 15., mu = 300., sigN = 300, tM = 10, Vres = 0, sigS = .25*300, tS = [50., 10.], tauN = 0., n = 180, N = 5e5, dt = .02, method = 0, ns = 1, omega_start = 0, omega_end = 4.):
    fm.N = N
    fm.dt = dt
    tauM = tM
    omega_e = omega_end*fm.N*fm.dt/(2*pi)
    omega_s = omega_start*fm.N*fm.dt/(2*pi)
    num_cores = multiprocessing.cpu_count()
    t = [2*pi*x/(fm.N*fm.dt) for x in linspace(omega_s+(omega_e-omega_s)/n, omega_e, n)]
    print "analytic ACF/CCF"
    ana =  Parallel(n_jobs=num_cores)(delayed(corr_combined)(R, theta, mu, sigN, tauM, Vres, sigS, tS, x, method) for x in t)
    ac_ana, cc_ana = [x[0] for x in ana], [x[1] for x in ana]
    print "analytic ACF/CCF done"
    print "analytic MI (cumtrapz)"
    mi = cumtrapz(-.5*log2(double(1 - array(cc_ana)/array(ac_ana))), dx = t[1]-t[0])
    return double(ac_ana), double(cc_ana), double(t), mi

def analytic_auto(R=.15, theta = 20., mu = 100., sigN = 400, tM = 30, Vres = -5, sigS = .25, tS = [50, 0], tauN = 0., n = 200, N = 5e5, dt = .02, method = 0, omega_end = 2.):
    fm.N = N
    fm.dt = dt
    tauM = tM
    omega_e = omega_end*fm.N*fm.dt/(2*pi)
    num_cores = multiprocessing.cpu_count()
    t = [2*pi*x/(fm.N*fm.dt) for x in linspace(1, omega_end, n)]
    ana =  Parallel(n_jobs=num_cores)(delayed(corr_combined)(R, theta, mu, sigN, tauM, Vres, sigS, tS, x, method) for x in t)
    ac_ana, cc_ana = [x[0] for x in ana], [x[1] for x in ana]
    return ac_ana, cc_ana, t

####
#SIMULATION PART
########

######AUTO######
def AC_sim(R=.15, theta = 20., mu = 0., sigS = .25, sigN = 400, tS = [85, 0], tM = 30, Vres = -5, tauN = 1., n = 100, method = 0, model = 'LIF', DeltaT = 1.5, tref = 5.):
    if model == 'LIF': cell = tc.SimpleIF(tM, R, 0., ures = Vres, V_thr = theta)
    if model == 'EIF': cell = tc.EIF(tM, R, 0., ures = Vres, V_thr = theta, DeltaT= DeltaT, tref=tref)
    if method == 0:
        g = fm.MM
    if method ==1:
        g = fm.AM_var
    #generate mods, voltages and spike trains for cross corr analysis
    #sigAM = [fm.AM(fm.OU(tS, sigS), fm.OU(tauN, sigN)) + mu for x in range(n)]
    #print "generate signals and spike trains (ACF)"
    N2 = int(fm.dt*fm.N/fm.dt2)
    sAM = np.zeros([n, N2])
    for x in range(n):
        sigAM = g(fm.mono_spec(tS[0], sigS, tS[1]), fm.OU(tauN, sigN)) + mu
        cell._Vinit = R*mu
        cell.voltagecourse(sigAM[::-1][:int(3*tS[0]/fm.dt)])
        cell._Vinit = cell._vol
        #print "signal has been generated"
        #vAM =  cell.timecourse(sigAM)
        #sAM[x] = cell.spiketrain(vAM)
        sAM[x] = cell.spiketrain2(sigAM)
        #print 'spike train has been generated'
    #print "calculate ACF"
    AC = array(auto_corr(sAM, 1, 1))/(fm.N2*fm.dt2**2)
    #print 'single ACF done'
    return AC

####CROSS#####
def CC_sim(R=.15, theta = 20., mu = 0., sigS = .25, sigN = 400, tS = [85, 0], tM = 30, Vres = -5, tauN = 1., n = 100, method = 0, model = 'LIF', DeltaT = 1.5, tref = 5.):
    if model == 'LIF': cell = tc.SimpleIF(tM, R, 0., ures = Vres, V_thr = theta)
    if model == 'EIF': cell = tc.EIF(tM, R, 0., ures = Vres, V_thr = theta, DeltaT= DeltaT, tref=tref)
    #generate mods, voltages and spike trains for cross corr analysis
    if method == 0:
        g = fm.MM
    if method ==1:
        g = fm.AM_var
    #print "generate signals and spike trains (CCF)"
    sig = fm.mono_spec(tS[0], sigS, tS[1])
    N2 = int(fm.dt*fm.N/fm.dt2)
    sAM = np.zeros([n, N2])
    for x in range(n):    
        sigAM = g(sig, fm.OU(tauN, sigN)) + mu
        cell._Vinit = R*mu
        cell.voltagecourse(sigAM[::-1][:int(3*tS[0]/fm.dt)])
        cell._Vinit = cell._vol
        sAM[x] = cell.spiketrain2(sigAM)
    #print "calculate CCF"
    CC = array(corr(sAM, 1, 1))/(fm.N2*fm.dt2**2)
    #print 'single CCF done'
    return CC

#check what happens when only ampliude of coefficients in signal is fixed
def CC_sim2(R=.15, theta = 20., mu = 0., sigS = .25, sigN = 400, tS = [85, 0], tM = 30, Vres = -5, tauN = 1., n = 100, method = 0, model = 'LIF', DeltaT = 1.5, tref = 5.):
    if model == 'LIF': cell = tc.SimpleIF(tM, R, 0., ures = Vres, V_thr = theta)
    if model == 'EIF': cell = tc.EIF(tM, R, 0., ures = Vres, V_thr = theta, DeltaT= DeltaT, tref=tref)
    #generate mods, voltages and spike trains for cross corr analysis
    if method == 0:
        g = fm.MM
    if method ==1:
        g = fm.AM_var
    #print "generate signals and spike trains (CCF)"
    sig = fm.mono_spec(tS[0], sigS, tS[1])
    N2 = int(fm.dt*fm.N/fm.dt2)
    sAM = np.zeros([n, N2])
    for x in range(n):
        sig = np.roll(sig, np.random.randint(0, fm.N))
        sigAM = g(sig, fm.OU(tauN, sigN)) + mu
        cell._Vinit = R*mu
        cell.voltagecourse(sigAM[::-1][:int(3*tS[0]/fm.dt)])
        cell._Vinit = cell._vol
        #vAM =  cell.timecourse(sigAM)
        #sAM[x] = cell.spiketrain(vAM)
        sAM[x] = cell.spiketrain2(sigAM)
    #print "calculate CCF"
    CC = array(corr(sAM, 1, 1))/(fm.N2*fm.dt2**2)
    #print 'single CCF done'
    return CC


def simulate_all(R=.04, theta = 15., mu = 300., sigN = 300, tM = 10, Vres = 0, sigS = .25*300, tS = [50., 10.], tauN = 0., n = 80, N = 5e5, dt = .02, method = 0, ns = 1, model = 'LIF', DeltaT = 1.5, tref = 5.):
    fm.N = N
    fm.dt = dt
    fm.N2 = int(fm.dt*fm.N/fm.dt2)
    num_cores = multiprocessing.cpu_count()
    ac = Parallel(n_jobs=num_cores)(delayed(AC_sim)(R, theta, mu, sigS, sigN, tS, tM, Vres, tauN, n, method, model, DeltaT, tref) for x in range(num_cores))
    ac_sim_f = mean([x[0] for x in ac], 0)
    #print 'AC sim. done'
    cc =  Parallel(n_jobs=num_cores)(delayed(CC_sim)(R, theta, mu, sigS, sigN, tS, tM, Vres, tauN, n, method, model, DeltaT, tref) for x in range(ns*num_cores))
    cc_sim_f = mean([x[0] for x in cc], 0)
    #print 'CC sim. done'
    t = [2*pi*x/(fm.N*fm.dt) for x in range(len(cc_sim_f))]
    #mutual information added
    mi = cumtrapz(-.5*nan_to_num(log2(1 - array(cc_sim_f[1:])/array(ac_sim_f[1:]), dtype = double)), dx = 2*pi/(fm.N*fm.dt))
    ####used to calculate the properly averaged MI through 1/2*log(auto/sigma_Rs)
    #sigma_Rs = gmean([x[0] for x in array(ac)-array(cc)], 0)
    return ac_sim_f*fm.dt2, cc_sim_f*fm.dt2, float16(t), float16(mi), #sigma_Rs

def simulate_auto(R=.15, theta = 20., mu = 100., sigN = 400, tM = 30, Vres = -5, sigS = .25, tS = [50, 0], tauN = 0., n = 100, N = 5e5, dt = .02, method = 1, model = 'LIF', DeltaT = 1.5, tref = 5.):
    fm.N = N
    fm.dt = dt
    fm.N2 = int(fm.dt*fm.N/fm.dt2)
    num_cores = multiprocessing.cpu_count()
    ac = Parallel(n_jobs=num_cores)(delayed(AC_sim)(R, theta, mu, sigS, sigN, tS, tM, Vres, tauN, n, method, model, DeltaT, tref) for x in range(num_cores))
    ac_sim_f = mean([x[0] for x in ac], 0)
    print 'AC sim. done'
    t = [2*pi*x/(fm.N*fm.dt) for x in range(len(ac_sim_f))]
    return ac_sim_f*fm.dt2, t

def simulate_cross(R=.04, theta = 15., mu = 300., sigN = 200, tM = 10, Vres = -0, sigS = .2, tS = [50, 0], tauN = 0., n = 100, N = 5e5, dt = .02, method = 1, model = 'LIF', DeltaT = 1.5, tref = 5.):
    fm.N = N
    fm.dt = dt
    fm.N2 = int(fm.dt*fm.N/fm.dt2)
    num_cores = multiprocessing.cpu_count()
    cc =  Parallel(n_jobs=num_cores)(delayed(CC_sim)(R, theta, mu, sigS, sigN, tS, tM, Vres, tauN, n, method, model, DeltaT, tref) for x in range(num_cores))
    cc_sim_f = mean([x[0] for x in cc], 0)
    print 'CC sim. done'
    t = [2*pi*x/(fm.N*fm.dt) for x in range(len(cc_sim_f))]
    return cc_sim_f*fm.dt2, t

############################
### CHECK GAUSSIANITY
############################
def check_Gauss_CC(sig, R=.04, theta = 15., mu = 300., sigS = .25, sigN = 300, tS = [20, 10.], tM = 10, Vres = 0, tauN = 0., n = 100, method = 1, model = 'LIF', DeltaT = 1.5, tref = 5.):
    if model == 'LIF': cell = tc.SimpleIF(tM, R, 0., ures = Vres, V_thr = theta)
    if model == 'EIF': cell = tc.EIF(tM, R, 0., ures = Vres, V_thr = theta, DeltaT= DeltaT, tref=tref)
    if method == 0:
        g = fm.MM
    if method ==1:
        g = fm.AM_var
    N2 = int(fm.dt*fm.N/fm.dt2)
    sAM = np.zeros([n, N2])
    for x in range(n):    
        sigAM = g(sig, fm.OU(tauN, sigN)) + mu
        cell._Vinit = R*mu
        cell.voltagecourse(sigAM[::-1][:int(3*tS[0]/fm.dt)])
        cell._Vinit = cell._vol
        sAM[x] = cell.spiketrain2(sigAM) #roll(cell.spiketrain2(sigAM)
    CC = rfft(sAM)
    CC = (transpose(real(CC)), transpose(imag(CC)))
    return CC

def check_Gauss_AC(R=.04, theta = 15., mu = 300., sigS = .25, sigN = 300, tS = [20, 10.], tM = 10, Vres = 0, tauN = 0., n = 100, method = 1, model = 'LIF', DeltaT = 1.5, tref = 5.):
    if model == 'LIF': cell = tc.SimpleIF(tM, R, 0., ures = Vres, V_thr = theta)
    if model == 'EIF': cell = tc.EIF(tM, R, 0., ures = Vres, V_thr = theta, DeltaT= DeltaT, tref=tref)
    if method == 0:
        g = fm.MM
    if method ==1:
        g = fm.AM_var
    N2 = int(fm.dt*fm.N/fm.dt2)
    sAM = np.zeros([n, N2])
    for x in range(n):
        sig = fm.mono_spec(tS[0], sigS, tS[1])
        sigAM = g(sig, fm.OU(tauN, sigN)) + mu
        cell._Vinit = R*mu
        cell.voltagecourse(sigAM[::-1][:int(3*tS[0]/fm.dt)])
        cell._Vinit = cell._vol
        sAM[x] = roll(cell.spiketrain2(sigAM), 0)
    CC = rfft(sAM)
    CC = (transpose(real(CC)), transpose(imag(CC)))
    return CC


def check_Gauss_repeats(R=.04, theta = 15., mu = 300., sigN = 300, tM = 10, Vres = 0, sigS = .25, tS = [20., 10.], tauN = 0., n = 80, N = 5e5, dt = .02, method = 1, ns = 1, model = 'LIF', DeltaT = 1.5, tref = 5.):
    fm.N = N
    fm.dt = dt
    fm.N2 = int(fm.dt*fm.N/fm.dt2)
    signal = fm.mono_spec(tS[0], sigS, tS[1])
    num_cores = multiprocessing.cpu_count()
    ac = Parallel(n_jobs=num_cores)(delayed(check_Gauss_CC)(signal, R, theta, mu, sigS, sigN, tS, tM, Vres, tauN, n, method, model, DeltaT, tref) for x in range(num_cores))
    #return hstack(ac[0]), hstack(ac[1])
    return dstack(ac)


def check_Gauss_uniques(R=.04, theta = 15., mu = 300., sigN = 300, tM = 10, Vres = 0, sigS = .25, tS = [20., 10.], tauN = 0., n = 80, N = 5e5, dt = .02, method = 1, ns = 1, model = 'LIF', DeltaT = 1.5, tref = 5.):
    fm.N = N
    fm.dt = dt
    fm.N2 = int(fm.dt*fm.N/fm.dt2)
    num_cores = multiprocessing.cpu_count()
    ac = Parallel(n_jobs=num_cores)(delayed(check_Gauss_AC)(R, theta, mu, sigS, sigN, tS, tM, Vres, tauN, n, method, model, DeltaT, tref) for x in range(num_cores))
    return dstack(ac)

# NICE PLOTTING FUNCTION
def plot_Gauss(a, binN = 50):
    fig = figure()
    l = len(a[0])
    for i, x in enumerate(linspace(4, l/3, 5, dtype = int)):
    #for i, x in enumerate(range(1,6)):
        ax = fig.add_subplot(5, 2, 2*i+1)
        sns.jointplot(a[0][x], a[1][x], marginal_kws=dict(fit = norm, bins = binN))
        ax = fig.add_subplot(5, 2, 2*i+2)
        sns.jointplot(a[0][x], a[0][x+1], marginal_kws=dict(fit = norm, bins = binN))
        print mean(a[0][x]), mean(a[1][x]), mean(a[0][x])**2+mean(a[1][x])**2
    show()
    
def plot_Rayleigh(a):
    fig = figure()
    l = len(a[0])
    for i, x in enumerate(linspace(4, l/3, 5, dtype = int)):
    #for i, x in enumerate(range(1,6)):
        ax = fig.add_subplot(5, 2, 2*i+1)
        sns.distplot(sqrt(a[0][x]**2+a[1][x]**2), fit = rayleigh, kde = False)
        ax = fig.add_subplot(5, 2, 2*i+2)
        sns.distplot(angle(a[0][x]+1j*a[1][x]), kde = False)
    show()

def plot_freq_corr(a):
    fig = figure()
    l = len(a[0])
    ax = fig.add_subplot(3, 1, 1)
    pcolor(corrcoef(a[0].T[:460].T[:150]), cmap = 'RdBu'), colorbar(), show()
    ax = fig.add_subplot(3, 1, 2)
    pcolor(corrcoef(a[1].T[:460].T[:150]), cmap = 'RdBu'), colorbar(), show()
    ax = fig.add_subplot(313)
    plot(mean(a[0], 1)), plot(mean(a[1], 1))#plot means
    show()
############################
### CALCULATE COHERENCE
############################
def coherence_sim(R=.04, theta = 15., mu = 300., sigS = .25*300, sigN = 300, tS = [20, 0], tM = 10, Vres = 0, tauN = 0., n = 100, method = 1, model = 'LIF', DeltaT = 1.5, tref = 5.):
    if model == 'LIF': cell = tc.SimpleIF(tM, R, 0., ures = Vres, V_thr = theta)
    if model == 'EIF': cell = tc.EIF(tM, R, 0., ures = Vres, V_thr = theta, DeltaT= DeltaT, tref=tref)
    if method == 0:
        g = fm.MM
    if method ==1:
        g = fm.AM_var
    N2 = int(fm.dt*fm.N/fm.dt2)
    #sAM = np.zeros([n, int(N2)])
    #sAM = np.zeros([n, int(fm.N)])
    #sAM = np.zeros(int(fm.N))
    XX = np.zeros(int(fm.N2/2+1))
    XS = np.zeros(int(fm.N2/2+1))
    SS = np.zeros(int(fm.N2/2+1))
    for x in range(n):
        s = fm.mono_spec(tS[0], sigS, tS[1])
        sigAM = g(s, fm.OU(tauN, sigN)) + mu
        sAM = cell.spiketrain2(sigAM)
        sAM_f = np.fft.rfft(sAM)
        sigAM_f = np.fft.rfft(s)[:len(sAM_f)]#np.fft.rfft(sigAM)
        XX = XX + conjugate(sAM_f)*sAM_f
        XS = XS + conjugate(sigAM_f)*sAM_f
        SS = SS + conjugate(sigAM_f)*sigAM_f
    #print 'single ACF done'
    return float64(XX/(n*fm.dt2*fm.N2)), XS/(n*fm.N), float64(SS*fm.dt/(n*fm.N))
    #return XX/(n*fm.dt2*fm.N2), XS/(n*fm.N), SS*fm.dt/(n*fm.N)

def coherence_sim_par(R=.04, theta = 15., mu = 300., sigN = 300, tM = 10, Vres = 0, sigS = .25, tS = [20., 10.], tauN = 0., n = 80, N = 5e5, dt = .02, method = 1, ns = 1, model = 'LIF', DeltaT = 1.5, tref = 5.):
    fm.N = N
    fm.dt = dt
    #fm.dt2 = .1
    fm.N2 = int(fm.dt*fm.N/fm.dt2)
    num_cores = multiprocessing.cpu_count()
    ac = Parallel(n_jobs=num_cores)(delayed(coherence_sim)(R, theta, mu, sigS, sigN, tS, tM, Vres, tauN, n, method, model, DeltaT, tref) for x in range(num_cores))
    return mean(ac, 0)

############################
### COMBINE EXACT AND LOWER BOUND CALCULATION
############################
def combined_par(R=.04, theta = 15., mu = 300., sigN = 300, tM = 10, Vres = 0, sigS = .25, tS = [20., 10.], tauN = 0., n = 80, N = 5e5, dt = .02, method = 1, ns = 1, model = 'LIF', DeltaT = 1.5, tref = 5.):
    fm.N = N
    fm.dt = dt
    #fm.dt2 = .1
    fm.N2 = int(fm.dt*fm.N/fm.dt2)
    num_cores = multiprocessing.cpu_count()
    ac = Parallel(n_jobs=num_cores)(delayed(coherence_sim)(R, theta, mu, sigS, sigN, tS, tM, Vres, tauN, n, method, model, DeltaT, tref) for x in range(num_cores*ns))
    ac = mean(ac, 0)
    cc =  Parallel(n_jobs=num_cores)(delayed(CC_sim)(R, theta, mu, sigS, sigN, tS, tM, Vres, tauN, n, method, model, DeltaT, tref) for x in range(num_cores*ns))
    cc_sim_f = mean([x[0] for x in cc], 0)
    print 'CC sim. done. snr={}. sigN={}.'.format(sigS, sigN)
    t = [2*pi*x/(fm.N*fm.dt) for x in range(len(cc_sim_f))]
    return ac[0], cc_sim_f*fm.dt2, t, ac[1], ac[2]

