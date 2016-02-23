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

# #!C:\Python27\python.exe

import sys
import os
import traceback
import math
import time
import pvsim

import sunspec.core.client as client
import script

import inverter

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

# output function to log the connection status and the current output power
def log_conn_state(inv, das=None):
    try:
        connected = inverter.get_conn_state(inv)
        power = inverter.get_power(inv, das)
        ts.log('Current connection state is %s - power output = %0.3f W' %
               (inverter.conn_state_str(connected), power))
    except Exception, e:
        ts.log_error('Error logging connect state: %s' % str(e))
        raise

def test_run():

    result = script.RESULT_FAIL
    das = None
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

        # Sandia Test Protocol: Communication is established between the Utility Management System Simulator
        # and EUT
        ts.log('Scanning EUT')
        try:
            inv = client.SunSpecClientDevice(ifc_type, slave_id=slave_id, name=ifc_name, baudrate=baudrate,
                                             parity=parity, ipaddr=ipaddr, ipport=ipport)
        except Exception, e:
            raise script.ScriptFail('Error: %s' % (e))

        verification_delay = 5
        pretest_delay = 0

        # Make sure the EUT is on and operating
        ts.log('Verifying EUT is in connected state. Waiting up to %d seconds for EUT to begin power export.'
               % (verification_delay+pretest_delay))
        if verify_initial_conn_state(inv, state=inverter.CONN_CONNECT,
                                     time_period=verification_delay+pretest_delay, das=das) is False:
            inv.controls.read()
            inv.controls.WMaxLimPct = 100
            inv.controls.write()

        try:
            inv.settings.read()
            power_max = int(inv.settings.WMax)
            ts.log('Inverter maximum power = %d W' % (power_max))
        except Exception, e:
            raise('Unable to get WMax setting: %s' % str(e))

        for power_limit_pct in [10, 20, 30, 40, 50, 60, 70, 80, 90, 100]:

            # Sandia Test Protocol Step 4: Issue power curtailment function
            # (Trigger set immediately before sending the enable command to the DER)
            inv.controls.read()
            inv.controls.WMaxLimPct = power_limit_pct
            inv.controls.write()

            curr_power = inverter.get_power(inv, das=None)
            ts.log('INV2 setpoint changed to %d%%, power = %d W' % (power_limit_pct, curr_power))

            time.sleep(3)

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
