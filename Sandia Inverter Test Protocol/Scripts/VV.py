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

# Test script for IEC TR 61850-90-7 VV11, VV12, VV13, and VV14 (Volt/Var Functions)
# This test requires the following SunSpec Alliance Modbus models: inverter, controls, settings, nameplate, volt_var
#
# !C:\Python27\python.exe

import sys
import os
import math
import time
import traceback
import sunspec.core.client as client
import script
import inverter
import terrasas
import gridsim
import das
import pvsim

# returns: True if state == current connection state and power generation matches threshold expectation, False if not
def verify_initial_conn_state(inv, state, time_period=0, threshold=50, data=None):
    result = None
    start_time = time.time()

    while result is None:
        elapsed_time = time.time()-start_time
        if elapsed_time <= time_period:
            if not inverter.verify_conn_state(inv, state, threshold, data):
                ts.sleep(0.89) #Attempt to make loop exactly 1 second
            else:
                result = True
        else:
            result = False

    return result


def var_pass_fail_band(inv, volt=None, var=None, n_points=4, var_range=50., deptRef = 2, data=None):
    varTarg = None
    var_upper = None
    var_lower = None

    #Check to be sure the voltages are monotonically increasing.
    for i in xrange(1, n_points-1):
        if volt[i] > volt[i+1]:
            ts.log_error('Voltages are not monotonically increasing in volt-var curve.')
        break

    lots_of_output = False #Flag to turn on data dumps to help debugging
    if lots_of_output:
        ts.log_debug('deptRef: %s' % deptRef)

    # get var settings
    try:
        inv.nameplate.read()
        max_Var = float(inv.nameplate.VArRtgQ1) #Q1 is pos
        max_VA = float(inv.nameplate.VARtg) #Q1 is pos
        max_W = float(inv.nameplate.WRtg) #Q1 is pos
        if lots_of_output:
            ts.log_debug('max_Var = %0.3f, max_VA = %0.3f, and max_W = %0.3f.' % (max_Var, max_VA, max_W))
    except Exception, e:
        ts.log_error('Unable to get var limits from EUT: %s' % str(e))
        raise
        #return script.RESULT_FAIL

    #Get grid voltage to determine the proper EUT vars
    gridV = inverter.get_ac_voltage_pct(inv, das=data)

    if deptRef == inverter.VOLTVAR_WMAX:
        if gridV < volt[1]: #Vgrid is below the 1st point - extrapolate
            varAval = math.sqrt(math.pow(max_VA,2) - math.pow(max_W,2)) # units of vars
            varAvalTargPct = var[1]/100.
            varTarg = varAval*varAvalTargPct # units of vars
            var_upper = varTarg + var_range*max_Var/100. #units of vars #var_range is %max_Var
            var_lower = varTarg - var_range*max_Var/100. #units of vars #var_range is %max_Var
            if lots_of_output:
                ts.log_debug('Low')
                ts.log_debug('varAval, varAvalTarg Fraction, varTarg, var_upper, var_lower')
                ts.log_debug('%.3f, %.3f, %.3f, %.3f, %.3f' %
                             (varAval, varAvalTargPct, varTarg, var_upper, var_lower))
        elif gridV > volt[n_points]: #Vgrid is above the last point - extrapolate
            varAval = math.sqrt(math.pow(max_VA,2) - math.pow(max_W,2)) # units of vars
            varAvalTargPct = var[n_points]/100.
            varTarg = varAval*varAvalTargPct # units of vars
            var_upper = varTarg + var_range*max_Var/100. #units of vars #var_range is %max_Var
            var_lower = varTarg - var_range*max_Var/100. #units of vars #var_range is %max_Var
            if lots_of_output:
                ts.log_debug('High')
                ts.log_debug('varAval, varAvalTarg Fraction, varTarg, var_upper, var_lower')
                ts.log_debug('%.3f, %.3f, %.3f, %.3f, %.3f' %
                             (varAval, varAvalTargPct, varTarg, var_upper, var_lower))
        else:
            # pointwise algorithm to find target vars
            for i in xrange(1, n_points):
                if lots_of_output:
                    ts.log_debug('Grid voltage is %.3f' % (gridV))
                    ts.log_debug('i = %d' % i)
                    ts.log_debug('gridV >= volt[i] and gridV <= volt[i+1]')
                    ts.log_debug('%.3f >= %.3f and %.3f <= %.3f' % (gridV, volt[i], gridV, volt[i+1]))

                if gridV >= volt[i] and gridV <= volt[i+1]: #curve interpolation
                    varAval = math.sqrt(math.pow(max_VA,2) - math.pow(max_W,2)) # units of vars
                    #varTarg = Qi + (Qi+1 - Qi)*((gridV - Vi)/(Vi+1 - Vi))
                    varAvalTargPct = (var[i] + (var[i+1] - var[i]) * ((gridV - volt[i])/(volt[i+1] - volt[i])))/100.
                    varTarg = varAval*varAvalTargPct # units of vars
                    var_upper = varTarg + var_range*max_Var/100. #units of vars #var_range is %max_Var
                    var_lower = varTarg - var_range*max_Var/100. #units of vars #var_range is %max_Var
                    if lots_of_output:
                        ts.log_debug('Interpolated')
                        ts.log_debug('varAval, varAvalTarg Fraction, varTarg, var_upper, var_lower')
                        ts.log_debug('%.3f, %.3f, %.3f, %.3f, %.3f' %
                                     (varAval, varAvalTargPct, varTarg, var_upper, var_lower))
                    break

    elif deptRef == inverter.VOLTVAR_VARMAX:
        if gridV < volt[1]: #Vgrid is below the 1st point - extrapolate
            varTargPct = var[1]/100.
            varTarg = max_Var*varTargPct # units of vars
            var_upper = varTarg + var_range*max_Var/100. #units of vars #var_range is %max_Var
            var_lower = varTarg - var_range*max_Var/100. #units of vars #var_range is %max_Var
            if lots_of_output:
                print 'volt[1], var[1]'
                print volt[1], var[1]
                ts.log_debug('Low')
                ts.log_debug('varTarg Fraction, varTarg, var_upper, var_lower')
                ts.log_debug('%.3f, %.3f, %.3f, %.3f' % (varTargPct, varTarg, var_upper, var_lower))
        elif gridV > volt[n_points]: #Vgrid is above the last point - extrapolate
            varTargPct = var[n_points]/100.
            varTarg = max_Var*varTargPct # units of vars
            var_upper = varTarg + var_range*max_Var/100. #units of vars #var_range is %max_Var
            var_lower = varTarg - var_range*max_Var/100. #units of vars #var_range is %max_Var
            if lots_of_output:
                print 'volt[n_points], var[n_points]'
                print volt[n_points], var[n_points]
                ts.log_debug('High')
                ts.log_debug('varTarg Fraction, varTarg,  var_upper, var_lower')
                ts.log_debug('%.3f, %.3f, %.3f, %.3f' % (varTargPct, varTarg, var_upper, var_lower))
        else:
            # pointwise algorithm to find target vars
            for i in xrange(1, n_points):
                if lots_of_output:
                    ts.log_debug('Grid voltage is %.3f' % (gridV))
                    ts.log_debug('i = %d' % i)
                    ts.log_debug('gridV >= volt[i] and gridV <= volt[i+1]')
                    ts.log_debug('%.3f >= %.3f and %.3f <= %.3f' % (gridV, volt[i], gridV, volt[i+1]))
                    #ts.log('var_range = %.3f' % var_range)
                if gridV >= volt[i] and gridV <= volt[i+1]: #curve interpolation
                    #varTarg = Qi + (Qi+1 - Qi)*((gridV - Vi)/(Vi+1 - Vi))
                    varTargPct = (var[i]+(var[i+1]-var[i])*((gridV-volt[i])/(volt[i+1]-volt[i])))/100.
                    varTarg = max_Var*varTargPct
                    var_upper = varTarg + var_range*max_Var/100. #var_range is %VarAval
                    var_lower = varTarg - var_range*max_Var/100. #var_range is %VarAval
                    if lots_of_output:
                        print 'var[i], var[i+1], var[i], gridV, volt[i], volt[i+1], volt[i]'
                        print var[i], var[i+1], var[i], gridV, volt[i], volt[i+1], volt[i]
                        print 'var[i] + (var[i+1]-var[i])*((gridV-volt[i])/(volt[i+1]-volt[i]))'
                        print var[i] + (var[i+1]-var[i])*((gridV-volt[i])/(volt[i+1]-volt[i]))
                        ts.log_debug('Interpolated - VV12')
                        ts.log_debug('varTarg Fraction, varTarg, var_upper, var_lower')
                        ts.log_debug('%.3f, %.3f, %.3f, %.3f' % (varTargPct, varTarg, var_upper, var_lower))
                    break


    elif deptRef == inverter.VOLTVAR_VARAVAL:
        fixedVarPct = var[1]/100. ###NOTE: fixedVarPct is a decimal, not in units of percent
        if volt[1] == 1: # %VarAval
            varAval = math.sqrt(math.pow(max_VA,2) - math.pow(max_W,2)) # units of vars
            varTarg = varAval*fixedVarPct # units of vars
            var_upper = varTarg + var_range/100.*max_Var #units of vars #var_range is %max_Var
            var_lower = varTarg - var_range/100.*max_Var #units of vars #var_range is %max_Var
        elif volt[1] == 2: # %WMax
            varTarg = max_W*fixedVarPct
            var_upper = varTarg + var_range/100.*max_Var #var_range is %max_Var
            var_lower = varTarg - var_range/100.*max_Var #var_range is %max_Var
        else: # %VarMax
            varTarg = max_Var*fixedVarPct # units of vars
            var_upper = varTarg + var_range/100.*max_Var #var_range is %max_Var
            var_lower = varTarg - var_range/100.*max_Var #var_range is %max_Var

    else:
        varTarg = 0
        var_upper = varTarg + var_range/100.*max_Var #var_range is %max_Var
        var_lower = varTarg - var_range/100.*max_Var #var_range is %max_Var

    return (varTarg, var_upper, var_lower)

def test_run():

    result = script.RESULT_FAIL
    data = None
    trigger = None
    grid = None
    pv = None
    inv = None
    volt = {}
    var = {}
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

        vv_mode = ts.param_value('vv.settings.vv_mode')
        if vv_mode == 'VV11 (watt priority)':
            deptRef = inverter.VOLTVAR_WMAX
        elif vv_mode == 'VV12 (var priority)':
            deptRef = inverter.VOLTVAR_VARMAX
        elif vv_mode == 'VV13 (fixed var)':
            deptRef = inverter.VOLTVAR_VARAVAL
            fixedVar = ts.param_value('vv.settings.fixedVar')
            var[1] = fixedVar # Not very clean - will pull 'points' info out later for pass/fail bounds
            fixedVarRef = ts.param_value('vv.settings.fixedVarRef')
            if fixedVarRef == '%VarAval':
                volt[1] = 1 # Not very clean - will pull 'points' info out later for pass/fail bounds
            elif fixedVarRef ==  '%WMax':
                volt[1] = 2 # Not very clean - will pull 'points' info out later for pass/fail bounds
            else: #fixedVarRef == '%VarMax'
                volt[1] = 3 # Not very clean - will pull 'points' info out later for pass/fail bounds
        else:
            deptRef = 4

        time_window = ts.param_value('vv.settings.time_window')
        timeout_period = ts.param_value('vv.settings.timeout_period')
        ramp_time = ts.param_value('vv.settings.ramp_time')

        if vv_mode == 'VV11 (watt priority)' or vv_mode == 'VV12 (var priority)':
            n_points = ts.param_value('vv.settings.n_points')
            curve_num = ts.param_value('vv.settings.curve_num')
            volt = ts.param_value('vv.curve.volt')
            var = ts.param_value('vv.curve.var')

        var_range = ts.param_value('invt.var_range')
        setpoint_period = ts.param_value('invt.setpoint_period')
        pretest_delay = ts.param_value('invt.pretest_delay')
        setpoint_failure_count = ts.param_value('invt.setpoint_failure_count')
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
        profile_name = ts.param_value('profile.profile_name')
        grid.profile_load(profile_name)

        #Inverter scan after grid and PV simulation setup so that Modbus registers can be read.
        ts.log('Scanning inverter')
        inv = client.SunSpecClientDevice(ifc_type, slave_id=slave_id, name=ifc_name, baudrate=baudrate, parity=parity,
                                         ipaddr=ipaddr, ipport=ipport)

        # Make sure the EUT is on and operating
        ts.log('Verifying EUT is in connected state. Waiting up to %d seconds for EUT to begin power export.'
               % (verification_delay+pretest_delay))
        if verify_initial_conn_state(inv, state=inverter.CONN_CONNECT,
                                     time_period=verification_delay+pretest_delay, data=data) is False:
                ts.log_error('Inverter unable to be set to connected state.')
                raise script.ScriptFail()

        ######## Begin Test ########
        if pretest_delay > 0:
            ts.log('Waiting for pre-test delay of %d seconds' % pretest_delay)
            ts.sleep(pretest_delay)

        # Request status from EUT and display vars
        var_original = inverter.get_var(inv, das=data)
        ts.log('Current reactive power is %.3f VAr' % var_original)

        #ts.log_debug('SET volt and var are: %s, %s' % (volt, var))
        #inv.volt_var.read()
        #ts.log_debug('inv.volt_var.ActCrv = %d' % inv.volt_var.ActCrv)
        inverter.set_volt_var(inv, volt=volt, var=var, n_points=n_points, time_window=time_window,
                              timeout_period=timeout_period, ramp_time=ramp_time,
                              curve_num=curve_num, deptRef=deptRef, enable=1, trigger=trigger)

        # Run the grid simulator profile immediately after setting the volt-var functions and triggering
        if grid is not None:
            ts.log('Running voltage profile.')
            grid.profile_start()

        inv.nameplate.read()
        VarAval = inv.nameplate.VArRtgQ1
        WAval = inv.nameplate.WRtg

        varTarg, var_upper, var_lower = var_pass_fail_band(inv, volt=volt, var=var, n_points=n_points,
                                                           var_range=var_range, deptRef=deptRef, data=data)

        ts.log('Target vars: %.3f. Pass limits for screening: lower = %.3f  upper = %.3f' %
               (varTarg, var_lower, var_upper))

        # Log VV parameters and calculate test_duration
        test_duration = setpoint_period + verification_delay
        ts.log('Waiting up to %d seconds for power change with a verification period of %d seconds.' %
               (ramp_time + time_window , verification_delay))

        start_time = time.time()
        elapsed_time = 0

        # Initialize consecutive failure count to not script fail on transient behavior
        failures = 0
        revert_complete = False

        if time_window != 0:
            window_complete = False
        else:
            window_complete = True
        time_window_execution = time_window

        while elapsed_time <= test_duration:
            ts.sleep(0.93)
            elapsed_time = time.time()-start_time

            current_vars = inverter.get_var(inv, das=data)
            if window_complete == True and revert_complete == False:
                varTarg, var_upper, var_lower = var_pass_fail_band(inv, volt=volt, var=var, n_points=n_points,
                                                               var_range=var_range, deptRef=deptRef, data=data)
            else:
                # Before the time window executes and after timeout period, the upper and lower pass/fail bounds for EUT
                # use the default volt-var state of 0 vars
                varTarg = 0
                inv.nameplate.read()
                var_upper = var_range/100.*float(inv.nameplate.VArRtgQ1) #var_range is %max_Var
                var_lower = -(var_range/100.*float(inv.nameplate.VArRtgQ1)) #var_range is %max_Var

            # Cheat a little since var is unsigned from data (and inverter?)
            if varTarg < 0 and current_vars > 0:
                current_vars = -current_vars

            ts.log('Var Target = %.3f [%.3f to %.3f], Vars = %.3f (Total Error = %.3f%%), Time: %0.3f seconds.' %
                   (varTarg, var_lower, var_upper, current_vars, (current_vars - varTarg)/VarAval*100.0, elapsed_time))

            if not revert_complete:

                # Check when the EUT is in range for the first time
                if window_complete == False and inverter.get_active_control_status(inv, inverter.STACTCTL_VOLT_VAR):
                    window_complete = True
                    time_window_execution = elapsed_time
                    ts.log('Randomization window occurred at %0.3f seconds, current vars %.3f.' %
                           (time_window_execution, current_vars))

                # Check for timeout period (reversion)
                if window_complete and timeout_period != 0:

                    #ts.log_debug('Volt-Var mode is: %d' %
                    #             inverter.get_active_control_status(inv, inverter.STACTCTL_VOLT_VAR))
                    #ts.log_debug('Is revert complete? %s' % revert_complete)

                    #### Update this section with the following line when firmware is updated
                    #if not inverter.get_active_control_status(inv, inverter.STACTCTL_VOLT_VAR): #reverted
                    if elapsed_time > timeout_period: #To be changed at a later date
                        revert_complete = True
                        ts.log('Reversion occurred at timeout period = %0.3f seconds, current vars %.3f.'
                                % (elapsed_time, current_vars))

                    # Did timeout_period fail?  If so, end the test here.
                    # Note: there's a final timeout_period check outside the while loop.
                    elif elapsed_time >= timeout_period+min(time_window,time_window_execution)+verification_delay:
                        ts.log_error('Inverter did not revert after %0.3f seconds.' % (elapsed_time))
                        raise script.ScriptFail()

                # if vars out of range
                if current_vars < var_lower or current_vars > var_upper:
                    # There are three acceptable sources of noncompliance. If the randomization window hasn't occurred,
                    # the reversion (timeout) occurred, or it is ramping to the target vars
                    if window_complete == False: #time window
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
            inv.volt_var.ModEna = 0
            inv.volt_var.write()
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


info.param_group('vv', label='VV Configuration')
info.param_group('vv.settings', label='VV Settings')
info.param('vv.settings.vv_mode', label='Volt-Var Mode', default='VV11 (watt priority)',
           values=['VV11 (watt priority)', 'VV12 (var priority)', 'VV13 (fixed var)', 'VV14 (no volt-var)'])
info.param('vv.settings.ramp_time', label='Ramp Time (seconds)', default=0,
           desc='Ramp time in seconds.'
                'A value of 0 indicates function should not ramp, but step.')
info.param('vv.settings.time_window', label='Time Window (seconds)', default=0,
           desc='Time window for volt-VAR change. Randomized time window for operation. '
                'A value of 0 indicates VV executes immediately.')
info.param('vv.settings.timeout_period', label='Timeout Period (seconds)', default=0,
           desc='Time period before function reverts to default state. '
                'A value of 0 indicates function should not revert.')
#info.param('vv.settings.ramp_rate', label='Ramp Rate Limit (%VarAval/sec (VV11))', default=0,
#           active='vv.settings.vv_mode',
#           active_value=['VV11 (watt priority)'],
#           desc='Maximum Ramp Rate in %VarAval/sec for VV11 and %Var/sec  for VV12, VV13, and VV14.')

# VV13 settings
info.param('vv.settings.fixedVarRef', label='Var reference', default='%VarAval',
           values=['%VarAval', '%WMax', '%VarMax'],
           active='vv.settings.vv_mode',  active_value=['VV13 (fixed var)'])
info.param('vv.settings.fixedVar', label='Fixed Var Setting (% Var reference)', default=20.0,
           active='vv.settings.vv_mode',
           active_value=['VV13 (fixed var)'])

# Define points for VV11 and VV12
info.param('vv.settings.curve_num', label='Curve number (1-4)', default=1, values=[1,2,3,4])
info.param('vv.settings.n_points', label='Number of (Volt, VAr) pairs (2-10)', default=4, values=[2,3,4,5,6,7,8,9,10],
           active='vv.settings.vv_mode',  active_value=['VV11 (watt priority)', 'VV12 (var priority)'])
info.param_group('vv.curve', label='VV Curve Points', index_count='vv.settings.n_points', index_start=1,
                 active_value=['VV11 (watt priority)', 'VV12 (var priority)'])
info.param('vv.curve.volt', label='Volt', default=100.,
           desc='Volt curve point')
info.param('vv.curve.var', label='VAr', default=0.,
           desc='VAr curve point')

info.param_group('invt', label='VV Timing and Pass/Fail Parameters')
info.param('invt.pretest_delay', label='Pre-Test Delay (seconds)', default=3,
           desc='Delay before beginning the test.')
info.param('invt.var_range', label='Var Pass/Fail Screen', default=15.,
           desc='+/- %Vars for Pass/Fail Screen (i.e., "5" = +/-5% of Max EUT Var Output)')
info.param('invt.setpoint_failure_count', label='Setpoint Failure Count', default=60,
           desc='Number of consecutive failures (var excursions beyond target vars) which does not '
                'produce a script fail. This accounts for EUT settling times due to AC input transients.')
info.param('invt.setpoint_period', label='Screening Duration (seconds)', default=300,
           desc='Amount of time that the power factor is analyzed, e.g., the voltage profile length.')
info.param('invt.verification_delay', label='Verification Delay (seconds)', default=5,
           desc='Wait time allowance before assigning failure for the time parameters.')
info.param('invt.posttest_delay', label='Post-Test Delay (seconds)', default=0,
           desc='Delay after finishing the test.')
info.param('invt.disable', label='Disable volt-var function at end of test?', default='No', values=['Yes', 'No'])

info.param_group('profile', label='VV Profile')
info.param('profile.profile_name', label='Simulation profile', default='VV Profile',
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



