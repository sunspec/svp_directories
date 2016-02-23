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

# Test script for IEC TR 61850-90-7 FW21
# This test requires the following SunSpec Alliance Modbus models: inverter, settings, nameplate, freq_watt_param

#!C:\Python27\python.exe

import sys
import os
import traceback
import time
import inverter
import pvsim

import gridsim
import das

import sunspec.core.client as client
import script

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

# returns: current ac freq as a percentage of nominal
def get_ac_freq_pct(inv, freq_ref = 60., das=None):
    try:

        #only use the das (data acquisition system) if it is available
        if das:
            das.read()
            gridFraw = das.ac_freq
        # without the das use the EUT to report the power level
        else:
            inv.inverter.read()
            gridFraw = float(inv.inverter.Hz)

        inv.settings.read()
        Freq_nom = float(freq_ref)

        return (gridFraw/Freq_nom)*100.0

    except Exception, e:
        raise script.ScriptFail('Unable to get ac freq from das or EUT: %s' % str(e))


# returns: target power and pass/fail limits - excluding hysteresis or ramp rates.
def power_pass_fail_band(inv, fw_mode='FW21 (FW parameters)', freq=None, W=None, n_points=3,
                         power_range=5, WGra = 65., HzStr=0.2, freq_ref=60, das=None):
    pow_targ = None
    pow_upper = None
    pow_lower = None

    freq_now = inverter.get_freq(inv, das=das)
    f_pct = (freq_now/freq_ref)*100.

    if fw_mode == 'FW21 (FW parameters)':
        # convert parameterized FW to pointwise parameters

        freq = {
            1: 100.,
            2: 100. + (HzStr / freq_ref) * 100.,
            3: 100. + ((HzStr + 100./WGra) * (100. / freq_ref)),
            'index_start': 1,
            'index_count': 3
        }

        W = {
            1: 100.,
            2: 100.,
            3: 0.,
            'index_start': 1,
            'index_count': 3
        }

    #Check to be sure the freq points are monotonically increasing.
    for i in xrange(1, n_points-1):
        if freq[i] > freq[i+1]:
            ts.log_error('Voltages are not monotonically increasing in FW curve.')
        break

    lots_of_output = True  #Flag to turn on data dumps to help debugging

    if f_pct <= freq[1]:  # Fgrid is below the 1st point - extrapolate
        pow_targ = W[1]  # units of % nameplate watts
        pow_upper = pow_targ + power_range  # units of % nameplate watts
        pow_lower = pow_targ - power_range  # units of % nameplate watts
        if lots_of_output:
            ts.log_debug('Low, frequency is %0.3f and freq point 1 is %0.3f' % (f_pct, freq[1]))
            ts.log_debug('pow_targ, pow_upper, pow_lower')
            ts.log_debug('%.3f, %.3f, %.3f' % (pow_targ, pow_upper, pow_lower))
    elif f_pct >= freq[n_points]: #Fgrid is above the last point - extrapolate
        pow_targ = W[n_points]  # units of vars
        pow_upper = pow_targ + power_range  # units of % nameplate watts
        pow_lower = pow_targ - power_range  # units of % nameplate watts
        if lots_of_output:
            ts.log_debug('High, frequency is %0.3f and freq point n is %0.3f' % (f_pct, freq[n_points]))
            ts.log_debug('pow_targ, pow_upper, pow_lower')
            ts.log_debug('%.3f, %.3f, %.3f' % (pow_targ, pow_upper, pow_lower))
    else:
        # pointwise algorithm to find target power
        for i in xrange(1, n_points):
            if lots_of_output:
                ts.log_debug('Grid freq is %.3f' % (f_pct))
                ts.log_debug('i = %d' % i)
                ts.log_debug('gridF >= freq[i] and gridF <= freq[i+1]')
                ts.log_debug('%.3f >= %.3f and %.3f <= %.3f' % (f_pct, freq[i], f_pct, freq[i+1]))

            if f_pct >= freq[i] and f_pct <= freq[i+1]:  # curve interpolation
                # pow_targ = Pi + (Pi+1 - Pi)*((f_pct - Fi)/(Fi+1 - Fi))
                pow_targ = (W[i]+(W[i+1]-W[i])*((f_pct-freq[i])/(freq[i+1]-freq[i])))
                pow_upper = pow_targ + power_range  # units of % nameplate watts
                pow_lower = pow_targ - power_range  # units of % nameplate watts
                if lots_of_output:
                    ts.log_debug('Interpolated')
                    ts.log_debug('pow_targ, pow_upper, pow_lower')
                    ts.log_debug('%.3f, %.3f, %.3f' % (pow_targ, pow_upper, pow_lower))
                break

    return pow_targ, pow_upper, pow_lower

def test_run():

    result = script.RESULT_FAIL
    data = None
    trigger = None
    grid = None
    pv = None
    inv = None
    freq = {}
    W = {}
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

        freq_ref = ts.param_value('fw.settings.freq_ref')  # is there a sunspec parameter for this?

        fw_mode = ts.param_value('fw.settings.fw_mode')
        #fw_mode == 'FW21 (FW parameters)':
        WGra = ts.param_value('fw.settings.WGra')
        HzStr = ts.param_value('fw.settings.HzStr')
        HzStop = ts.param_value('fw.settings.HzStop')
        HysEna = ts.param_value('fw.settings.HysEna')
        HzStopWGra = ts.param_value('fw.settings.HzStopWGra')

        #'FW22 (pointwise FW)'
        time_window = ts.param_value('fw.settings.time_window')
        timeout_period = ts.param_value('fw.settings.timeout_period')
        ramp_time = ts.param_value('fw.settings.ramp_time')
        recovery_ramp_rate = ts.param_value('fw.settings.recovery_ramp_rate')
        curve_num = ts.param_value('fw.settings.curve_num')
        n_points = ts.param_value('fw.settings.n_points')
        freq = ts.param_value('fw.curve.freq')
        W = ts.param_value('fw.curve.W')

        pretest_delay = ts.param_value('invt.pretest_delay')
        power_range = ts.param_value('invt.power_range')
        setpoint_failure_count = ts.param_value('invt.setpoint_failure_count')
        setpoint_period = ts.param_value('invt.setpoint_period')
        verification_delay = ts.param_value('invt.verification_delay')
        posttest_delay = ts.param_value('invt.posttest_delay')
        disable = ts.param_value('invt.disable')

        # initialize data acquisition system
        daq = das.das_init(ts)
        data = daq.data_init()
        trigger = daq.trigger_init()

        # initialize pv simulation
        pv = pvsim.pvsim_init(ts)
        pv.power_on()

        # initialize grid simulation
        grid = gridsim.gridsim_init(ts)
        grid.profile_load(ts.param_value('profile.profile_name'))

        # Sandia Test Protocol: Communication is established between the Utility Management System Simulator and EUT
        # EUT scan after grid and PV simulation setup so that Modbus registers can be read.
        ts.log('Scanning inverter')
        inv = client.SunSpecClientDevice(ifc_type, slave_id=slave_id, name=ifc_name, baudrate=baudrate, parity=parity,
                                         ipaddr=ipaddr, ipport=ipport)

        # Make sure the EUT is on and operating
        ts.log('Verifying EUT is in connected state. Waiting up to %d seconds for EUT to begin power export.'
               % (verification_delay+pretest_delay))
        if verify_initial_conn_state(inv, state=inverter.CONN_CONNECT,
                                     time_period=verification_delay+pretest_delay, das=data) is False:
                ts.log_error('Inverter unable to be set to connected state.')
                raise script.ScriptFail()

        ######## Begin Test ########
        if pretest_delay > 0:
            ts.log('Waiting for pre-test delay of %d seconds' % pretest_delay)
            ts.sleep(pretest_delay)

        # Request status and display power
        freq_original = inverter.get_freq(inv, das=data)
        power_original = inverter.get_power(inv, das=data)
        ts.log('Current grid frequency is %.3f Hz and EUT power is %.3f W' % (freq_original, power_original))

        ### todo: open the ride-through settings at this point to ensure the EUT doesn't trip during freq profile.

        # ts.log_debug('%s, %s, %s, %s, %s' % (WGra, HzStr, HzStop, HysEna, HzStopWGra))

        if HzStopWGra == 0:
            ts.log_warning('Setting HzStopWGra to 10000 because of the limits of the EUT. This is the fastest available option.')

        inverter.set_freq_watt(inv, fw_mode=fw_mode, freq=freq, W=W, n_points=n_points, curve_num=curve_num,
                               timeout_period=timeout_period, ramp_time=ramp_time,
                               recovery_ramp_rate=recovery_ramp_rate,
                               time_window=time_window, WGra=WGra, HzStr=HzStr, HzStop=HzStop, HysEna=HysEna,
                               HzStopWGra=HzStopWGra, enable=1, trigger=trigger)

        # Run the grid simulator profile immediately after setting the freq-watt functions and triggering
        if grid is not None:
            ts.log('Running frequency profile.')
            grid.profile_start()

        # power_pass_fail_band only determines the point on the curve. It does not account for hysteresis.
        pow_targ, pow_upper, pow_lower = power_pass_fail_band(inv, fw_mode=fw_mode, freq=freq, W=W, n_points=n_points,
                                                              power_range=power_range, WGra=WGra,
                                                              HzStr=HzStr, freq_ref=freq_ref, das=das)

        ts.log('Target power: %.3f. Pass limits for screening: upper = %.3f  lower = %.3f' %
               (pow_targ, pow_upper, pow_lower))

        # Log FW parameters and calculate test_duration
        test_duration = setpoint_period + verification_delay
        ts.log('Waiting up to %d seconds for power change with a verification period of %d seconds.' %
               (ramp_time + time_window, verification_delay))

        ts.log_debug('dc_voltage = %0.3f' % data.dc_voltage)
        ts.log_debug('dc_current = %0.3f' % data.dc_current)
        ts.log_debug('ac_voltage = %0.3f' % data.ac_voltage)
        ts.log_debug('ac_current = %0.3f' % data.ac_current)
        ts.log_debug('dc_watts = %0.3f' % data.dc_watts)
        ts.log_debug('Power = %0.3f' % data.ac_watts)
        ts.log_debug('ac_freq = %0.3f' % data.ac_freq)
        ts.log_debug('trigger = %0.3f' % data.trigger)

        start_time = time.time()
        elapsed_time = 0

        # Initialize consecutive failure count to not script fail on transient behavior
        failures = 0
        revert_complete = False

        in_hysteresis = False  # flag for when the FW is in hysteresis
        inv.nameplate.read()
        max_W = float(inv.nameplate.WRtg)

        if time_window != 0:
            window_complete = False
        else:
            window_complete = True
        time_window_execution = time_window

        while elapsed_time <= test_duration:
            ts.sleep(0.93)
            elapsed_time = time.time()-start_time

            power_pct = (inverter.get_power(inv, das=data) / max_W) * 100.

            #determine if function is in hysteresis
            if fw_mode == 'FW21 (FW parameters)' and HysEna == 'Yes':
                freq_new = inverter.get_freq(inv, das=data)

                if freq_new < freq_original and freq_original > HzStr:
                    if not in_hysteresis:
                        in_hysteresis = True
                        hys_power = power_pct
                        ts.log('Entered the Hysteresis band with power limit = %0.3f%%' % hys_power)
                    else:
                        ts.log('Still in the Hysteresis band with power limited to %0.3f%%' % hys_power)
                elif in_hysteresis and freq_new < HzStop:
                    in_hysteresis = False  # No longer in hysteresis band
                    ts.log('Exited hysteresis band. Returning to FW curve power at HzStopWGra = %0.3f %%nameplate/min'
                           % HzStopWGra)

                freq_original = freq_new

            if window_complete is True and revert_complete is False:
                if in_hysteresis is False:
                    # pow_targ, pow_upper, pow_lower are in percentages of nameplate power
                    pow_targ, pow_upper, pow_lower = power_pass_fail_band(inv, fw_mode=fw_mode, freq=freq, W=W,
                                                                          n_points=n_points, power_range=power_range,
                                                                          WGra=WGra, HzStr=HzStr,
                                                                          freq_ref=freq_ref, das=data)
                else:  # in hysteresis band
                    pow_targ = hys_power
                    pow_upper = pow_targ + power_range  # units of % nameplate watts
                    pow_lower = pow_targ - power_range  # units of % nameplate watts
            else:
                # Before the time window executes and after timeout period, the upper and lower pass/fail bounds for EUT
                # use the default power state of 100% Wmax
                pow_targ = 100.
                pow_upper = pow_targ + power_range  # units of % nameplate watts
                pow_lower = pow_targ - power_range  # units of % nameplate watts

            ts.log('W Target = %.3f [%.3f to %.3f], W = %.3f (Error = %0.3f%%), Time: %0.3f seconds.' %
                   (pow_targ, pow_lower, pow_upper, power_pct, (power_pct - pow_targ), elapsed_time))

            if revert_complete is False:  #if testing FW21, timing parameters are all 0, so they don't affect results

                # Check when the EUT is in range for the first time
                if window_complete is False and \
                        inverter.get_active_control_status(inv, inverter.STACTCTL_FREQ_WATT_PARAM):
                    window_complete = True
                    time_window_execution = elapsed_time
                    ts.log('Randomization window occurred at %0.3f seconds, current power %.3f.' %
                           (time_window_execution, power_pct))

                # Check for timeout period (reversion)
                if window_complete and timeout_period != 0:

                    if not inverter.get_active_control_status(inv, inverter.STACTCTL_FREQ_WATT_PARAM): #reverted
                        revert_complete = True
                        ts.log('Reversion occurred at timeout period = %0.3f seconds, current power %.3f.'
                               % (elapsed_time, power_pct))

                    # Did timeout_period fail?  If so, end the test here.
                    # Note: there's a final timeout_period check outside the while loop.
                    elif elapsed_time >= timeout_period+min(time_window,time_window_execution)+verification_delay:
                        ts.log_error('Inverter did not revert after %0.3f seconds.' % elapsed_time)
                        raise script.ScriptFail()

                # if power out of range
                if power_pct < pow_lower or power_pct > pow_upper:
                    ts.log_debug('Power %0.3f, Pow Lower = %0.3f, Pow Upper = %0.3f.' % (power_pct, pow_lower, pow_upper))
                    # There are three acceptable sources of noncompliance. If the randomization window hasn't occurred,
                    # the reversion (timeout) occurred, or it is ramping to the target vars
                    if window_complete is False: #time window
                        ts.log('Randomization window still in effect after %0.3f seconds.' % (time.time()-start_time))
                    elif elapsed_time > min(time_window,time_window_execution)+ramp_time:
                        # Noncompliance is not from time period, time window, or ramp rate
                        # Count this as a failure
                        failures += 1
                        if failures >= setpoint_failure_count:
                            ts.log_error('Inverter exceeded var setpoint + buffer after %0.3f seconds. '
                                         'Fail count = %d.' % (elapsed_time,failures))
                            raise script.ScriptFail()
                        else:
                            ts.log_warning('Inverter exceeded var setpoint + buffer after %0.3f seconds. '
                                           'Fail count = %d.' % (elapsed_time,failures))
                    else:
                        ts.log_warning('EUT has not reached the target reactive power because it is ramping.')
                else:
                    failures = 0

        # Additional timeout check to determine if the timeout_period occurred during the test. This is necessary
        # in cases where the verification_delay is not set sufficiently long.
        if timeout_period != 0 and inverter.get_active_control_status(inv, inverter.STACTCTL_VOLT_VAR):
            ts.log_error('Inverter did not revert by the end of the test duration. Elapsed time = %0.3f seconds.  '
                         'Increase the verification period if the timeout period is greater than the elapsed time.'
                         % (elapsed_time))
            raise script.ScriptFail()

        if posttest_delay > 0:
            ts.log('Waiting for post-test delay of %d seconds' % posttest_delay)
            ts.sleep(posttest_delay)

        result = script.RESULT_PASS

    except script.ScriptFail, e:
        reason = str(e)
        if reason:
            ts.log_error(reason)
    finally:
        if trigger:
            trigger.off()
        if pv:
            pv.close()
        if disable == 'yes' and inv is not None:
            inv.freq_watt_param.ModEna = 0
            inv.freq_watt_param.write()

    return result

def run(test_script):

    try:
        global ts
        ts= test_script
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


info.param_group('fw', label='FW Configuration')
info.param_group('fw.settings', label='FW Settings')
info.param('fw.settings.fw_mode', label='Freq-Watt Mode', default='FW21 (FW parameters)',
           values=['FW21 (FW parameters)', 'FW22 (pointwise FW)'],
           desc='Parameterized FW curve or pointwise linear FW curve?')
info.param('fw.settings.freq_ref', label='Nominal Grid Frequency (Hz)', default=60.)

# Define points for FW21
info.param('fw.settings.WGra', label='Ramp Rate (%nameplate power/Hz)', default=65.,
           active='fw.settings.fw_mode',  active_value='FW21 (FW parameters)',
           desc='slope of the reduction in the maximum allowed watts output as a function '
                'of frequency (units of % max power/ Hz)')
info.param('fw.settings.HzStr', label='FW Start Freq Above Nominal (delta Hz)', default=0.2,
           active='fw.settings.fw_mode',  active_value='FW21 (FW parameters)',
           desc='Frequency deviation from fnom at which power reduction occurs.')
info.param('fw.settings.HysEna', label='Hysteresis Enabled', default='Yes', values=['Yes', 'No'],
           active='fw.settings.fw_mode',  active_value='FW21 (FW parameters)')
info.param('fw.settings.HzStop', label='FW Stop Freq Above Nominal (delta Hz)', default=0.1,
           active='fw.settings.HysEna',  active_value='Yes',
           desc='frequency deviation from nominal frequency (ECPNomHz) at which curtailed power output '
                'returns to normal and the cap on the power level value is removed.')
info.param('fw.settings.HzStopWGra', label='Recovery Ramp Rate (%nameplate power/min)', default=10000.,
           active='fw.settings.fw_mode',  active_value='FW21 (FW parameters)',
           desc='Maximum time-based rate of change at which power output returns to normal '
                'after having been capped by an over frequency event)')

# Define points for FW22
info.param('fw.settings.ramp_time', label='Ramp Time (seconds)', default=0,
           active='fw.settings.fw_mode',  active_value='FW22 (pointwise FW)',
           desc='Ramp time in seconds. A value of 0 indicates function should not ramp, but step.')
info.param('fw.settings.recovery_ramp_rate', label='Ramp Time (seconds)', default=0,
           active='fw.settings.fw_mode',  active_value='FW22 (pointwise FW)',
           desc='Optional parameter defining how quickly the DER output returns to normal '
                '(default) value after frequency returns to nominal.')
info.param('fw.settings.time_window', label='Time Window (seconds)', default=0,
           active='fw.settings.fw_mode',  active_value='FW22 (pointwise FW)',
           desc='Time window for FW change. Randomized time window for operation. '
                'A value of 0 indicates FW executes immediately.')
info.param('fw.settings.timeout_period', label='Timeout Period (seconds)', default=0,
           active='fw.settings.fw_mode',  active_value='FW22 (pointwise FW)',
           desc='Time period before function reverts to default state. '
                'A value of 0 indicates function should not revert.')
info.param('fw.settings.curve_num', label='Curve number (1-4)', default=1, values=[1,2,3,4],
           active='fw.settings.fw_mode',  active_value='FW22 (pointwise FW)')
info.param('fw.settings.n_points', label='Number of (Freq, Power) pairs (2-10)', default=3, values=[2,3,4,5,6,7,8,9,10],
           active='fw.settings.fw_mode',  active_value='FW22 (pointwise FW)')

info.param_group('fw.curve', label='fw Curve Points', index_count='fw.settings.n_points', index_start=1,
                 active='fw.settings.fw_mode',  active_value='FW22 (pointwise FW)')
info.param('fw.curve.freq', label='%Hz', default=100.,
           desc='Freq curve point')
info.param('fw.curve.W', label='%Wmax', default=100.,
           desc='Power curve point')

info.param_group('invt', label='FW Timing and Pass/Fail Parameters')
info.param('invt.pretest_delay', label='Pre-Test Delay (seconds)', default=3,
           desc='Delay before beginning the test.')
info.param('invt.power_range', label='Power Pass/Fail Screen', default=5,
           desc='+/- %nameplate power for Pass/Fail Screen (i.e., "5" = +/-5% of nameplate watts for the EUT)')
info.param('invt.setpoint_failure_count', label='Setpoint Failure Count', default=60,
           desc='Number of consecutive failures (power excursions beyond target vars) which does not '
                'produce a script fail. This accounts for EUT settling time.')
info.param('invt.setpoint_period', label='Screening Duration (seconds)', default=300,
           desc='Amount of time that the power factor is analyzed, e.g., the frequency profile length.')
info.param('invt.verification_delay', label='Verification Delay (seconds)', default=5,
           desc='Wait time allowance before assigning failure for the time parameters.')
info.param('invt.posttest_delay', label='Post-Test Delay (seconds)', default=0,
           desc='Delay after finishing the test.')
info.param('invt.disable', label='Disable FW function at end of test?', default='No', values=['Yes', 'No'])

info.param_group('profile', label='FW Profile')
info.param('profile.profile_name', label='Simulation profile', default='FW Profile',
           values=['FW Profile', 'VV Profile', 'Manual'],
           desc='"Manual" is reserved for not running a profile.')

# Grid simulator
gridsim.params(info)

# PV simulator
pvsim.params(info)

# Data and Trigger
das.params(info)

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




