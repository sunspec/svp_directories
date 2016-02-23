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

# Test script for SIRFN ESS Protocol - FW

#!C:\Python27\python.exe

import sys
import os
import traceback
import time
import inverter

import gridsim
import das

import sunspec.core.client as client
import script

# returns: current ac freq as a percentage of nominal
def get_ac_freq_pct(inv, freq_ref = 60., data=None):
    try:

        #only use the das (data acquisition system) if it is available
        if data:
            data.read()
            gridFraw = data.ac_freq
        # without the das use the EUT to report the power level
        else:
            inv.inverter.read()
            gridFraw = float(inv.inverter.Hz)

        inv.settings.read()
        Freq_nom = float(freq_ref)

        return (gridFraw/Freq_nom)*100.0

    except Exception, e:
        raise script.ScriptFail('Unable to get ac freq from das or EUT: %s' % str(e))


def interp(x1, y1, x2, y2, x_int):
    return y1 + (y2 - y1) * ((x_int - x1)/(x2 - x1))


def test_run():

    result = script.RESULT_FAIL
    data = None
    trigger = None
    grid = None
    inv = None
    freq = {}
    W = {}
    disable = None


    # Step 1: Prepare the EUT according to the following.
    # -	Connected EUT to an energy storage device or an energy storage simulator and depending on the connection scheme
    # to a PV simulator.
    # -	Connect to Utility Simulator with operation within nominal voltage range for a minimum of 5 minutes.
    # -	Verify EUT is powered on to a level required to receive the command.
    # -	Verify energy storage state of charge (SOC) will not interfere with FW tests.  If the SOC is near SOCmax or
    # SOCmin, charge or discharge the ES system until close to nominal SOC.
    # -	Established communication to EUT with Utility Management System (UMS).
    # -	Record EUT output (e.g., voltage, current, power) with data acquisition system.
    #
    # Step 2: Request status from EUT and record the EUT parameters.
    #
    # Step 3: Send FW (F, P) pairs according to Test 1 in Table 1-2.  Send default timing parameters to EUT according to
    # Table 1-3.
    #
    # Step 4: Confirm FW parameters are updated in the EUT.
    #
    # Step 5: Set the EUT power to WMAXch.
    #
    # Step 6: Adjust the grid frequency to the required grid frequency points: 5 points per line and the Hzmin and Hzmax
    # points. The tests will run from nominal frequency to Hzmin to Hzmax back to nominal frequency.
    #
    # Step 7: Set the timing parameters according to Test 1 in Table 1-3.
    #
    # Step 8: Step the grid frequency to Hzmin and Hzmax according to Section 1.4.2.
    #
    # Step 9: Repeat Steps 7-8 with all the timing parameters required based on the FCT.
    #
    # Step 10: Repeat Steps 6-9 with the EUT power set to WMAXch, 50% WMAXch, 0, 50% WMAXdch, WMAXdch
    #
    # Step 11: Repeat Steps 3 - 10 for each FW domain test to be performed according to the FCT. (If the EUT is not
    # capable of hysteresis tests 1-2 will be performed in Table 1-2.  If the EUT is capable of hysteresis tests 1-5
    # will be performed in Table 1-2.)
    #
    # Step 12: Analyze performance data.


    try:
        pretest_delay = ts.param_value('invt.pretest_delay')
        power_range = ts.param_value('invt.power_range')
        setpoint_failure_count = ts.param_value('invt.setpoint_failure_count')
        setpoint_period = ts.param_value('invt.setpoint_period')
        verification_delay = ts.param_value('invt.verification_delay')
        posttest_delay = ts.param_value('invt.posttest_delay')
        disable = ts.param_value('invt.disable')

        # initialize data acquisition system
        daq = das.das_init(ts)
        data = daq.data_init()
        trigger = daq.trigger_init()

        # initialize grid simulation
        grid = gridsim.gridsim_init(ts)

        ######## Begin Test ########
        if pretest_delay > 0:
            ts.log('Waiting for pre-test delay of %d seconds' % pretest_delay)
            ts.sleep(pretest_delay)

        #Test # 1:
        WMAXdch = 4.5
        WMAXch = -4.5
        Hzmin = 52
        Hzmax = 68

        #Arrays of (Fx,Px)y pairs where x is the point number and y is the FW quadrant

        #Curve 1
        F11 = 100
        P11 = WMAXdch
        F21 = Hzmax-1
        P21 = WMAXdch
        F31 = Hzmax-0.5
        P31 = 0

        #Curve 2
        F12 = 100
        P12 = WMAXdch
        F22 = Hzmin
        P22 = WMAXdch
        F32 = Hzmin+0.5
        P32 = 0

        #Curve 3
        F13 = 100
        P13 = WMAXch
        F23 = Hzmin+1
        P23 = WMAXch
        F33 = Hzmin+0.5
        F33 = 0

        #Curve 4
        F14 = 100
        P14 = WMAXch
        F24 = Hzmax
        P24 = WMAXch
        F34 = Hzmax-0.5
        P34 = 0

        Fn = 60.

        for start_power in [WMAXdch, WMAXdch/2, 0, WMAXch/2, WMAXch]:

            if ts.confirm('Set EUT output power to %.3f.' % start_power) is False:
                ts.log('Aborted FW test because output power was not set.')

            ts.log('Output power now set to %.2f.' % start_power)

            if start_power == WMAXdch:
                lines = [1, 4, 5, 6, 7, 8]
            elif start_power == WMAXch:
                lines = [1, 2, 3, 4, 5, 8]
            else:
                lines = range(1, 9)

            for line in lines:
                #ts.log('Testing frequency values along line # %i.' % line)

                F_left = interp(P22, F22, P23, F23, start_power) # assume slope for curves in quad 2 and 3 are same
                # ts.log('F_left=%.3f, P22=%.3f, F22=%.3f, P23=%.3f, F23=%.3f, start_power=%.3f, .'
                #        % (F_left, P22, F22, P23, F23, start_power))
                F_right = interp(P21, F21, P24, F24, start_power) # assume slope for curves in quad 2 and 3 are same

                if line == 1:
                    start = Fn
                    stop = F_left
                elif line == 2:
                    start = F_left
                    stop = F22
                elif line == 3:
                    start = F22
                    stop = F_left
                elif line == 4:
                    start = F_left
                    stop = Fn
                elif line == 5:
                    start = Fn
                    stop = F_right
                elif line == 6:
                    start = F_right
                    stop = F24
                elif line == 7:
                    start = F24
                    stop = F_right
                else:  # line = 8
                    start = F_right
                    stop = Fn

                step = (stop-start)/5.
                # frequency points. The end is captured with the next line
                testpoints = [start, start+step, start+(2*step), start+(3*step)]
                #ts.log('Test points are %s' % testpoints)

                for freq in testpoints:
                    # Step the grid simulator frequency immediately after setting the freq-watt functions and triggering
                    if grid is not None:
                        grid.freq(freq=freq)

                        freq_read = power = 0.0
                        if data:
                            data.read()
                            freq_read = data.ac_freq
                            power = data.ac_watts

                        # ts.log('Frequency set to %.3f.' % freq)
                        ts.log('DAQ Frequency and Power = %.3f, %.3f' % (freq_read, power))

                        ts.sleep(verification_delay)

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
        if disable == 'yes' and inv is not None:
            inv.freq_watt_param.ModEna = 0
            inv.freq_watt_param.write()

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


info = script.ScriptInfo(name=os.path.basename(__file__), run=run, version='1.0.3')

info.param_group('invt', label='FW Timing and Pass/Fail Parameters')
info.param('invt.pretest_delay', label='Pre-Test Delay (seconds)', default=3,
           desc='Delay before beginning the test.')
info.param('invt.power_range', label='Power Pass/Fail Screen', default=5,
           desc='+/- %nameplate power for Pass/Fail Screen (i.e., "5" = +/-5% of nameplate watts for the EUT)')
info.param('invt.setpoint_failure_count', label='Setpoint Failure Count', default=60,
           desc='Number of consecutive failures (power excursions beyond target vars) which does not '
                'produce a script fail. This accounts for EUT settling time.')
info.param('invt.setpoint_period', label='Screening Duration (seconds)', default=300,
           desc='Amount of time that the power factor is analyzed, e.g., the frequency profile length.')
info.param('invt.verification_delay', label='Verification Delay (seconds)', default=5,
           desc='Wait time allowance before assigning failure for the time parameters.')
info.param('invt.posttest_delay', label='Post-Test Delay (seconds)', default=0,
           desc='Delay after finishing the test.')
info.param('invt.disable', label='Disable FW function at end of test?', default='No', values=['Yes', 'No'])

# Grid simulator
gridsim.params(info)

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
