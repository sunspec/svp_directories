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

# Test script for IEC TR 61850-90-7 INV1 (Connect/Disconnect)
# This test requires the following SunSpec Alliance Modbus models: inverter, controls, settings, nameplate

#!C:\Python27\python.exe

import sys
import os
import traceback
import time
import inverter
import pvsim
import das

import sunspec.core.client as client
import script

# returns: True if state == current connection state and power generation matches threshold expectation, False if not
def verify_conn_state_change(inv, state, time_window=0, timeout_period=0, verification_delay=5, threshold=50,
                             data=None):
    result = None
    start_time = time.time()
    elapsed_time = 0

    # Time window takes precedence over timeout period: time_window is passed first when time_window and timeout_period
    # are used at the same time.
    if time_window != 0:
        time_period = time_window + verification_delay
        # Note: the actual amount of time allowed for the change is time_period, not time_window
        ts.log('Randomization window in use. Waiting up to %d seconds for %s state' %
               (time_window, inverter.conn_state_str(state)))
    elif timeout_period != 0:
        time_period = timeout_period + verification_delay
        # Note: the actual amount of time allowed for the change is time_period, not timeout_period
        ts.log('Time period in use. Waiting up to %d seconds for EUT to revert to %s.  '
               'Verification time is %d seconds.' %
               (timeout_period, inverter.conn_state_str(state), verification_delay))
    else:
        time_period = verification_delay
        ts.log('Waiting for verification delay of up to %d seconds' % verification_delay)

    while result is None:
        if elapsed_time <= time_period:
            power = inverter.get_power(inv, data)
            ts.log('Elapsed time is %0.3f seconds, EUT power is %0.3f W' % (elapsed_time, power))
            if not inverter.verify_conn_state(inv, state, threshold, data):
                ts.sleep(0.89)  # Attempt to make loop exactly 1 second
                elapsed_time = time.time()-start_time
            else:
                ts.log('State changed to %s after %0.3f seconds' % (inverter.conn_state_str(state), elapsed_time))
                result = True
        else:
            ts.log('Connection state did not change within required time')
            result = False

    log_conn_state(inv, data)
    return result

# output function to log the connection status and the current output power
def log_conn_state(inv, data=None):
    try:
        connected = inverter.get_conn_state(inv)
        power = inverter.get_power(inv, data)
        ts.log('Current connection state is %s - power output = %0.3f W' % (inverter.conn_state_str(connected), power))
    except Exception, e:
        ts.log('Error logging connect state: %s' % str(e))
        raise

def test_run():

    result = script.RESULT_FAIL
    data = None
    trigger = None
    inv = None
    pv = None
    disable = None

    try:
        # EUT communication parameters
        ifc_type = ts.param_value('comm.ifc_type')
        ifc_name = ts.param_value('comm.ifc_name')
        if ifc_type == client.MAPPED:
            ifc_name = ts.param_value('comm.map_name')
        baudrate = ts.param_value('comm.baudrate')
        parity = ts.param_value('comm.parity')
        ipaddr = ts.param_value('comm.ipaddr')
        ipport = ts.param_value('comm.ipport')
        slave_id = ts.param_value('comm.slave_id')

        # INV1 parameters
        operation = ts.param_value('inv1.operation')
        time_window = ts.param_value('inv1.time_window')
        timeout_period = ts.param_value('inv1.timeout_period')

        # Script timing and pass/fail criteria
        pretest_delay = ts.param_value('invt.pretest_delay')
        verification_delay = ts.param_value('invt.verification_delay')
        posttest_delay = ts.param_value('invt.posttest_delay')
        power_threshold = ts.param_value('invt.power_threshold')
        disable = ts.param_value('invt.disable')

        # initialize data acquisition system
        daq = das.das_init(ts)
        data = daq.data_init()
        trigger = daq.trigger_init()

        # initialize pv simulation
        pv = pvsim.pvsim_init(ts)
        pv.power_on()

        # It is assumed that the PV and Grid Simulators (if used) are connected to the EUT and operating properly
        # prior to running this test script.
        if pretest_delay > 0:
            ts.log('Waiting for pre-test delay of %d seconds' % pretest_delay)
            ts.sleep(pretest_delay)

        # Sandia Test Protocol: Communication is established between the Utility Management System Simulator and EUT
        ts.log('Scanning EUT')
        try:
            inv = client.SunSpecClientDevice(ifc_type, slave_id=slave_id, name=ifc_name, baudrate=baudrate,
                                             parity=parity, ipaddr=ipaddr, ipport=ipport)
        except Exception, e:
            raise script.ScriptFail('Error: %s' % e)

        # Define operation states (connected/disconnected)
        # Default state is required for timeout_periods because the EUT will return to that mode of operation
        default_state = inverter.CONN_CONNECT
        if operation == 'Connect':
            orig_state = inverter.CONN_DISCONNECT
            state = inverter.CONN_CONNECT
        elif operation == 'Disconnect':
            orig_state = inverter.CONN_CONNECT
            state = inverter.CONN_DISCONNECT
        else:
            ts.log('Unknown operation requested: %s' % operation)
            raise script.ScriptFail()

        # Sandia Test Protocol Step 1: Request Status of EUT.
        # Sandia Test Protocol Step 2: UMS receives response to the DS93 command.
        # Verify EUT is in correct state before running the test.
        if inverter.verify_conn_state(inv, orig_state, threshold=power_threshold, das=data) is False:
            # todo: update inverter module with das changed to data
            ts.log('Inverter not in correct state, setting state to: %s' %
                   (inverter.conn_state_str(orig_state)))
            # EUT put into state where INV1 can be verified
            inverter.set_conn_state(inv, orig_state)
            if verify_conn_state_change(inv, orig_state, verification_delay=verification_delay,
                                        threshold=power_threshold, data=data) is False:
                raise script.ScriptFail()

        # Sandia Test Protocol Step 3: Inverter output is measured and logged.
        log_conn_state(inv, data=data)

        # Sandia Test Protocol Step 4: UMS issues the INV1 command.
        ts.log('Executing %s' % operation)
        inverter.set_conn_state(inv, state, time_window=time_window, timeout_period=timeout_period, trigger=trigger)

        # Sandia Test Protocol Step 5: Verify the INV1 command was successfully executed.
        if verify_conn_state_change(inv, state, time_window=time_window, verification_delay=verification_delay,
                                    threshold=power_threshold, data=data) is False:
            raise script.ScriptFail()

        # Verify revert (timeout) to default state if timeout period specified
        if timeout_period > 0:

             if verify_conn_state_change(inv, default_state, timeout_period=timeout_period,
                                         verification_delay=verification_delay,
                                         threshold=power_threshold, data=data) is False:
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
            inv.controls.Conn = 1
            inv.controls.write()

    # Sandia Test Protocol Step 6: Repeat test with different parameters from the INV Test Matrix.
    return result

    # Sandia Test Protocol Step 7: After running all the tests for this function, characterize the EUT response with
    # the collected data and assign pass/fail.

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

info.param_group('inv1', label='INV1 Test Parameters')
info.param('inv1.operation', label='Operation', default='Connect', values=['Connect', 'Disconnect'],
           desc='Operation to be performed in test.')
info.param('inv1.time_window', label='Time Window (seconds)', default=0,
           desc='Randomized time window for operation. A value of 0 indicates INV1 executes immediately.')
info.param('inv1.timeout_period', label='Timeout Period (seconds)', default=0,
           desc='Time period before connect state reverts to default state. '
                'A value of 0 indicates change should not revert.')

info.param_group('invt', label='INV1 Timing and Pass/Fail Parameters')
info.param('invt.pretest_delay', label='Pre-Test Delay (seconds)', default=0,
           desc='Delay before beginning the test.')
info.param('invt.power_threshold', label='Power Verification Threshold for Pass/Fail (W)', default=50,
           desc='Power threshold in watts to use to determine pass/fail, e.g., connection passes when '
                'EUT output is above the threshold.')
info.param('invt.verification_delay', label='Verification Delay (seconds)', default=5,
           desc='Time allowed for INV1 operations. Applied to connect, disconnect, time window, and revert.')
info.param('invt.posttest_delay', label='Post-Test Delay (seconds)', default=10,
           desc='Delay after finishing the test.')
info.param('invt.disable', label='Set INV1 to ON at the end of the test?', default='No', values=['Yes', 'No'])

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




