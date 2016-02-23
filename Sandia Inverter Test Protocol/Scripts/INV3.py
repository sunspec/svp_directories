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

# Test script for IEC TR 61850-90-7 INV3 (Fixed Power Factor)
# This test requires the following SunSpec Alliance Modbus models: inverter, controls, settings, nameplate
#
#!C:\Python27\python.exe

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

# get the screening range for the INV3 test
def calculate_pf_range(power_factor, power_factor_range):
    #Note 1: 'lower' and 'upper' are defined by vertical position on P-Q plane (not based on numerical value)
    #Note 2: Within Q1 and Q4 the 'upper' value is greater than the PF and the 'lower' value is less than the PF
    #Note 3: Q1 is negative, Q4 is positive
    if power_factor < 0 and power_factor_range - power_factor >= 1: #in Q1 with range back into Q4
        power_factor_upper = power_factor + power_factor_range
        power_factor_lower = 1 - (power_factor_range - (1 + power_factor))
    else: 
        if power_factor > 0 and power_factor_range + power_factor > 1: #in Q4 (and unity) with range back to Q1
            power_factor_upper = (power_factor_range - (1 - power_factor)) - 1
            power_factor_lower = power_factor - power_factor_range
        else: #in Q1 or Q4 with range in same quadrant 
            power_factor_upper = power_factor + power_factor_range
            power_factor_lower = power_factor - power_factor_range
    return (power_factor_upper, power_factor_lower)

# Function reports if the EUT PF out of range
def pf_out_of_range(power_factor, power_factor_lower, power_factor_upper, power_factor_range):
    # False = in range, True = out of range
    # Note: Q1 is negative, Q4 is positive
    
    if power_factor_lower*power_factor_upper < 0: #range includes both Q1 and Q4
        if power_factor > 0 and power_factor > power_factor_lower: # between limits in Q4
            #Note: since the PF is assumed to be the correct sign, you do not have to check the other side of unity
            return False
        elif power_factor <= 0 and power_factor < power_factor_upper: # between limits in Q1
            #Note: since the PF is assumed to be the correct sign, you do not have to check the other side of unity
            return False
        else:
            return True
    else: #in Q1 or Q4 with range in same quadrant
        if power_factor > 0: # Q4
            if power_factor > power_factor_lower and power_factor < power_factor_upper:
                #ts.log_debug('power_factor > power_factor_lower = %.3f > %.3f, ' \
                #      'power_factor < power_factor_upper = %.3f < %.3f' \
                #      %  (power_factor, power_factor_lower, power_factor, power_factor_upper))
                return False
            else:
                return True
        else: # Q1
            if power_factor > power_factor_lower and power_factor < power_factor_upper:
                #ts.log_debug('power_factor > power_factor_lower = %.3f > %.3f, ' \
                #      'power_factor < power_factor_upper = %.3f < %.3f' \
                #      %  (power_factor, power_factor_lower, power_factor, power_factor_upper))
                return False
            else:
                return True

# Log the connection status and the current output power
def log_conn_state(inv, data=None):
    try:
        connected = inverter.get_conn_state(inv)
        power = inverter.get_power(inv, data)
        pf = inverter.get_power_factor(inv, data)
        ts.log('Current connection state is %s. Power output = %0.3f W. power factor %0.3f.' %
               (inverter.conn_state_str(connected), power, pf))
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

        power_factor = ts.param_value('inv3.power_factor')
        ramp_time = ts.param_value('inv3.ramp_time')  # time to ramp
        time_window = ts.param_value('inv3.time_window')
        timeout_period = ts.param_value('inv3.timeout_period')
    
        pretest_delay = ts.param_value('invt.pretest_delay')
        power_factor_range = ts.param_value('invt.power_factor_range')
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
        pv.irradiance_set(ts.param_value('profile.irr_start'))
        pv.profile_load(ts.param_value('profile.profile_name'))
        pv.power_on()

        # Sandia Test Protocol: Communication is established between the Utility Management System Simulator and EUT
        ts.log('Scanning EUT')
        try:
            # Sandia Test Protocol Step 1: Request status of EUT
            # Sandia Test Protocol Step 2: UMS receives response from EUT
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

        # Get parameters
        try:
            inv.nameplate.read()
            # get min/max PF settings
            min_PF = float(inv.nameplate.PFRtgQ1)
            max_PF = float(inv.nameplate.PFRtgQ4)
            ts.log('Power factor range for this device is %.3f to %.3f' % (min_PF, max_PF))

            # Sandia Test Protocol Step 3: EUT output power factor is measured and logged
            # Get INV3 settings and report these.

            # Get PF from EUT
            pf = inverter.get_power_factor(inv, das=data)
            ts.log('Power factor is %f.' % pf)
        except Exception, e:
            raise script.ScriptFail('Unable to get PF limits or PF from EUT: %s' % str(e))

        try:
            inv.controls.read()
            OutPFSet_Ena = inv.controls.OutPFSet_Ena
            if OutPFSet_Ena:
                ts.log('Power factor mode is enabled.')
            else:
                ts.log('Power factor mode is not enabled.')
        except Exception, e:
            raise script.ScriptFail('Unable to read OutPFSet_Ena: %s' % str(e))

        #### Comparison of DAS PF and the EUT PF
        # Request status from DAS and display power factor
        if data:
            data.read()
            power_factor_data_original = data.ac_pf
            ts.log_debug('Current DAS-measured power factor is +/-%.3f' % power_factor_data_original)

        # Request status from EUT and display power factor
        power_factor_original = inverter.get_power_factor(inv, data)
        if power_factor_original is not None:
            pass
            # ts.log_debug('Current inverter-measured power factor is +/-%.3f' % power_factor_original)
        else:
            ts.log_error('Inverter does not have PF in the inverter model.')
            raise script.ScriptFail()

        # Find pass/fail bounds
        (power_factor_upper, power_factor_lower) = calculate_pf_range(power_factor, power_factor_range)
        ts.log('Target power factor: %.3f. Pass limits for screening: lower = %.3f  upper = %.3f' %
               (power_factor, power_factor_lower, power_factor_upper))

        # Sandia Test Protocol Step 4: Issue power factor function
        # (Trigger set immediately before sending the enable command to the DER)
        inverter.set_power_factor(inv, time_window=time_window, timeout_period=timeout_period, ramp_time=ramp_time,
                                  power_factor=power_factor, enable=1, trigger=trigger)

        # Start the pv simulator irradiance profile
        pv.profile_start()

        # Store INV3 execution time for determining when time window and timeout period occur
        # Note: this is below the pv.start command to allow the manual operator time to begin he profile.
        start_time = time.time()
        elapsed_time = 0

        # Sandia Test Protocol Step 5: EUT response to command.
        # Sandia Test Protocol Step 6: Verify command was executed. (Conduct test while profile is running.)

        # Log INV3 parameters and calculate test_duration
        test_duration = setpoint_period + verification_delay
        ts.log('Waiting up to %d seconds for power factor change with a verification period of %d seconds.' %
               (ramp_time + time_window , verification_delay))

        # Initialize consecutive failure count to not script fail on transient behavior
        failures = 0
        revert_complete = False

        if time_window != 0:
            window_complete = False
            time.sleep(2) #EUT needs some time to adjust inverter.STACTCTL_FIXED_PF
        else:
            window_complete = True
        time_window_execution = time_window

        while elapsed_time <= test_duration:
            ts.sleep(0.93)
            elapsed_time = time.time()-start_time

            pf = inverter.get_power_factor(inv, data)

            # Cheating here because the PF is unsigned in inv.inverter.PF and data.ac_pf
            # With a good data acquisition system, this code block can be deleted.
            if power_factor < 0 and pf > 0:
                # assume the PF is the correct sign
                pf = -pf

            # Screening: determine if the PF is in the target range
            out_of_range = pf_out_of_range(pf, power_factor_lower, power_factor_upper, power_factor_range)

            ts.log('PF Target = %.3f, PF = %.3f (Total Error = %.3f%%), Time: %0.3f seconds.' %
                   (power_factor, pf, (pf - power_factor)*100.0, elapsed_time))

            if revert_complete == False:
                #ts.log_debug('PF status: %d. Time: %.3f seconds.' %
                #             (inverter.get_active_control_status(inv, inverter.STACTCTL_FIXED_PF), elapsed_time))

                # Check when the EUT is in range for the first time
                if window_complete == False and inverter.get_active_control_status(inv, inverter.STACTCTL_FIXED_PF):
                    window_complete = True
                    time_window_execution = elapsed_time
                    ts.log('Randomization window occurred at %0.3f seconds, current power factor %.3f.' %
                           (time_window_execution, pf))

                # Check for timeout period (reversion)
                if window_complete == True and timeout_period != 0:

                    #ts.log_debug('PF mode is: %d' %
                    #             inverter.get_active_control_status(inv, inverter.STACTCTL_FIXED_PF))
                    #ts.log_debug('Is revert complete? %s' % revert_complete)

                    if not inverter.get_active_control_status(inv, inverter.STACTCTL_FIXED_PF): #reverted
                        revert_complete = True
                        ts.log('Reversion occurred at timeout period = %0.3f seconds, current power factor %.3f.'
                                % (elapsed_time, pf))

                        #Change target power factor to default settings (PF = unity)
                        power_factor = 1.0
                        (power_factor_upper, power_factor_lower) = calculate_pf_range(1.0, power_factor_range)

                    # Did timeout_period fail?  If so, end the test here.
                    # Note: there's a final timeout_period check outside the while loop.
                    elif elapsed_time >= timeout_period+min(time_window,time_window_execution)+verification_delay:
                        ts.log_error('Inverter did not revert after %0.3f seconds.' % (elapsed_time))
                        raise script.ScriptFail()

                # if pf is out of range
                if out_of_range is True:
                    # There are three acceptable sources of noncompliance. If the randomization window hasn't occurred,
                    # the reversion (timeout) occurred, or it is ramping to the target PF
                    if window_complete == False: #time window
                        ts.log('Randomization window still in effect after %0.3f seconds.' % (time.time()-start_time))
                    elif elapsed_time > min(time_window,time_window_execution)+ramp_time:
                        # Noncompliance is not from time period, time window, or ramp rate
                        # Count this as a failure
                        failures += 1
                        if failures >= setpoint_failure_count:
                            ts.log_error('Inverter exceeded PF setpoint + buffer after %0.3f seconds. '
                                         'Fail count = %d.' % (elapsed_time,failures))
                            raise script.ScriptFail()
                        else:
                            ts.log_warning('Inverter exceeded PF setpoint + buffer after %0.3f seconds. '
                                           'Fail count = %d.' % (elapsed_time,failures))
                    elif ramp_time != 0:
                        ts.log_warning('EUT has not reached the target PF, likely because it is ramping.')
                else:
                    failures = 0

        # Additional timeout check to determine if the timeout_period occurred during the test. This is necessary
        # in cases where the verification_delay is not set sufficiently long.
        if timeout_period != 0 and inverter.get_active_control_status(inv, inverter.STACTCTL_FIXED_PF):
            ts.log_error('Inverter did not revert by the end of the test duration. Elapsed time = %0.3f seconds.  '
                         'Increase the verification period if the timeout period is greater than the elapsed time.'
                         % (elapsed_time))
            raise script.ScriptFail()

        if posttest_delay > 0:
              ts.log('Waiting for post-test delay of %d seconds.' % posttest_delay)
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
            inv.controls.OutPFSet_Ena = 0
            inv.controls.write()

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

    #ts.log('Returning to default power factor settings')   
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

info.param_group('inv3', label='INV3 Test Parameters')
info.param('inv3.power_factor', label='Power Factor (negative = underexcited)', default=1.0,
           desc='Positive PF is underexcited, leading, absorbing reactive power, sinking vars like a capacitive source'
                'or inductive load.')
info.param('inv3.ramp_time', label='Ramp Time (seconds)', default=0,
           desc='Time for the power converter-based DER to move from the current setpoint to the new setpoint.')
info.param('inv3.time_window', label='Time Window (seconds)', default=0,
           desc='Randomized time window for operation. A value of 0 indicates INV2 executes immediately.')
info.param('inv3.timeout_period', label='Timeout Period (seconds)', default=0,
           desc='Time period before function reverts to default state. '
                'A value of 0 indicates function should not revert.')

info.param_group('invt', label='INV3 Timing and Pass/Fail Parameters')
info.param('invt.pretest_delay', label='Pre-Test Delay (seconds)', default=35,
           desc='Delay before beginning the test.')
info.param('invt.power_factor_range', label='Power Factor Pass/Fail Screen', default=0.05,
           desc='Entering a value of 0.03 means the PF can be within +/-0.03 of the target PF.')
info.param('invt.setpoint_failure_count', label='Setpoint Failure Count', default=5,
           desc='Number of consecutive failures (power factor excursions beyond target PF) which does not '
                'produce a script fail. This accounts for EUT settling times due to DC input transients.')
info.param('invt.setpoint_period', label='Screening Duration (seconds)', default=360,
           desc='Amount of time that the power factor is analyzed, e.g., the irradiance profile length.')
info.param('invt.verification_delay', label='Verification Delay (seconds)', default=5,
           desc='Wait time allowance before assigning failure for the time parameters.')
info.param('invt.posttest_delay', label='Post-Test Delay (seconds)', default=0,
           desc='Delay after finishing the test.')
info.param('invt.disable', label='Disable INV3 function at end of test?', default='No', values=['Yes', 'No'])

info.param_group('profile', label='PV Simulator Profile')
info.param('profile.profile_name', label='Profile Name', default='None',
           values=['None', 'STPsIrradiance'],
           desc='Select name or "None"" to not run a profile.')
info.param('profile.irr_start', label='Initial Irradiance (W/m^2)', default=1000.0,
           desc='Irradiance at the beginning of the profile. Use 200 W/m^2 for the Sandia Test Protocols.')

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

    test_script = script.Script(info=script_info(), config_file=config_file)

    run(test_script)


