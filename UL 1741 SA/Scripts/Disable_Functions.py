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
import inverter

import sunspec.core.client as client

import script


def test_run():

    global inv

    ifc_type = ts.param_value('global.inverter.ifc_type')
    ifc_name = ts.param_value('global.inverter.ifc_name')
    baudrate = ts.param_value('global.inverter.baudrate')
    parity = ts.param_value('global.inverter.parity')
    ipaddr = ts.param_value('global.inverter.ipaddr')
    ipport = ts.param_value('global.inverter.ipport')
    slave_id = ts.param_value('global.inverter.slave_id')

    INV1 = ts.param_value('resets.inv1')
    INV2 = ts.param_value('resets.inv2')
    INV3 = ts.param_value('resets.inv3')
    VV = ts.param_value('resets.vv')

    print INV1, INV2, INV3, VV

    inv = client.SunSpecClientDevice(ifc_type, slave_id=slave_id, name=ifc_name, baudrate=baudrate, parity=parity, ipaddr=ipaddr, ipport=ipport)

    try:
        inv.read()
    except Exception, e:
        ts.log('Unable to read EUT.')
        return script.RESULT_FAIL

    if inv.controls.Conn == '0' and INV1 == 'yes':
        ts.log('Inverter in disconnected state, setting state to connected')
        state = inverter.CONN_CONNECT
        inverter.set_conn_state(inv, state, time_window=0, timeout_period=0)
    ts.log('INV1 Reset - Inverter operating.')

    if INV2 == 'yes':
        inverter.set_power_limit(inv, time_window=0, timeout_period=0, ramp_time=0, power_limit_pct=100, enable=0)
        ts.log('INV2 Disabled.')

    if INV3 == 'yes':
        inverter.set_power_factor(inv, time_window=0, timeout_period=0, ramp_time=0, power_factor=1, enable=0)
        ts.log('INV3 Disabled.')

    if VV == 'yes':
        inverter.set_volt_var(inv, n_points=0, time_window=0, timeout_period=0, ramp_time=0, curve_num=1,
                              deptRef=2, enable=0)
        ts.log('VV Functions Disabled.')

    return script.RESULT_PASS

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

# inverter device parameters
info.param_group('global', label='Global Parameters', glob=True)
info.param_group('global.inverter', label='Inverter Device Parameters')
info.param('global.inverter.ifc_type', label='Interface Type', default=client.RTU, values=[client.RTU, client.TCP, client.MAPPED])

# rtu parameters
info.param('global.inverter.ifc_name', label='Interface Name', default='COM3',  active='global.inverter.ifc_type', active_value=[client.RTU])
info.param('global.inverter.baudrate', label='Baud Rate', default=9600, values=[9600, 19200], active='global.inverter.ifc_type', active_value=[client.RTU])
info.param('global.inverter.parity', label='Parity', default='N', values=['N', 'E'], active='global.inverter.ifc_type', active_value=[client.RTU])

# tcp parameters
info.param('global.inverter.ipaddr', label='IP Address', default='127.0.0.1', active='global.inverter.ifc_type', active_value=[client.TCP])
info.param('global.inverter.ipport', label='IP Port', default=502, active='global.inverter.ifc_type', active_value=[client.TCP])
info.param('global.inverter.map_name', label='Map File', default='',  active='global.inverter.ifc_type', active_value=[client.MAPPED], ptype=script.PTYPE_FILE)
info.param('global.inverter.slave_id', label='Slave Id', default=1)

info.param_group('resets', label='Reset These Functions')
info.param('resets.inv1', label='Reset INV1?', default='yes', values=['yes', 'no'])
info.param('resets.inv2', label='Reset INV2?', default='yes', values=['yes', 'no'])
info.param('resets.inv3', label='Reset INV3?', default='yes', values=['yes', 'no'])
info.param('resets.vv', label='Reset VV Functions?', default='yes', values=['yes', 'no'])

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


