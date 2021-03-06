from pylab import *
import fm

#computes autocorrelation function based on convolution theorem
def auto_corr(a, c=1, d=1):
    co = np.zeros(int(fm.N2/2)+1)
    ft = np.fft.rfft(a)
    for i in range(len(a)):
        #co = np.sum([co, conjugate(np.fft.rfft(a[i]**c))*np.fft.rfft(a[i]**d)/len(a)],0)
        #co = sum([co, conjugate(ft[i])*ft[i]/len(a)], 0)
        co = co + conjugate(ft[i])*ft[i]
    #return real(co/len(a)), np.roll(np.fft.irfft(real(co/len(a))), int(fm.N2/2))
    return float32(real(co/len(a))), np.array([])
