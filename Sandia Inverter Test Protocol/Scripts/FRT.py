'''
Copyright (c) 2015, Sandia National Labs and SunSpec Alliance
All rights reserved.

Redistribution and use in source and binary forms, with or without modification,
are permitted provided that the following conditions are met:

Redistributions of source code must retain the above copyright notice, this
list of conditions and the following disclaimer.

Redistributions in binary form must reproduce the above copyright notice, this
list of conditions and the following disclaimer in the documentation and/or
other materials provided with the distribution.

Neither the names of the Sandia National Labs and SunSpec Alliance nor the names of its
contributors may be used to endorse or promote products derived from
this software without specific prior written permission.

THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS "AS IS" AND
ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT LIMITED TO, THE IMPLIED
WARRANTIES OF MERCHANTABILITY AND FITNESS FOR A PARTICULAR PURPOSE ARE
DISCLAIMED. IN NO EVENT SHALL THE COPYRIGHT HOLDER OR CONTRIBUTORS BE LIABLE FOR
ANY DIRECT, INDIRECT, INCIDENTAL, SPECIAL, EXEMPLARY, OR CONSEQUENTIAL DAMAGES
(INCLUDING, BUT NOT LIMITED TO, PROCUREMENT OF SUBSTITUTE GOODS OR SERVICES;
LOSS OF USE, DATA, OR PROFITS; OR BUSINESS INTERRUPTION) HOWEVER CAUSED AND ON
ANY THEORY OF LIABILITY, WHETHER IN CONTRACT, STRICT LIABILITY, OR TORT
(INCLUDING NEGLIGENCE OR OTHERWISE) ARISING IN ANY WAY OUT OF THE USE OF THIS
SOFTWARE, EVEN IF ADVISED OF THE POSSIBILITY OF SUCH DAMAGE.

Written by Sandia National Laboratories, Loggerware, and SunSpec Alliance
Questions can be directed to Jay Johnson (jjohns2@sandia.gov)
'''

# Test script for Sandia Test Protocol L/HFRT
# This test requires the following SunSpec Alliance Modbus models:
# inverter, controls, settings, nameplate, LFRT, HFRT, LFRTC, HFRTC
#
# !C:\Python27\python.exe

import sys
import os
import math
import time
import traceback

import sunspec.core.client as client
import script
import script_util

import inverter
import terrasas
import gridsim
import sandia_dsm as dsm
import pvsim

# returns: True if state == current connection state and power generation matches threshold expectation, False if not
def verify_initial_conn_state(inv, state, time_period=0, threshold=50, das=None):
    result = None
    start_time = time.time()

    while result is None:
        elapsed_time = time.time()-start_time
        if elapsed_time <= time_period:
            if not inverter.verify_conn_state(inv, state, threshold, das):
                ts.sleep(0.89) #Attempt to make loop exactly 1 second
            else:
                result = True
        else:
            result = False

    return result

def das_init():
    das = None
    wfmtrigger = None
    wfmtrigger_params = None

    datamethod = ts.param_value('datatrig.dsm_method')
    trigmethod = ts.param_value('datatrig.trigger_method')

    # Sandia Test Protocol: test precursors
    # Setup up DAS if available. Make sure the data from the test is being recorded prior to running the test.
    if datamethod == 'Sandia LabView DSM':
        import sandia_dsm as dsm
        computer = ts.param_value('datatrig.das_comp')
        if computer == '10 Node':
            node = ts.param_value('datatrig.node')
        das = dsm.Data(dsm_id=node)

    # Setup waveform trigger if available
    if trigmethod == 'Create Local File for Sandia LabView DSM':
        import sandia_dsm as dsm
        wfmtrigger = dsm.WfmTrigger(ts)
        wfmtrigger_params = script_util.group_params(ts, group='wfm')

    return (das, wfmtrigger, wfmtrigger_params)


def calc_ride_through_duration(wfmtime, ac_current, ac_voltage=None, grid_trig=None, f_window=20., trip_thresh=3.):
    """ Returns the time between the freq change and when the EUT tripped

    wfmtime is the time vector from the waveform
    ac_current is the raw current measurement from the DAQ corresponding to wfmtime times
    ac_voltage  is the raw voltage measurements from the DAQ corresponding to wfmtime times
    grid_trig is the trigger measurement corresponding to wfmtime times
    f_window is the window around the nominal grid freq where the FRT test is started
    trip_thresh is the RMS current level where the EUT is believe to be tripped or ceasing to energize

    There are two options for determining the start of the FRT test (the latter is used when ac_voltage != None)
    1. Using the trigger channel from the grid simulator
    2. Using the freq calculation of the ac voltage to determine when the freq exits f_nominal +/- f_window
    """

    f_grid = 60.
    cycles_in_window = 1.
    window_size = cycles_in_window*(1./f_grid)*1000.  # in ms

    if ac_voltage is not None:  # use the ac voltage to calculate the frequency to determine when the FRT test starts
        fs = ts.param_value('wfm.trigsamplingrate')  # sampling rate of waveform
        avg_freq, freqs, freq_times = freq_from_crossings(wfmtime, ac_voltage, fs)

        f_nom = gsim.freq()
        freq_idx = [idx for idx, i in enumerate(freqs) if (i <= (f_nom - f_window) or i >= (f_nom + f_window))]
        if len(freq_idx) != 0:
            try:
                frt_start = freq_times[min(freq_idx)]
            except:
                raise script.ScriptFail('Error in Waveform File. Unable to get freq time: %s' % str(e))
        else:
            raise script.ScriptFail('No frequency deviation in the waveform file.')

    else:  # use the trigger to indicate when the grid simulator started the FRT test
        trig_thresh = 0.01
        trig_idx = [idx for idx, i in enumerate(grid_trig) if i >= trig_thresh]
        if len(trig_idx) != 0:
            try:
                frt_start = wfmtime[min(trig_idx)]
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
        return trip_time - frt_start

    else:
        trip_time = 0.  # no trip occurred
        return trip_time


def freq_from_crossings(wfmtime, sig, fs):
    """Estimate frequency by counting zero crossings

    Doesn't work if there are multiple zero crossings per cycle.

    """
    from scipy import signal
    #import matplotlib.pyplot as plt

    # FILTER THE WAVEFORM WITH LOWPASS BUTTERWORTH FILTER
    wn = (2*math.pi*60)/fs  #Wn is normalized from 0 to 1, where 1 is the Nyquist frequency, pi radians/sample
    b, a = signal.butter(4, wn, analog=False)
    sig_ff = signal.filtfilt(b, a, sig)

    # Find the zero crossings of the filtered data
    # Linear interpolation to find truer zero crossings
    indices = find(logical_and(sig_ff[1:] >= 0., sig_ff[:-1] < 0.))
    crossings = [i - sig_ff[i] / (sig_ff[i+1] - sig_ff[i]) for i in indices]  #interpolate
    cross_times = wfmtime[0] + np.array(crossings)/fs

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

    return avg_freq, freqs, freq_times


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

    import numpy as np

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

    tmp = 0
    for i in range(size):
        tmp2 = data[i] - mean
        tmp += tmp2 * tmp2
    tmp /= float(size)

    return math.sqrt(tmp)


def predict_frt_response_time(test_freq_pct, ride_through, h_time=0, h_freq=0, h_n_points=0,
                              l_time=0, l_freq=0, l_n_points=0,
                              hc_time=0, hc_freq=0, hc_n_points=0,
                              lc_time=0, lc_freq=0, lc_n_points=0):
    """ Calculate the frequency response time for a given test condition and FRT curves
    Return must stay connected duration (c_time) and must disconnect time (d_time)
    """
    c_time = None
    d_time = None
    lots_of_output = False

    #Check to be sure the times are monotonically increasing.
    for i in xrange(1, h_n_points-1):
        if h_time[i] > h_time[i+1]:
            ts.log_error('Times are not monotonically increasing in HFRTD curve.')
        break
    for i in xrange(1, l_n_points-1):
        if l_time[i] > l_time[i+1]:
            ts.log_error('Times are not monotonically increasing in LFRTD curve.')
        break
    for i in xrange(1, hc_n_points-1):
        if hc_time[i] > hc_time[i+1]:
            ts.log_error('Times are not monotonically increasing in HFRTC curve.')
        break
    for i in xrange(1, lc_n_points-1):
        if lc_time[i] > lc_time[i+1]:
            ts.log_error('Times are not monotonically increasing in LFRTC curve.')
        break

    if test_freq_pct > 100.:  # use HFRTD

        if test_freq_pct < h_freq[h_n_points]: #test_freq_pct is below the last point - extrapolate
            d_time = 0
            if lots_of_output:
                ts.log_debug('h_time = %s, h_time[n_points] = %s' % (h_time, h_time[h_n_points]))
                ts.log_debug('F_test is lower than HFRTD[n_points]. Trip time is %0.3f' % d_time)
        elif test_freq_pct > h_freq[1]: #test_freq_pct is above the 1st point - extrapolate
            d_time = h_time[1]  # there is no trip time - EUT should run indefinitely
            if lots_of_output:
                ts.log_debug('F_test is higher than HFRTD[1]. Trip time is %0.3f' % d_time)
        else:
            # pointwise algorithm to find target vars
            for i in xrange(1, h_n_points):
                if lots_of_output:
                    ts.log_debug('Grid frequency is %.3f' % (test_freq_pct))
                    ts.log_debug('i = %d' % i)
                    ts.log_debug('test_freq_pct >= freq[i+1] and test_freq_pct <= freq[i]')
                    ts.log_debug('%.3f >= %.3f and %.3f <= %.3f' % (test_freq_pct, h_freq[i+1], test_freq_pct, h_freq[i]))

                if test_freq_pct >= h_freq[i+1] and test_freq_pct <= h_freq[i]: #curve interpolation
                    #Time = Ti + (Ti+1 - Ti)*((test_freq_pct - Vi)/(Vi+1 - Vi))
                    d_time = h_time[i] + (h_time[i+1] - h_time[i])*((test_freq_pct - h_freq[i])/(h_freq[i+1] - h_freq[i]))
                    if lots_of_output:
                        ts.log_debug('Interpolated. Trip time is %0.3f' % d_time)
                    break

    else:  # use LFRTD
        if test_freq_pct < l_freq[1]: #test_freq_pct is below the 1st point - extrapolate
            d_time = l_time[1]
            if lots_of_output:
                ts.log_debug('l_time = %s, l_time[1] = %s' % (l_time, l_time[1]))
                ts.log_debug('F_test is lower than LFRTD[1]. Trip time is %0.3f' % d_time)
        elif test_freq_pct > l_freq[l_n_points]: #test_freq_pct is above the last point - extrapolate
            d_time = 0  # there is no trip time - EUT should run indefinitely
            if lots_of_output:
                ts.log_debug('F_test is higher than LFRTD[n_points]. Trip time is %0.3f' % d_time)
        else:
            # pointwise algorithm to find target vars
            for i in xrange(1, l_n_points):
                if lots_of_output:
                    ts.log_debug('Grid frequency is %.3f' % (test_freq_pct))
                    ts.log_debug('i = %d' % i)
                    ts.log_debug('test_freq_pct >= freq[i] and test_freq_pct <= freq[i+1]')
                    ts.log_debug('%.3f >= %.3f and %.3f <= %.3f' % (test_freq_pct, l_freq[i], test_freq_pct, l_freq[i+1]))

                if test_freq_pct >= l_freq[i] and test_freq_pct <= l_freq[i+1]: #curve interpolation
                    #Time = Ti + (Ti+1 - Ti)*((test_freq_pct - Vi)/(Vi+1 - Vi))
                    d_time = l_time[i] + (l_time[i+1] - l_time[i])*((test_freq_pct - l_freq[i])/(l_freq[i+1] - l_freq[i]))
                    if lots_of_output:
                        ts.log_debug('Interpolated. Trip time is %0.3f' % d_time)
                    break

    if ride_through == 'No':
        c_time = 0
    else:
        if test_freq_pct > 100.:  # use HFRTC
            if test_freq_pct < hc_freq[hc_n_points]: #test_freq_pct is below the last point - extrapolate
                c_time = 0
                if lots_of_output:
                    ts.log_debug('F_test is lower than HFRTC[n_points]. Ride-through time is %0.3f' % c_time)
            elif test_freq_pct > hc_freq[1]: #test_freq_pct is above the 1st point - extrapolate
                c_time = hc_time[1]  # there is no must remain connected time - EUT should run indefinitely
                if lots_of_output:
                    ts.log_debug('F_test is higher than HFRTC[1]. Ride-through time is %0.3f' % c_time)
            else:
                # pointwise algorithm to find target vars
                for i in xrange(1, hc_n_points):
                    if lots_of_output:
                        ts.log_debug('Grid frequency is %.3f' % (test_freq_pct))
                        ts.log_debug('i = %d' % i)
                        ts.log_debug('test_freq_pct >= freq[i+1] and test_freq_pct <= freq[i]')
                        ts.log_debug('%.3f >= %.3f and %.3f <= %.3f' %
                                     (test_freq_pct, hc_freq[i+1], test_freq_pct, hc_freq[i]))

                    if test_freq_pct >= hc_freq[i+1] and test_freq_pct <= hc_freq[i]: #curve interpolation
                        #Time = Ti + (Ti+1 - Ti)*((test_freq_pct - Vi)/(Vi+1 - Vi))
                        c_time = hc_time[i] + (hc_time[i+1] - hc_time[i])*\
                                              ((test_freq_pct - hc_freq[i])/(hc_freq[i+1] - hc_freq[i]))
                        if lots_of_output:
                            ts.log_debug('Interpolated. Ride-through time is %0.3f' % c_time)
                        break
        else:  # use LFRTD
            if test_freq_pct < lc_freq[1]: #test_freq_pct is below the 1st point - extrapolate
                c_time = lc_time[1]
                if lots_of_output:
                    ts.log_debug('F_test is lower than LFRTC[1]. Ride-through time is %0.3f' % c_time)
            elif test_freq_pct > lc_freq[lc_n_points]: #test_freq_pct is above the last point - extrapolate
                c_time = 0  # there is no must remain connected time - EUT should run indefinitely
                if lots_of_output:
                    ts.log_debug('F_test is higher than LFRTC[n_points]. Ride-through time is %0.3f' % c_time)
            else:
                # pointwise algorithm to find target vars
                for i in xrange(1, lc_n_points):
                    if lots_of_output:
                        ts.log_debug('Grid frequency is %.3f' % (test_freq_pct))
                        ts.log_debug('i = %d' % i)
                        ts.log_debug('test_freq_pct >= freq[i] and test_freq_pct <= freq[i+1]')
                        ts.log_debug('%.3f >= %.3f and %.3f <= %.3f' %
                                     (test_freq_pct, lc_freq[i], test_freq_pct, lc_freq[i+1]))

                    if test_freq_pct >= lc_freq[i] and test_freq_pct <= lc_freq[i+1]: #curve interpolation
                        #Time = Ti + (Ti+1 - Ti)*((test_freq_pct - Vi)/(Vi+1 - Vi))
                        c_time = lc_time[i] + (lc_time[i+1] - lc_time[i])*\
                                              ((test_freq_pct - lc_freq[i])/(lc_freq[i+1] - lc_freq[i]))
                        if lots_of_output:
                            ts.log_debug('Interpolated. Ride-through time is %0.3f' % c_time)
                        break

    return c_time, d_time


def test_run():

    result = script.RESULT_FAIL
    das = None
    wfmtrigger = None
    gsim = None
    pv = None
    inv = None
    filename = None
    disable = None

    try:
        ifc_type = ts.param_value('comm.ifc_type')
        ifc_name = ts.param_value('comm.ifc_name')
        if ifc_type == client.MAPPED:
            ifc_name = ts.param_value('comm.map_name')
        baudrate = ts.param_value('comm.baudrate')
        parity = ts.param_value('comm.parity')
        ipaddr = ts.param_value('comm.ipaddr')
        ipport = ts.param_value('comm.ipport')
        slave_id = ts.param_value('comm.slave_id')

        time_window = ts.param_value('frt.settings.time_window')
        timeout_period = ts.param_value('frt.settings.timeout_period')
        ramp_time = ts.param_value('frt.settings.ramp_time')

        h_n_points = ts.param_value('frt.settings.h_n_points')
        h_curve_num = ts.param_value('frt.settings.h_curve_num')
        h_time = ts.param_value('frt.h_curve.h_time')
        h_freq = ts.param_value('frt.h_curve.h_freq')

        l_n_points = ts.param_value('frt.settings.l_n_points')
        l_curve_num = ts.param_value('frt.settings.l_curve_num')
        l_time = ts.param_value('frt.l_curve.l_time')
        l_freq = ts.param_value('frt.l_curve.l_freq')

        ride_through = ts.param_value('frt.settings.ride_through')

        hc_n_points = ts.param_value('frt.settings.hc_n_points')
        hc_curve_num = ts.param_value('frt.settings.hc_curve_num')
        hc_time = ts.param_value('frt.hc_curve.hc_time')
        hc_freq = ts.param_value('frt.hc_curve.hc_freq')

        lc_n_points = ts.param_value('frt.settings.lc_n_points')
        lc_curve_num = ts.param_value('frt.settings.lc_curve_num')
        lc_time = ts.param_value('frt.lc_curve.lc_time')
        lc_freq = ts.param_value('frt.lc_curve.lc_freq')

        time_msa = ts.param_value('invt.time_msa')
        test_point_offset = ts.param_value('invt.test_point_offset')
        frt_period = ts.param_value('invt.frt_period')
        pretest_delay = ts.param_value('invt.pretest_delay')
        failure_count = ts.param_value('invt.failure_count')
        verification_delay = ts.param_value('invt.verification_delay')
        posttest_delay = ts.param_value('invt.posttest_delay')
        disable = ts.param_value('invt.disable')

        # initialize data acquisition system
        das, wfmtrigger, wfmtrigger_params = das_init()

        # initialize pv simulation
        pv = pvsim.pvsim_init(ts)
        pv.power_on()

        # initialize grid simulation
        gsim = gridsim.gridsim_init(ts)

        #Inverter scan after grid and PV simulation setup so that Modbus registers can be read.
        ts.log('Scanning inverter')
        inv = client.SunSpecClientDevice(ifc_type, slave_id=slave_id, name=ifc_name, baudrate=baudrate, parity=parity,
                                         ipaddr=ipaddr, ipport=ipport)

        ### Find test points ###
        # determine the test points for the HFRT tests (ends near nominal)
        h_f_test_points = [h_freq[h_freq['index_start']]+test_point_offset]
        h_f_test_points.append(h_freq[h_freq['index_start']]-test_point_offset)
        for x in range(h_freq['index_start']+1, h_freq['index_count']):
            h_f_test_points.append(h_freq[x]+test_point_offset)
            h_f_test_points.append(h_freq[x]-test_point_offset)
        h_f_test_points.append(h_freq[h_freq['index_count']]+test_point_offset)
        h_f_test_points.append(h_freq[h_freq['index_count']]-test_point_offset)
        #ts.log_debug(h_f_test_points)

        # determine the test points for the LFRT tests (starts near nominal)
        l_f_test_points = [l_freq[l_freq['index_count']]+test_point_offset]
        l_f_test_points.append(l_freq[l_freq['index_count']]-test_point_offset)
        for x in range(l_freq['index_count']-1, l_freq['index_start'], -1):
            l_f_test_points.append(l_freq[x]+test_point_offset)
            l_f_test_points.append(l_freq[x]-test_point_offset)
        l_f_test_points.append(l_freq[l_freq['index_start']]+test_point_offset)
        l_f_test_points.append(l_freq[l_freq['index_start']]-test_point_offset)
        #ts.log_debug(l_f_test_points)

        f_test_points = h_f_test_points + l_f_test_points
        list(set(f_test_points))  # remove duplicate points
        # ts.log_debug(f_test_points)

        if ride_through == 'Yes':

            # determine the test points for the HFRTC tests (ends near nominal)
            hc_f_test_points = [hc_freq[hc_freq['index_start']]+test_point_offset]
            hc_f_test_points.append(hc_freq[hc_freq['index_start']]-test_point_offset)
            for x in range(hc_freq['index_start']+1, hc_freq['index_count']):
                hc_f_test_points.append(hc_freq[x]+test_point_offset)
                hc_f_test_points.append(hc_freq[x]-test_point_offset)
            hc_f_test_points.append(hc_freq[hc_freq['index_count']]+test_point_offset)
            hc_f_test_points.append(hc_freq[hc_freq['index_count']]-test_point_offset)
            #ts.log_debug(hc_f_test_points)

            # determine the test points for the LFRTC tests (starts near nominal)
            lc_f_test_points = [lc_freq[lc_freq['index_count']]+test_point_offset]
            lc_f_test_points.append(lc_freq[lc_freq['index_count']]-test_point_offset)
            for x in range(lc_freq['index_count']-1, lc_freq['index_start'], -1):
                lc_f_test_points.append(lc_freq[x]+test_point_offset)
                lc_f_test_points.append(lc_freq[x]-test_point_offset)
            lc_f_test_points.append(lc_freq[lc_freq['index_start']]+test_point_offset)
            lc_f_test_points.append(lc_freq[lc_freq['index_start']]-test_point_offset)
            #ts.log_debug(lc_f_test_points)

            f_test_points = f_test_points + hc_f_test_points + lc_f_test_points

        f_test_points = list(set(f_test_points))  # remove duplicate points
        f_test_points.sort()

        # remove negative test points
        for x in range(len(f_test_points)-1, 0, -1):
            if f_test_points[x] < 0:
                del f_test_points[x]
        ts.log('Voltage Test points are %s' % f_test_points)

        ######## Begin Test ########
        #if pretest_delay > 0:
        #    ts.log('Waiting for pre-test delay of %d seconds' % pretest_delay)
        #    ts.sleep(pretest_delay)

        # note: timing parameters are not tested currently by this script - would need to wrap the assignment into loop
        # below to determine response times and timeout periods

        ts.log('Writing the frt curves to the EUT')
        '''
        inverter.set_frt_trip_high(inv, h_time=h_time, h_freq=h_freq, h_n_points=h_n_points, h_curve_num=h_curve_num,
                         time_window=time_window, timeout_period=timeout_period, ramp_time=ramp_time,
                         enable=1, wfmtrigger=wfmtrigger)

        inverter.set_frt_trip_high(inv, l_time=l_time, l_freq=l_freq, l_n_points=l_n_points, l_curve_num=l_curve_num,
                         time_window=time_window, timeout_period=timeout_period, ramp_time=ramp_time,
                         enable=1, wfmtrigger=wfmtrigger)

        if ride_through == 'Yes':
            inverter.set_frt_stay_connected_high(inv, hc_time=hc_time, hc_freq=hc_freq, hc_n_points=hc_n_points,
                                                 hc_curve_num=hc_curve_num, time_window=time_window,
                                                 timeout_period=timeout_period, ramp_time=ramp_time,
                                                 enable=1, wfmtrigger=wfmtrigger)

            inverter.set_frt_stay_connected_low(inv, lc_time=lc_time, lc_freq=lc_freq, lc_n_points=lc_n_points,
                                                 lc_curve_num=lc_curve_num, time_window=time_window,
                                                 timeout_period=timeout_period, ramp_time=ramp_time,
                                                 enable=1, wfmtrigger=wfmtrigger)
        '''

        failures = 0  # failure counter
        for i in xrange(0, len(f_test_points)):
            # determine the expected behavior
            c_time, d_time = predict_frt_response_time(f_test_points[i], ride_through,
                                                       h_time=h_time, h_freq=h_freq, h_n_points=h_n_points,
                                                       l_time=l_time, l_freq=l_freq, l_n_points=l_n_points,
                                                       hc_time=hc_time, hc_freq=hc_freq, hc_n_points=hc_n_points,
                                                       lc_time=lc_time, lc_freq=lc_freq, lc_n_points=lc_n_points)

            ts.log('Test %i, test frequency = %0.3f %%Fnom. Expected Ride-Through Time = %0.3f sec. '
                   'Expected Trip Time = %0.3f sec.' % (i+1, f_test_points[i], c_time, d_time))

            if d_time == 0.:  # test doesn't have a trip boundary. Set d_time to max time plus verification time
                max_time = max(l_time, lc_time, h_time, hc_time)
                ts.log_debug('max_time: %s, max(max_time): %s' % (max_time, max(max_time)))
                d_time = max_time + verification_delay

            ### Make sure the EUT is on and operating
            if inverter.get_conn_state(inv) and inverter.get_power_norm(inv) < 0.05:
                ts.log_warning('EUT not operating! Checking grid simulator operations.')

                # if the inverter is off it's probably because the grid simulator is misconfigured.
                if gsim:
                    gsim.profile_stop()  #abort the profile
                    ts.log('grid nominal frequency: %s' % gsim.f_nom())
                    gsim.freq(gsim.f_nom())  # return simulator to nominal frequency

                ts.log('Waiting up to %d seconds for EUT to begin power export.' % (verification_delay+pretest_delay))
                if verify_initial_conn_state(inv, state=inverter.CONN_CONNECT,
                                             time_period=verification_delay+pretest_delay, das=das) is False:
                        ts.log_error('Inverter unable to be set to connected state.')
                        raise script.ScriptFail()

            ### Arm the data acquisition system for waveform capture
            if das is not None:
                das_time = inverter.get_time(das=das)
                while das_time == inverter.get_time(das=das):
                    ts.log('Monitoring the data stream to ensure the das is prepared for a waveform capture. '
                           'DAS time: %s' % inverter.get_time(das=das))
                    ts.sleep(1)

                ts.log('Configuring the data capture for the following channels: %s' %
                       wfmtrigger_params.get('trigacqchannels'))
                ts.log('Configuring the %s waveform trigger for %s = %0.3f' %
                       (wfmtrigger_params.get('trigcondition'), wfmtrigger_params.get('trigchannel'),
                        float(wfmtrigger_params.get('trigval'))))
                # ts.log_debug('wfmtrigger_params = %s' % wfmtrigger_params)
                wfmtrigger.trigger(wfmtrigger_params=wfmtrigger_params)

                ts.log('Data acquisition preparing for waveform capture. Waiting for pre-test delay of %d seconds'
                       % pretest_delay)
                starttime = time.time()
                while pretest_delay >= (time.time()-starttime):
                    totaltime = time.time()-starttime
                    ts.log('Waiting %0.3f more seconds.' % (pretest_delay-totaltime))
                    ts.sleep(1.0 - totaltime % 1)

            else:  # there is no data acquisition system
                ts.log_warning('No data acquisition system configured.')
                if ts.confirm('Please configure the trigger to capture the ride-through and enable it.') is False:
                    raise script.ScriptFail('Aborted frt!')

            if f_test_points[i] < 100.:
                frt_test_freq_pct = f_test_points[i]+test_point_offset
            else:
                frt_test_freq_pct = f_test_points[i]-test_point_offset

            ### Execute the frequency change
            if gsim is not None:
                ### create transient event in grid simulator
                if d_time == 0 and c_time == 0:  # near nominal
                    test_duration = max(h_time, l_time, lc_time, hc_time)
                    # be sure to catch end of transient with at least a 3 cycle window
                    wfmtrigger_params['posttrig'] = test_duration + max(verification_delay, 0.0166*3)
                else:
                    test_duration = max(c_time, d_time)
                    # be sure to catch end of transient with at least a 3 cycle window
                    wfmtrigger_params['posttrig'] = test_duration + max(verification_delay, 0.0166*3)
                ts.log('The post trigger time has been adjusted to %s for this ride through test to capture '
                       'the EUT dynamics' % wfmtrigger_params.get('posttrig'))

                # Use the profile so the timing for the event is accurate and there is a trigger from the simulator
                gsim.profile_load(profile_name='Transient_Step', v_step=100., f_step=frt_test_freq_pct,
                                  t_step=test_duration)
                ts.log('Profile is loaded in simulator. Running the grid simulator profile.')
                gsim.profile_start()
            else:
                ts.log('Must set the grid simulator frequency to the ride-through frequency.')
                if ts.confirm('Set the grid simulator to the test frequency: %0.3f %%Fnom.' %
                              frt_test_freq_pct) is False:
                    raise script.ScriptFail('Aborted frt!')

            ### Wait for DAS to capture transient event
            start_time = time.time()
            elapsed_time = 0.
            while elapsed_time <= wfmtrigger_params['posttrig']:
                ts.log('Waiting for waveform capture to complete. Total time remaining %0.3f seconds' %
                       (wfmtrigger_params['posttrig']-elapsed_time))
                ts.sleep(0.93)
                elapsed_time = time.time() - start_time

            ### Screen waveform data and save in the results file
            if das is not None:

                ts.log('Waiting post test delay of %0.2f seconds before processing the data file.' % posttest_delay)
                ts.sleep(posttest_delay)

                # get data from waveform saved on the hard drive
                # (this function could use a little help to make it more robust...)
                wfmname = wfmtrigger.getfilename()
                ts.log('Analyzing waveform data in file "%s".' % wfmname)

                if ts.param_value('wfm.trigchannel').count(',') == 3:
                    wfmtime, ac_voltage, ac_current = wfmtrigger.read_file(wfmname)

                    # calculate the time the EUT rode through the frequency event
                    # ride_through_time == 0 means no trip/ceassation
                    ride_through_time = calc_ride_through_duration(wfmtime, ac_current, ac_voltage=ac_voltage)

                else:  # if there are more than 3 channels being collected, assume the first 4 the following:
                    wfmtime, ac_voltage, ac_current, grid_trig = wfmtrigger.read_file(wfmname)

                    # calculate the time the EUT rode through the voltage event
                    # ride_through_time == 0 means no trip/ceassation
                    ride_through_time = calc_ride_through_duration(wfmtime, ac_current, grid_trig=grid_trig)

                if ride_through_time == 0:
                    ts.log('The EUT did not trip or momentarily cease to energize.')
                else:
                    ts.log('The ride-through duration was %0.3f.' % ride_through_time)

                if ride_through_time - time_msa < c_time:
                    ts.log_warning('The ride-through duration of %0.3f minus the manufacturers stated '
                                   'accuracy of %0.3f is less '
                                   'than the ride-through time of %0.3f.' % (ride_through_time, time_msa, c_time))
                    failures += 1
                    ts.log_warning('The number of failures is %i.' % failures)
                elif ride_through_time + time_msa > d_time:
                    ts.log_warning('The ride-through duration of %0.3f plus the manufacturers stated '
                                   'accuracy of %0.3f is more '
                                   'than the must disconnect time of %0.3f.' % (ride_through_time, time_msa, c_time))
                    failures += 1
                    ts.log_warning('The number of failures is %i.' % failures)

                # save file to results
                results_dir = os.path.dirname(__file__)[:-7] + 'Results' + os.path.sep
                ts.log('Moving waveform "%s" to results folder: %s.' % (wfmname, results_dir))
                wfmtrigger.move_file_to_results(wfmname=wfmname, results_dir=results_dir, delete_original='No')

            else:
                ts.log('Ride-through test complete. Please analyze the data to assign pass/fail result.')

            if failures >= failure_count:
                raise script.ScriptFail()

        ts.log('Waiting the post-test duration %i.' % posttest_delay)
        ts.sleep(posttest_delay)

        result = script.RESULT_PASS

    except script.ScriptFail, e:
        reason = str(e)
        if reason:
            ts.log_error(reason)
    finally:
        if pv:
            pv.close()
        if disable == 'yes' and inv is not None:
            '''
            inv.hfrtd.ModEna = 0
            inv.hfrtc.ModEna = 0
            inv.lfrtd.ModEna = 0
            inv.lfrtc.ModEna = 0

            inv.hfrtd.write()
            inv.hfrtc.write()
            inv.lfrtd.write()
            inv.lfrtc.write()
            '''

        if gsim:
            gsim.profile_stop()  #abort the profile
            gsim.freq(gsim.f_nom())  #return simulator to nominal frequency

    return result


def run(test_script):
    try:
        global ts
        ts = test_script
        rc = 0
        result = script.RESULT_COMPLETE

        ts.log_debug('')
        ts.log_debug('**************  Starting %s  **************' % (ts.config_name()))
        ts.log_debug('Script: %s %s' % (ts.name, ts.info.version))
        ts.log_active_params()

        result = test_run()

        ts.result(result)
        if result == script.RESULT_FAIL:
            rc = 1

    except Exception, e:
        ts.log_error('Test script exception: %s' % traceback.format_exc())
        rc = 1

    sys.exit(rc)

info = script.ScriptInfo(name=os.path.basename(__file__), run=run, version='1.0.3')

# EUT communication parameters
info.param_group('comm', label='EUT Communication Parameters', glob=True)
info.param('comm.ifc_type', label='Interface Type', default=client.RTU, values=[client.RTU, client.TCP, client.MAPPED])
# RTU parameters
info.param('comm.ifc_name', label='Interface Name', default='COM3',  active='comm.ifc_type', active_value=[client.RTU],
           desc='Select the communication port from the UMS computer to the EUT.')
info.param('comm.baudrate', label='Baud Rate', default=9600, values=[9600, 19200], active='comm.ifc_type',
           active_value=[client.RTU])
info.param('comm.parity', label='Parity', default='N', values=['N', 'E'], active='comm.ifc_type',
           active_value=[client.RTU])
# TCP parameters
info.param('comm.ipaddr', label='IP Address', default='192.168.0.170', active='comm.ifc_type',
           active_value=[client.TCP])
info.param('comm.ipport', label='IP Port', default=502, active='comm.ifc_type', active_value=[client.TCP])
# Mapped parameters
info.param('comm.map_name', label='Map File', default='mbmap.xml',active='comm.ifc_type',
           active_value=[client.MAPPED], ptype=script.PTYPE_FILE)
info.param('comm.slave_id', label='Slave Id', default=1)

# frt settings
info.param_group('frt', label='FRT Configuration')
info.param_group('frt.settings', label='frt Settings')
info.param('frt.settings.ramp_time', label='Ramp Time (seconds)', default=0,
           desc='Ramp time in seconds.'
                'A value of 0 indicates function should not ramp, but step.')
info.param('frt.settings.time_window', label='Time Window (seconds)', default=0,
           desc='Time window for FRT change. Randomized time window for operation.'
                'A value of 0 indicates FRT executes immediately.')
info.param('frt.settings.timeout_period', label='Timeout Period (seconds)', default=0,
           desc='Time period before function reverts to default state. '
                'A value of 0 indicates function should not revert.')

info.param('frt.settings.ride_through', label='Does the test have ride-through curves?', default='Yes',
           values=['Yes', 'No'])

# Define points for HFRT must trip curves
info.param('frt.settings.h_curve_num', label='HFRT Curve number', default=1, values=[1,2,3,4])
info.param('frt.settings.h_n_points', label='Number of (t, F) pairs (2-10)', default=4,
           values=[2,3,4,5,6,7,8,9,10])
info.param_group('frt.h_curve', label='HFRT Curve Trip Points', index_count='frt.settings.h_n_points', index_start=1,
                 desc='Curve is assumed to be vertical from 1st point and horizontal from last point.')
info.param('frt.h_curve.h_time', label='Time (sec)', default=0., desc='Time curve point')
info.param('frt.h_curve.h_freq', label='Freq (%Fnom)', default=100., desc='Freq curve point')

# Define points for LFRT must trip curves
info.param('frt.settings.l_curve_num', label='LFRT Curve number', default=1, values=[1,2,3,4])
info.param('frt.settings.l_n_points', label='Number of (t, F) pairs (2-10)', default=4,
           values=[2,3,4,5,6,7,8,9,10])
info.param_group('frt.l_curve', label='LFRT Curve Trip Points', index_count='frt.settings.l_n_points', index_start=1,
                 desc='Curve is assumed to be vertical from 1st point and horizontal from last point.')
info.param('frt.l_curve.l_time', label='Time (sec)', default=0., desc='Time curve point')
info.param('frt.l_curve.l_freq', label='Freq (%Fnom)', default=100., desc='Freq curve point')

# Define points for HFRT must remain connected curves
info.param('frt.settings.hc_curve_num', label='HFRT must remain connected curve number',
           active='frt.settings.ride_through', active_value=['Yes'], default=1, values=[1,2,3,4])
info.param('frt.settings.hc_n_points', label='Number of (t, F) pairs (2-10)',
           active='frt.settings.ride_through', active_value=['Yes'], default=4, values=[2,3,4,5,6,7,8,9,10])
info.param_group('frt.hc_curve', label='HFRT Curve Must Remain Connected Points',
                 active='frt.settings.ride_through', active_value=['Yes'],
                 index_count='frt.settings.hc_n_points', index_start=1,
                 desc='Curve is assumed to be vertical from 1st point and horizontal from last point.')
info.param('frt.hc_curve.hc_time', label='Time (sec)',
           active='frt.settings.ride_through', active_value=['Yes'], default=0., desc='Time curve point')
info.param('frt.hc_curve.hc_freq', label='Freq (%Fnom)',
           active='frt.settings.ride_through', active_value=['Yes'], default=100., desc='Freq curve point')

# Define points for LFRT must remain connected curves
info.param('frt.settings.lc_curve_num', label='LFRT must remain connected curve number)',
           active='frt.settings.ride_through', active_value=['Yes'], default=1, values=[1,2,3,4])
info.param('frt.settings.lc_n_points', label='Number of (t, F) pairs (2-10)',
           active='frt.settings.ride_through', active_value=['Yes'], default=4, values=[2,3,4,5,6,7,8,9,10])
info.param_group('frt.lc_curve', label='LFRT Curve Must Remain Connected Points',
                 active='frt.settings.ride_through', active_value=['Yes'],
                 index_count='frt.settings.lc_n_points', index_start=1,
                 desc='Curve is assumed to be vertical from 1st point and horizontal from last point.')
info.param('frt.lc_curve.lc_time', label='Time (sec)',
           active='frt.settings.ride_through', active_value=['Yes'], default=0., desc='Time curve point')
info.param('frt.lc_curve.lc_freq', label='Freq (%Fnom)',
           active='frt.settings.ride_through', active_value=['Yes'], default=100., desc='Freq curve point')

# Timing parameters
info.param_group('invt', label='FRT Timing and Pass/Fail Parameters')
info.param('invt.pretest_delay', label='Pre-Test Delay (seconds)', default=10,
           desc='Delay before beginning the test - Set to time required to arm trigger.')
info.param('invt.time_msa', label='Time Pass/Fail Screen', default=0.1,
           desc='+/- time for Pass/Fail Screen (i.e., "0.1" = +/- 0.1 seconds)')
info.param('invt.test_point_offset', label='Test Point Offset (%V)', default=1.,
           desc='Offset from the F points that FRT will be verified, e.g., Foffset = 0.01 and (t,F) = (0.16 s, 97%);'
           ' then test points will be 96 and 98 %F')
info.param('invt.frt_period', label='Duration beyond must trip curve for analysis (seconds)', default=5,
           desc='Amount of time that the frt is analyzed.')
info.param('invt.verification_delay', label='Verification Delay (seconds)', default=5,
           desc='Wait time allowance before assigning failure for the time parameters.')
info.param('invt.posttest_delay', label='Post-Test Delay (seconds)', default=10,
           desc='Delay after finishing the test.')
info.param('invt.failure_count', label='Setpoint Failure Count', default=60,
           desc='Number of consecutive failures (power excursions beyond target vars) which does not '
                'produce a script fail. This accounts for EUT settling time.')
info.param('invt.disable', label='Disable frt function at end of test?', default='No', values=['Yes', 'No'])

# Grid simulator
gridsim.params(info)

# PV simulator
pvsim.params(info)

# todo: must add ability to control multiple channels at the same time
# todo: also nice to control the two racks at the same time for multiple inverter tests

# DAS
info.param_group('datatrig', label='Data Acquisition and Triggering', glob=True)
info.param('datatrig.dsm_method', label='Data Acquisition Method', default='Disabled - Data from EUT',
           values=['Disabled - Data from EUT', 'Sandia LabView DSM'],
           desc='Each lab will have different data acquisition methods. Sandia passes the data from the DAQ '
                'to python by writing the values locally or collecting them over the local TCP network.')
info.param_group('wfm', label='Waveform Capture Parameters',
           active='datatrig.dsm_method', active_value=['Sandia LabView DSM'],
           desc='Sandia technique for capturing waveforms using the DSM.', glob=True)
info.param('wfm.trigsamplingrate', label='Waveform Sampling Rate (Hz)', default='24.0e3')
info.param('wfm.pretrig', label='Pretrigger Time (sec)', default='166.667e-3')
info.param('wfm.posttrig', label='Posttrigger Time (sec)', default='5.000')
info.param('wfm.trigval', label='Trigger Value/Level', default='3.000')
info.param('wfm.trighyswindow', label='Trigger Window', default='10.000e-3')
info.param('wfm.trigtimeout', label='Trigger Timeout Time (sec)', default='30')
info.param('wfm.trigcondition', label='Trigger Condition', default='Falling Edge',
           values=['Falling Edge', 'Rising Edge', 'Above Level', 'Below Level',
                   'When Inside Window', 'When Outside Window'])
info.param('wfm.trigchannel', label='Trigger Channel', default='Ametek_Trigger',
           values=['AC_Voltage_10', 'DC_Voltage_10', 'Ametek_Trigger'],
           desc='Each lab will need a different triggering method. Sandia uses the Ametek trigger')
info.param('wfm.trigacqchannels', label='Channels to Capture', default='AC_Current_10, AC_Voltage_10, Ametek_Trigger')

info.logo('sunspec.gif')

def script_info():
    return info


if __name__ == "__main__":


    # stand alone invocation
    config_file = None
    if len(sys.argv) > 1:
        config_file = sys.argv[1]

    test_script = script.Script(info=script_info(), config_file=config_file)

    run(test_script)



