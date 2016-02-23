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
import script
import gridsim


def test_run():

    result = script.RESULT_PASS

    # initialize grid simulation
    grid = gridsim.gridsim_init(ts)

    # Run the profile
    grid.profile_load(ts.param_value('profile.profile_name'))

    if ts.param_value('profile.run_profile') == 'Yes':
        grid.profile_start()

    return result

def run(test_script):
    try:
        global ts
        ts = test_script
        rc = 0
        result = script.RESULT_COMPLETE

        ts.log('**************  Starting test %s  **************' % (ts.name))
        ts.log('Script: %s %s' % (ts.name, ts.info.version))
        result = test_run()

        ts.log_active_params()

        ts.result(result)
        if result == script.RESULT_FAIL:
            rc = 1

    except Exception, e:
        ts.log('Test script exception: %s' % traceback.format_exc())
        rc = 1

    # ts.log('Returning to default power factor settings')
    sys.exit(rc)


info = script.ScriptInfo(name=os.path.basename(__file__), run=run, version='1.0.3')


info.param_group('profile', label='Grid Simulator Profile')
info.param('profile.profile_name', label='Simulation profile', default='Manual',
           values=['FW Profile', 'VV Profile', 'Manual'],
           desc='"Manual" is reserved for not running a profile.')
info.param('profile.run_profile', label='Run Profile', default='No',
           values=['Yes', 'No'],
           desc='Run the grid simulator profile?')

# Grid simulator
gridsim.params(info)

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



