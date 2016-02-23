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

#!C:\Python27\python.exe

import sys
import os
import traceback
import time
import script
import sunspec.core.client as client


def test_run():

    result = script.RESULT_FAIL
    f = None

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

        # Data parameters
        duration = ts.param_value('data.duration')
        interval = ts.param_value('data.interval')
        parameters = ts.param_value('data.parameters')
        filename = ts.param_value('data.filename')

        # Sandia Test Protocol: Communication is established between the Utility Management System Simulator and EUT
        ts.log('Scanning EUT')
        try:
            inv = client.SunSpecClientDevice(ifc_type, slave_id=slave_id, name=ifc_name, baudrate=baudrate,
                                             parity=parity, ipaddr=ipaddr, ipport=ipport)
        except Exception, e:
            raise script.ScriptFail('Error: %s' % e)

        # PARSE PARAMETERS
        ts.log('Configuring the data capture for the following channels: %s' % parameters)

        formattedchans = parameters.replace(", ", "\t")
        formattedchans = formattedchans.replace(",", "\t")
        formattedchans = 'Time\tTotal_Time\t%s' % formattedchans  # add python time and absolute time to channels
        ts.log('Channel string: %s' % formattedchans)
        channels = formattedchans.split()

        results_dir = os.path.dirname(__file__)[:-7] + 'Results' + os.path.sep
        csv_filename = '%s%s.tsv' % (results_dir, filename)
        ts.log('Saving to file: %s' % csv_filename)
        f = open(csv_filename, 'w')

        try:
            f.write("%s\n" % formattedchans)
        except Exception, e:
            ts.log_error('Unable to save channel list to file: %s' % csv_filename)

        starttime = time.time()
        while duration >= (time.time()-starttime):
            try:
                inv.inverter.read()
                totaltime = time.time()-starttime
                ts.log('Collecting data at time: %s' % totaltime)
                data_string = '%s\t%s\t' % (time.time(), totaltime)
                for name in channels[2:]:
                    # ts.log('Getting %s data.' % name)
                    dpoint = 'inv.inverter.%s' % name  # Assume all channels are in SunSpec Model 'inverter'
                    # ts.log('Result: %s' % eval(dpoint))
                    data_string += str(eval(dpoint))
                    data_string += '\t'
                try:
                    f.write("%s\n" % data_string)
                except Exception, e:
                    ts.log_error('Unable to save channel list to file: %s. %s' % (csv_filename, e))
            except Exception, e:
                ts.log_error('Inverter could not be read. %s' % e)

            time.sleep(interval - ((time.time() - starttime) % interval))

        if f is not None:
            f.close()

        result = script.RESULT_PASS

    except script.ScriptFail, e:
        reason = str(e)
        if reason:
            ts.log_error(reason)
    finally:
        if f is not None:
            f.close()

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

info.param_group('data', label='EUT Data Parameters')
info.param('data.duration', label='Capture Duration (seconds)', default=30)
info.param('data.interval', label='Capture Interval (seconds)', default=1)
info.param('data.parameters', label='EUT parameters to capture (SunSpec names).', default='Hz, W, PF, DCA, DCV',
           desc='Use the SunSpec parameter names to create the channels to capture.')
info.param('data.filename', label='Data file name', default='FrequencyData',
           desc='The results will be saved in the results folder of the SVP directory.')

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




