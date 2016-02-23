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
import glob

import sunspec.core.client as client

#import svp.script as script
import script

def default_path():
    path_name = ''

    svp_script_dir = os.path.dirname(__file__)
    if svp_script_dir[-7:] == 'Scripts':
        path_name = svp_script_dir[:-8]

    return path_name


def test_run():

    path = ts.param_value('global.svp_dir')
    ts.log(path)

    lib_path = os.path.join(path, 'Lib')
    if os.path.isdir(lib_path):
        ts.log(lib_path)
        files = glob.glob(os.path.join(lib_path, '*.pyc'))
        for f in files:
            os.remove(f)

    scripts_path = os.path.join(path, 'Scripts')
    if os.path.isdir(scripts_path):
        ts.log(scripts_path)
        files = glob.glob(os.path.join(scripts_path, '*.pyc'))
        for f in files:
            os.remove(f)

    results_path = os.path.join(path, 'Results')
    if os.path.isdir(results_path):
        ts.log(results_path)
        files = glob.glob(os.path.join(results_path, '*'))
        for f in files:
            os.remove(f)

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

info = script.ScriptInfo(name=os.path.basename(__file__), run=run, version='1.0.1')

# inverter device parameters
info.param_group('global', label='Global Parameters', glob=True)
info.param('global.svp_dir', label='SVP Directory', default=default_path(), ptype=script.PTYPE_DIR)


def script_info():
    
    return info


if __name__ == "__main__":


    # stand alone invocation
    config_file = None
    if len(sys.argv) > 1:
        config_file = sys.argv[1]

    test_script = script.Script(info=script_info(), config_file=config_file)

    run(test_script)


