from __future__ import division
from numpy import logical_and, average, diff
from matplotlib.mlab import find
import numpy as np
from scipy import signal
import matplotlib.pyplot as plt
import math

__author__ = 'detldaq'

def calc_ride_through_duration(wfmtime, ac_current, ac_voltage=None, grid_trig=None, v_window=20., trip_thresh=3.):
    """ Returns the time between the voltage change and when the EUT tripped

    wfmtime is the time vector from the waveform
    ac_current is the raw current measurement from the DAQ corresponding to wfmtime times
    ac_voltage  is the raw voltage measurements from the DAQ corresponding to wfmtime times
    grid_trig is the trigger measurement corresponding to wfmtime times
    v_window is the window around the nominal RMS voltage where the VRT test is started
    trip_thresh is the RMS current level where the EUT is believe to be tripped or ceasing to energize

    There are two options for determining the start of the VRT test (the latter is used when ac_voltage != None)
    1. Using the trigger channel from the grid simulator
    2. Using the RMS calculation of the ac voltage to determine when the voltage exits v_nominal +/- v_window
    """

    import wave
    import matplotlib.pyplot as plt

    f_grid = 60.
    cycles_in_window = 1.
    window_size = cycles_in_window*(1./f_grid)*1000.  # in ms

    if ac_voltage is not None:  # use the ac voltage RMS values to determine when the vrt test starts
        time_RMS, ac_voltage_RMS = calculateRmsOfSignal(ac_voltage, windowSize=window_size,
                                                        samplingFrequency=24e3,
                                                        overlap=int(window_size/3))
        v_nom = 240.
        volt_idx = [idx for idx, i in enumerate(ac_voltage_RMS) if (i <= (v_nom - v_window) or i >= (v_nom + v_window))]
        if len(volt_idx) != 0:
            try:
                vrt_start = time_RMS[min(volt_idx)]
            except:
                raise script.ScriptFail('Error in Waveform File. Unable to get voltage time from wfmtime: %s' % str(e))
        else:
            raise script.ScriptFail('No voltage deviation in the waveform file.')

        '''
        # for comparison
        trig_thresh = 3.
        trig_idx = [idx for idx, i in enumerate(grid_trig) if i >= trig_thresh]
        if len(trig_idx) != 0:
            try:
                vrt_start = wfmtime[min(trig_idx)]
            except:
                raise script.ScriptFail('Error in Waveform File. Unable to get trig time from wfmtime: %s' % str(e))
        else:
            raise script.ScriptFail('No daq trigger in the waveform file.')
        '''

    else:  # use the trigger to indicate when the grid simulator started the VRT test
        trig_thresh = 3.
        trig_idx = [idx for idx, i in enumerate(grid_trig) if i >= trig_thresh]
        if len(trig_idx) != 0:
            try:
                vrt_start = wfmtime[min(trig_idx)]
            except:
                raise script.ScriptFail('Error in Waveform File. Unable to get trig time from wfmtime: %s' % str(e))
        else:
            raise script.ScriptFail('No daq trigger in the waveform file.')

    ac_current_thresh = trip_thresh  # Amps
    time_RMS, ac_current_RMS = calculateRmsOfSignal(ac_current, windowSize=window_size,
                                                    samplingFrequency=24e3,
                                                    overlap=int(window_size/3))

    ac_current_idx = [idx for idx, i in enumerate(ac_current_RMS) if i <= ac_current_thresh]
    if len(ac_current_idx) != 0:
        try:
            trip_time = time_RMS[min(ac_current_idx)]
        except:
            raise script.ScriptFail('Error in Waveform File. Unable to get trip time from wfmtime: %s' % str(e))

        '''
        plt.plot(wfmtime, ac_current, color='blue', label='ac_current')
        plt.plot(time_RMS, ac_current_RMS, color='black', label='ac_current_RMS')
        plt.plot(wfmtime, grid_trig, color='g', label='grid_trig')
        plt.plot([vrt_start, vrt_start], [min(ac_current), max(ac_current)], color='red', label='VRT start-trig')
        # plt.plot([vrt_start_RMS, vrt_start_RMS], [min(ac_current), max(ac_current)], 'r-.', label='VRT start-RMS')
        plt.plot([trip_time, trip_time], [min(ac_current), max(ac_current)], 'r--', label='EUT trip')
        plt.legend()
        plt.grid(which='both', axis='both')
        plt.show()
        '''

        return trip_time - vrt_start

    else:
        trip_time = 0.  # no trip occurred
        return trip_time


def freq_from_crossings(wfmtime, sig, fs):
    """Estimate frequency by counting zero crossings

    Doesn't work if there are multiple zero crossings per cycle.

    """
    from scipy import signal
    import matplotlib.pyplot as plt

    # FILTER THE WAVEFORM WITH LOWPASS BUTTERWORTH FILTER
    # todo: revisit the wn calculation to be sure it works for multiple sampling rates
    wn = (2*math.pi*60)/fs  #Wn is normalized from 0 to 1, where 1 is the Nyquist frequency, pi radians/sample
    b, a = signal.butter(4, wn, analog=False)
    sig_ff = signal.filtfilt(b, a, sig)

    #check the frequency response
    '''
    w, h = signal.freqs(b, a)
    plt.plot(w, 20 * np.log10(abs(h)))
    plt.xscale('log')
    plt.title('Butterworth filter frequency response')
    plt.xlabel('Frequency [radians / second]')
    plt.ylabel('Amplitude [dB]')
    plt.margins(0, 0.1)
    plt.grid(which='both', axis='both')
    plt.show()
    '''

    # Find the zero crossings of the filtered data
    # Linear interpolation to find truer zero crossings

    indices = find(logical_and(sig_ff[1:] >= 0., sig_ff[:-1] < 0.))
    crossings = [i - sig_ff[i] / (sig_ff[i+1] - sig_ff[i]) for i in indices]  #interpolate
    cross_times = wfmtime[0] + np.array(crossings)/fs

    '''
    plt.plot(wfmtime, sig, color='red', label='Original')
    plt.plot(wfmtime, sig_ff, color='blue', label='filtered data')
    plt.plot(cross_times, np.zeros(len(cross_times)), 'ro', label='Zero Crossings')
    plt.legend()
    plt.grid(which='both', axis='both')
    plt.axis([0, 5/60, min(sig)/2, max(sig)/2])
    plt.show()
    '''

    time_steps = diff(crossings)
    avg_freq = fs / average(time_steps)
    freqs = [fs/time_steps[i] for i in xrange(0, len(cross_times)-1)]  #interpolate
    freq_times = [(cross_times[i]+cross_times[i+1])/2 for i in xrange(0, len(freqs)-1)]  #interpolate

    plt.plot(wfmtime, sig, color='red', label='Original')
    plt.plot(wfmtime, sig_ff, color='blue', label='Filtered data')
    plt.plot(freq_times, freqs[:-1], 'g', label='Frequency')
    plt.legend(loc=4)
    plt.grid(which='both', axis='both')
    plt.axis([0, freq_times[-1], 50, 61])
    plt.show()

    return avg_freq, freqs


def calculateRMS(data):
    ######################################################################
    #   calculates the RMS data of the given array
    #   @param a list or a numpy array
    #   @return a scalar containing either an RMS value
    #   http://homepage.univie.ac.at/christian.herbst//python/dsp_util_8py_source.html
    tmp = 0
    size = len(data)
    for i in range(size):
        tmp += data[i]
    mean = tmp / float(size)
    #print "mean: ", mean
    tmp = 0
    for i in range(size):
        tmp2 = data[i] - mean
        tmp += tmp2 * tmp2
    tmp /= float(size)
    return math.sqrt(tmp)


def calculateRmsOfSignal(data, windowSize, samplingFrequency, overlap=0):
    ######################################################################
    #   calculate and return the time-varying RMS of a signal
    #   @param data a list or a numpy array containing the signal that should be
    #       analyzed
    #   @param windowSize duration of the sliding analysis window in milli-seconds
    #   @param samplingFrequency sampling frequency [Hz]
    #   @param overlap overlap between individual windows, specified in milli-seconds
    #   @return a tuple containing two numpy arrays for the temporal offset and the
    #       RMS value at the respective temporal offset.
    #   http://homepage.univie.ac.at/christian.herbst//python/dsp_util_8py_source.html

    if windowSize < 1:
        raise Exception("window size must not below 1 ms")
    if overlap >= windowSize:
        raise Exception("overlap must not exceed window size")

    numFrames = len(data)
    duration = numFrames / float(samplingFrequency)

    readProgress = (windowSize - overlap) / 1000.0
    outputSize = int(duration / readProgress)
    dataX = np.zeros(outputSize)
    dataY = np.zeros(outputSize)
    t = 0
    halfWindowSize = windowSize / 2000.0
    for idx in range(outputSize):
        left = int((t - halfWindowSize) * float(samplingFrequency))
        right = left + int(windowSize * float(samplingFrequency) / 1000.0)
        if right >= numFrames:
            right = numFrames - 1
        numFramesLocal = right - left
        #print idx, t, left, right, readProgress
        if numFramesLocal <= 0:
            raise Exception("zero window size (t = " + str(t) + " sec.)")
        dataTmp = np.zeros(numFramesLocal)
        for i in range(numFramesLocal):
            dataTmp[i] = data[i + left]
        dataX[idx] = t
        t += readProgress
        rms = calculateRMS(dataTmp)
        dataY[idx] = rms

    return dataX[1:], dataY[1:]  #throw away awful first data point

if __name__ == "__main__":

    import sandia_dsm as dsm
    wfmtrigger = dsm.WfmTrigger(ts=None)

    # get data from waveform saved on the hard drive
    # (this function could use a little help to make it more robust...)
    wfmname = wfmtrigger.getfilename()
    print('Analyzing waveform data in file "%s".' % wfmname)
    wfmtime, ac_voltage, ac_current, grid_trig = wfmtrigger.read_file(wfmname)

    ride_through_time = calc_ride_through_duration(wfmtime, ac_current, ac_voltage=ac_voltage, grid_trig=grid_trig)

    ride_through_time = calc_ride_through_duration(wfmtime, ac_current, grid_trig=grid_trig)
    '''
    plt.plot(wfmtime, ac_voltage, color='blue', label='ac_voltage data')
    plt.plot(wfmtime, ac_current, color='red', label='ac_current')
    plt.plot(wfmtime, grid_trig, 'g', label='grid_trig')
    plt.grid(which='both', axis='both')
    plt.show()

    plt.plot(wfmtime, grid_trig, 'g', label='grid_trig')
    plt.grid(which='both', axis='both')
    plt.show()

    fs = 24e3
    avg_frequency, frequencies = freq_from_crossings(wfmtime, ac_voltage, fs)
    #print frequencies

    cycles_in_window = 5.
    f_grid = 60.
    windowSize = cycles_in_window*(1./f_grid)*1000.  # in ms
    time_RMS, ac_voltage_RMS = calculateRmsOfSignal(ac_voltage, windowSize=windowSize, samplingFrequency=fs,
                                                    overlap=windowSize/3)

    wn = (2.*math.pi*60.)/fs  #Wn is normalized from 0 to 1, where 1 is the Nyquist frequency, pi radians/sample
    b, a = signal.butter(4, wn, analog=False)
    sig_ff = signal.filtfilt(b, a, ac_voltage)
    time_filt_RMS, ac_voltage_filt_RMS = calculateRmsOfSignal(sig_ff, windowSize=windowSize,
                                                              samplingFrequency=fs, overlap=windowSize/3)

    print ac_voltage_filt_RMS
    print ac_voltage_RMS

    plt.plot(wfmtime, ac_voltage, color='red', label='Voltage')
    plt.plot(time_RMS, ac_voltage_RMS, color='black', label='Voltage_RMS')
    plt.plot(wfmtime, sig_ff, color='green', label='Voltage Filtered')
    plt.plot(time_filt_RMS, ac_voltage_filt_RMS, color='blue', label='Filtered Voltage_RMS')
    plt.legend()
    plt.grid(which='both', axis='both')
    plt.show()
    '''
