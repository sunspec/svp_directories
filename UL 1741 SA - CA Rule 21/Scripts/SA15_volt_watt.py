'''
Copyright (c) 2016, Sandia National Labs and SunSpec Alliance
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
import gridsim
import pvsim
import das

import sunspec.core.client as client

import script
import openpyxl

def test_run():

    result = script.RESULT_FAIL
    daq = None

    try:
        # initialize data acquisition system
        ts.log('result_id = %s' % (ts.result_id()))
        ts.log('result_dir = %s' % (ts.result_dir()))

        grid = gridsim.gridsim_init(ts)
        pv = pvsim.pvsim_init(ts)
        daq = das.das_init(ts)

        pv.irradiance_set(ts.param_value('profile.irr_start'))
        # pv.profile_load(ts.param_value('profile.profile_name'))
        # pv.profile_start()
        pv.power_on()

        ts.log('Running capture 2')
        daq.data_capture_start()
        ts.sleep(8)
        daq.data_capture_stop()
        ds = daq.data_capture_dataset()
        ds.to_csv(ts.result_file('capture_2.csv'))

        result = script.RESULT_COMPLETE

    except script.ScriptFail, e:
        reason = str(e)
        if reason:
            ts.log_error(reason)
    finally:
        if daq is not None:
            daq.close()

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

info = script.ScriptInfo(name=os.path.basename(__file__), run=run, version='1.0.0')

gridsim.params(info)
pvsim.params(info)

info.param_group('profile', label='PV Simulator Profile')
info.param('profile.profile_name', label='Profile Name', default='None',
           values=['None', 'Test Profile'],
           desc='Select name or "None"" to not run a profile.')
info.param('profile.irr_start', label='Initial Irradiance (W/m^2)', default=1000.0,
           desc='Irradiance at the beginning of the profile.')

das.params(info)

# info.logo('sunspec.gif')

def script_info():
    
    return info


if __name__ == "__main__":

    # stand alone invocation
    config_file = None
    if len(sys.argv) > 1:
        config_file = sys.argv[1]

    params = None

    test_script = script.Script(info=script_info(), config_file=config_file, params=params)
    test_script.log('log it')

    run(test_script)


