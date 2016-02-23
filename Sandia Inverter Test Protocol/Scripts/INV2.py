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

# Test script for IEC TR 61850-90-7 INV2 (Curtail active power)
# This test requires the following SunSpec Alliance Modbus models: inverter, controls, settings, nameplate
#
# #!C:\Python27\python.exe

import sys
import os
import traceback
import math
import time
import pvsim
import das

import sunspec.core.client as client
import script

import inverter

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

# output function to log the connection status and the current output power
def log_conn_state(inv, data=None):
    try:
        connected = inverter.get_conn_state(inv)
        power = inverter.get_power(inv, data)
        ts.log('Current connection state is %s - power output = %0.3f W' %
               (inverter.conn_state_str(connected), power))
    except Exception, e:
        ts.log_error('Error logging connect state: %s' % str(e))
        raise

def test_run():

    result = script.RESULT_FAIL
    data = None
    trigger = None
    inv = None
    pv = None
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

        power_limit_pct = ts.param_value('inv2.power_limit_pct')
        ramp_time = ts.param_value('inv2.ramp_time')  # slope defined by % nameplate power/sec
        time_window = ts.param_value('inv2.time_window')
        timeout_period = ts.param_value('inv2.timeout_period')

        pretest_delay = ts.param_value('invt.pretest_delay')
        power_limit_pct_buffer = ts.param_value('invt.power_limit_pct_buffer')
        screening_period = ts.param_value('invt.screening_period')
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
        pv.irradiance_set(ts.param_value('profile.irr_start'))
        pv.profile_load(ts.param_value('profile.profile_name'))
        pv.power_on()

        # Sandia Test Protocol: Communication is established between the Utility Management System Simulator
        # and EUT
        ts.log('Scanning EUT')
        try:
            inv = client.SunSpecClientDevice(ifc_type, slave_id=slave_id, name=ifc_name, baudrate=baudrate,
                                             parity=parity, ipaddr=ipaddr, ipport=ipport)
        except Exception, e:
            raise script.ScriptFail('Error: %s' % (e))

        if pretest_delay > 0:
            ts.log('Waiting for pre-test delay of %d seconds' % pretest_delay)
            ts.sleep(pretest_delay)

        # Make sure the EUT is on and operating
        ts.log('Verifying EUT is in connected state. Waiting up to %d seconds for EUT to begin power export.'
               % (verification_delay+pretest_delay))
        if verify_initial_conn_state(inv, state=inverter.CONN_CONNECT,
                                     time_period=verification_delay+pretest_delay, data=data) is False:
                ts.log_error('Inverter unable to be set to connected state.')
                raise script.ScriptFail()

        # Sandia Test Protocol Step 1: Request status of EUT
        # Sandia Test Protocol Step 2: UMS receives response from EUT
        try:
            inv.settings.read()
            power_max = int(inv.settings.WMax)
            ts.log('Inverter maximum power = %d W' % (power_max))
        except Exception, e:
            raise('Unable to get WMax setting: %s' % str(e))

        # Sandia Test Protocol Step 3: EUT output power is measured and logged
        power_original = float(inverter.get_power(inv, das=data))
        ts.log('Inverter power = %0.3f W' % power_original)

        # Sandia Test Protocol Step 4: Issue power curtailment function
        # (Trigger set immediately before sending the enable command to the DER)
        inverter.set_power_limit(inv, time_window=time_window, timeout_period=timeout_period, ramp_time=ramp_time,
                                 power_limit_pct=power_limit_pct, enable=1, trigger=trigger)

        # Start the pv simulator irradiance profile
        pv.profile_start()

        # Store INV2 execution time for determining when time window and timeout period occur
        # Note: this is below the pv.profile_start command to allow the manual operator time to begin he profile.
        start_time = time.time()
        elapsed_time = 0

        # Sandia Test Protocol Step 5: EUT response to command.
        # Sandia Test Protocol Step 6: Verify command was executed. (Conduct test while profile is running.)

        # Power_limit is a value in watts (e.g., 1500 W), whereas power_limit_pct is a percentage (e.g., 50)
        power_limit = int(power_max * power_limit_pct/100.0) + float(power_max * (float(power_limit_pct_buffer)/100.0))
        ts.log('INV2 setpoint changed to %d%%, power_limit = %d W' % (power_limit_pct, power_limit))

        # Log INV2 parameters
        if ramp_time != 0:
            ts.log('Ramp time is %d seconds.' % (ramp_time))
        if time_window != 0:
            ts.log('Using randomization window of %d seconds.' % time_window)
            window_complete = False
        else:
            window_complete = True
        if verification_delay > 0:
            ts.log('Using verification delay of %d seconds.' % verification_delay)

        # rt_tw_duration is the allowable time for the curtailment of the function to initiate
        rt_tw_duration = ramp_time + time_window + verification_delay

        ts.log('Waiting up to %d seconds for power change with a verification period of %d seconds.' %
               (ramp_time + time_window , verification_delay))

        # Check for INV2 execution and (loosely) screen for Time Window and/or Ramp Time
        ramp_and_window_complete = None
        while ramp_and_window_complete is None:
            if elapsed_time <= rt_tw_duration:
                power = inverter.get_power(inv, das=data)

                # Determine if the Time Window has occurred
                if not window_complete and inverter.get_active_control_status(inv, inverter.STACTCTL_FIXED_W):
                    ts.log('Time window result: EUT enabled INV2 after %0.3f seconds' % (time.time()-start_time))
                    window_complete = True
                else:
                    ts.log('Time window incomplete after %0.3f seconds' % (time.time()-start_time))

                # Check on ramp time
                if window_complete and power <= power_limit:
                    ts.log('EUT changed output power limit to setpoint range after %0.3f seconds, '
                           'current output power is %d W.' %
                           (time.time()-start_time, power))
                    ramp_and_window_complete = True
                else:
                    ts.log_warning('EUT has not completed the Time Window or Ramp Time by %0.3f seconds' % (time.time()-start_time))
                    ts.sleep(0.998) # Attempt to sleep 1 second for each loop iteration
                    elapsed_time = time.time()-start_time
            else:
                ts.log_error('Operation did not occur within time window, current power output is %d W' % (power))
                ramp_and_window_complete = False
        if ramp_and_window_complete is False:
            raise script.ScriptFail()

        # If INV2 will time out, enter this conditional.
        # Note that only the reversion (timeout period) is screened here. No other functionality is verified.
        if timeout_period > 0:
            # Note: continue the 'elapsed_time' from the previous loop
            ts.log('Timeout Period in use. Waiting up to %d seconds for inverter to revert to original output power. '
                   'Additional verification time is %d seconds.' % (timeout_period, verification_delay))

            revert_complete = None
            while revert_complete is None:

                if elapsed_time <= timeout_period + verification_delay:
                    power = inverter.get_power(inv, das=data)

                    # Check when inverter has disabled the INV2 command to determine when the reversion has occurred.
                    #ts.log_debug('INV2 mode is: %d' %
                    #             inverter.get_active_control_status(inv, inverter.STACTCTL_FIXED_W))
                    if not inverter.get_active_control_status(inv, inverter.STACTCTL_FIXED_W):
                        ts.log('Inverter reverted to increased output power after %0.3f seconds' %
                               (time.time()-start_time))
                        revert_complete = True

                    # Reversion has not occurred
                    else:
                        ts.sleep(0.998) # Attempt to sleep 1 second for each loop iteration
                        elapsed_time = time.time()-start_time

                    ts.log('EUT Power Limit Target = %.2f %%, EUT %% power = %.2f (Total Error = %.2f%%). '
                           'Time: %0.3f seconds.' % (power_limit_pct, power*100/power_max,
                            ((power - power_limit_pct*power_max/100)/power_max)*100., elapsed_time))

                else:
                    revert_complete = False
                    ts.log_error('Revert operation did not occur within %d seconds, current power output '
                                     'is %d W.' % (timeout_period + verification_delay , power))
            if revert_complete is False:
                raise script.ScriptFail()

        # If there is no reversion is in effect, determine if INV2 maintains the correct curtailment for a screening
        # period.  Generally the screening period will be equal to the length of the DC input profile.
        elif screening_period > 0:
            # Note: continue the 'elapsed_time' from the previous loop
            ts.log('Verifying setpoint range is not exceeded for %d seconds.' % (screening_period))

            # curtailment_success is an indication of proper curtailment
            curtailment_success = None

            # Initialize failure count to 0. Allow the power to exceed this value 'setpoint_failure_count' times.
            failures = 0

            # Ensure proper curtailment for the screening period
            while curtailment_success is None:
                if elapsed_time <= screening_period:
                    power = inverter.get_power(inv, das=data)

                    # failure only occurs if the EUT power exceeds the curtailment power_limit
                    if power > power_limit:
                        ts.sleep(0.998) # Attempt to sleep 1 second for each loop iteration
                        failures += 1
                        ts.log_warning('Inverter exceeded power setpoint %d consecutive times.' % (failures))
                        if failures >= setpoint_failure_count:
                            curtailment_success = False
                            ts.log_error('Inverter exceeded power setpoint + buffer after %0.3f seconds, current output '
                                         'power is %d W.' % (elapsed_time, power))

                    else: # power is below the power_limit
                        ts.sleep(0.998) # Attempt to sleep 1 second for each loop iteration
                        elapsed_time = time.time()-start_time
                        failures = 0

                    ts.log('EUT Watt %% Limit Target= %.2f, EUT %% power = %.2f (Total Error = %.2f%%)' %
                           (power_limit_pct, power*100/power_max,
                            ((power - power_limit_pct*power_max/100)/power_max)*100.))

                # EUT maintained proper operation for the screening period
                else:
                    ts.log('Inverter remained within power limit for setpoint period, current power output '
                           'is %d W.' % (power))
                    curtailment_success = True

                if curtailment_success is False:
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
        if pv is not None:
            pv.close()
        if disable == 'yes' and inv is not None:
            inv.controls.WMaxLim_Ena = 0
            inv.controls.write()

    return result

    # Sandia Test Protocol Step 7: Repeat tests varying the INV2 parameters.
    # Sandia Test Protocol Step 8: Post-process to verify response with data analysis.

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


info = script.ScriptInfo(name=os.path.basename(__file__), run=run, version='1.0.2')

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

info.param_group('inv2', label='INV2 Test Parameters')
info.param('inv2.power_limit_pct', label='Power Curtailment Setpoint (% of nameplate)', default=100,
           desc='Curtail to this setpoint (% nameplate).')
info.param('inv2.ramp_time', label='Ramp Time (Seconds)', default=0,
           desc='Power ramp time to adjust to the new power output.')
info.param('inv2.time_window', label='Time Window (seconds)', default=0,
           desc='Randomized time window for operation. A value of 0 indicates INV2 executes immediately.')
info.param('inv2.timeout_period', label='Timeout Period (seconds)', default=0,
           desc='Time period before function reverts to default state. '
                'A value of 0 indicates function should not revert.')

info.param_group('invt', label='INV2 Timing and Pass/Fail Parameters')
info.param('invt.pretest_delay', label='Pre-Test Delay (seconds)', default=35,
           desc='Delay before beginning the test.')
info.param('invt.power_limit_pct_buffer', label='Allowable Setpoint Error (% of nameplate)', default=5,
           desc='Tolerance applied to the pass/fail screening. This is applied only to the INV2 upper limit.')
info.param('invt.screening_period', label='Screening Duration (seconds)', default=360,
           desc='Amount of time that the power curtailment is analyzed, e.g., the irradiance profile length.')
info.param('invt.setpoint_failure_count', label='Setpoint Failure Count', default=5,
           desc='Number of consecutive failures (power excursions beyond Power Setpoint) which does not '
                'produce a script fail. This accounts for EUT settling times due to DC input transients.')
info.param('invt.verification_delay', label='Verification Delay (seconds)', default=5,
           desc='Wait time allowance before assigning failure for the time parameters.')
info.param('invt.posttest_delay', label='Post-Test Delay (seconds)', default=0,
           desc='Delay after finishing the test.')
info.param('invt.disable', label='Disable INV2 function at end of test?', default='No', values=['Yes', 'No'])

info.param_group('profile', label='PV Simulator Profile')
info.param('profile.profile_name', label='Profile Name', default='None',
           values=['None', 'STPsIrradiance'],
           desc='Select name or "None"" to not run a profile.')
info.param('profile.irr_start', label='Initial Irradiance (W/m^2)', default=1000.0,
           desc='Irradiance at the beginning of the profile. Use 1000 W/m^2 for the Sandia Test Protocols.')

#PV simulator
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

    test_script = script.TestScript(info=script_info(), config_file=config_file)

    run(test_script)
