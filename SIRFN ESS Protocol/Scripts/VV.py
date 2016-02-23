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

# Test script for SIRFN ESS Protocol - VV
# This test requires the following SunSpec Alliance Modbus models: inverter, controls, settings, nameplate, volt_var
#
# !C:\Python27\python.exe

import sys
import os
import math
import time
import traceback
import numpy as np

import sunspec.core.client as client
import script

import inverter
import terrasas
import gridsim
import das

# returns: current ac voltage
def get_ac_voltage_pct(inv, data=None):
    try:

        #only use the das (data acquisition system) if it is available
        if data:
            data.read()
            gridVraw = data.ac_freq
        # without the das use the EUT to report the power level
        else:
            inv.inverter.read()
            gridVraw = float(inv.inverter.PhVphA)

        inv.settings.read()
        Vgrid_nom = float(inv.settings.VRef)

        return (gridVraw/Vgrid_nom)*100.0

    except Exception, e:
        raise script.ScriptFail('Unable to get ac voltage from das or EUT: %s' % str(e))

def grid_voltage_get(volt=None, var=None, v_nom = 240., line_to_test=1, voltage_pct_test_point=0.):

    v_min_pct = 100.*211./v_nom
    v_max_pct = 100.*264./v_nom
    v_min_lvrt_pct = v_min_pct  # not implemented now because it's not in many EUT modbus mappings
    v_max_lvrt_pct = v_max_pct  # not implemented now because it's not in many EUT modbus mappings

    if line_to_test == 1:
        #ts.log_debug('First line')
        # set the minimum point on the first curve to the greater of:
        # a) minimum voltage for the function
        # b) minimum voltage for the LVRT Near Nominal (NN) value
        Vmin_pct = max(v_min_pct,v_min_lvrt_pct)
        Vmax_pct = volt[1]

    elif line_to_test == int(volt['index_count']+1):
        #ts.log_debug('Last line')
        # set the maximum point on the last curve to the lesser of:
        # a) maximum voltage for the function
        # b) maximum voltage for the HVRT Near Nominal (NN) value
        Vmax_pct = min(v_max_pct,v_max_lvrt_pct)
        Vmin_pct = volt[volt['index_count']]

        #todo: warn if the voltage is above the grid simulator limits

    else:
        #ts.log_debug('One of the middle lines')
        Vmin_pct = volt[line_to_test-1]
        Vmax_pct = volt[line_to_test]

    # Address the situations when then (V,Q) points are above or below the EUT's min and max voltage
    # If that is the case, set the voltage limits for the line segment to the EUT limits
    if Vmin_pct < v_min_pct:
        ts.log_warning('       Point %i voltage is below the minimum voltage of the EUT.' % (line_to_test-1))
        ts.log_warning('       Setting the Line Segment Start point to the minimum EUT voltage.')
        Vmin_pct = v_min_pct
    if Vmax_pct < v_min_pct:
        ts.log_warning('       Point %i voltage is below the minimum voltage of the EUT.' % (line_to_test))
        ts.log_warning('       Setting the Line Segment End point to the minimum EUT voltage.')
        Vmax_pct = v_min_pct

    if Vmin_pct > v_max_pct:
        ts.log_warning('       Point %i voltage is above the maximum voltage of the EUT.' % (line_to_test-1))
        ts.log_warning('       Setting the Line Segment Start point to the maximum EUT voltage.')
        Vmin_pct = v_max_pct
    if Vmax_pct > v_max_pct:
        ts.log_warning('       Point %i voltage is above the maximum voltage of the EUT.' % (line_to_test))
        ts.log_warning('       Setting the Line Segment End point to the maximum EUT voltage.')
        Vmax_pct = v_max_pct

    voltage_pct = Vmin_pct + ((Vmax_pct-Vmin_pct)*voltage_pct_test_point/100.)
    return voltage_pct


def volt_var_set(v_nom=240., volt=None, var=None, v_deadband_max=None, v_deadband_avg=None, v_deadband_min=None,
                 Q_max_cap=None, Q_max_ind=None, k_varmax=None, k_varavg=None, k_varmin=None, manualcurve=None):

    v1=[0. for i in range(6)]
    v2=[0. for i in range(6)]
    v3=[0. for i in range(6)]
    v4=[0. for i in range(6)]
    q1=[0. for i in range(6)]
    q2=[0. for i in range(6)]
    q3=[0. for i in range(6)]
    q4=[0. for i in range(6)]

    # UL 1741 Test 1
    v1[1] = v_nom-(v_deadband_min/2.)-(Q_max_cap/k_varmax)
    v2[1] = v_nom-(v_deadband_min/2.)
    v3[1] = v_nom+(v_deadband_min/2.)
    v4[1] = (Q_max_cap/k_varmax)+v3[1]
    q1[1] = Q_max_cap
    q2[1] = 0.
    q3[1] = 0.
    q4[1] = Q_max_ind
    # UL 1741 Test 2
    v1[2] = v_nom-(v_deadband_avg/2.)-(Q_max_cap/k_varavg)
    v2[2] = v_nom-(v_deadband_avg/2.)
    v3[2] = v_nom+(v_deadband_avg/2.)
    v4[2] = (Q_max_cap/k_varavg)+v3[2]
    q1[2] = 0.5*Q_max_cap
    q2[2] = 0.
    q3[2] = 0.
    q4[2] = 0.5*Q_max_ind
    # UL 1741 Test 3
    v1[3] = v_nom-(v_deadband_max/2.)-(Q_max_cap/k_varmin)
    v2[3] = v_nom-(v_deadband_max/2.)
    v3[3] = v_nom+(v_deadband_max/2.)
    v4[3] = (Q_max_cap/k_varmin)+v3[3]
    q1[3] = 0.25*Q_max_cap
    q2[3] = 0.
    q3[3] = 0.
    q4[3] = 0.25*Q_max_ind
    # UL 1741 Test 4
    v1[4] = v2[2]-(Q_max_cap/k_varavg)
    v2[4] = v2[2]
    v3[4] = v3[2]
    v4[4] = v3[2]+(Q_max_cap/k_varavg)
    q1[4] = 0.5*Q_max_cap
    q2[4] = 0.05*Q_max_cap
    q3[4] = 0.05*Q_max_cap
    q4[4] = 0.5*Q_max_ind
    # UL 1741 Test 5
    v1[5] = v2[3]-(Q_max_cap/k_varmin)
    v2[5] = v3[3]
    v3[5] = v3[3]
    v4[5] = v3[3]+(Q_max_cap/k_varmin)
    q1[5] = 0.25*Q_max_cap
    q2[5] = 0.05*Q_max_ind
    q3[5] = 0.05*Q_max_ind
    q4[5] = 0.25*Q_max_ind

    # All points are in volts/vars at this point - must converter them to % of nameplate:
    for i in range(6):
        v1[i] = (100./v_nom)*v1[i]
        v2[i] = (100./v_nom)*v2[i]
        v3[i] = (100./v_nom)*v3[i]
        v4[i] = (100./v_nom)*v4[i]
        q1[i] = (100./Q_max_cap)*q1[i]
        q2[i] = (100./Q_max_cap)*q2[i]
        q3[i] = (100./Q_max_cap)*q3[i]
        q4[i] = (100./Q_max_cap)*q4[i]

    # output the volt-var curves for the 1741 tests
    for i in xrange(1,6):
        ts.log('Test %d: V1=%.3f, Q1=%.3f.' % (i, v1[i], q1[i]))
        ts.log('Test %d: V2=%.3f, Q2=%.3f.' % (i, v2[i], q2[i]))
        ts.log('Test %d: V3=%.3f, Q3=%.3f.' % (i, v3[i], q3[i]))
        ts.log('Test %d: V4=%.3f, Q4=%.3f.' % (i, v4[i], q4[i]))
        ts.log('***')

    # populate the volt and var libraries with the correct points based on the UL 1741 test number
    if manualcurve != 'Manual':
        test_num = ts.param_value('vv.settings.test_num')
        n_points = 4
        volt = {
            1: v1[test_num],
            2: v2[test_num],
            3: v3[test_num],
            4: v4[test_num],
            'index_start': 1,
            'index_count': 4,
            }

        var = {
            1: q1[test_num],
            2: q2[test_num],
            3: q3[test_num],
            4: q4[test_num],
            'index_start': 1,
            'index_count': 4,
            }

    ts.log('Voltage points: %s.' % volt)
    ts.log('Var points: %s.' % var)

    return (volt, var)


def test_run():

    result = script.RESULT_FAIL
    data = None
    trigger = None
    grid = None
    inv = None
    volt = {}
    var = {}
    disable = None

    try:
        # gridsim_v_nom = grid.v_nom()

        var_ramp_rate = ts.param_value('vv.settings.var_ramp_rate')  # time to ramp
        msa_var = ts.param_value('vv.settings.MSA_VAr')
        k_varmax = ts.param_value('vv.settings.k_varmax')
        v_deadband_min = ts.param_value('vv.settings.v_deadband_min')
        v_deadband_max = ts.param_value('vv.settings.v_deadband_max')
        manualcurve = ts.param_value('vv.settings.manualcurve')

        pretest_delay = ts.param_value('invt.pretest_delay')
        verification_delay = ts.param_value('invt.verification_delay')
        voltage_tests_per_line = ts.param_value('invt.voltage_tests_per_line')
        disable = ts.param_value('invt.disable')

        # initialize data acquisition system
        daq = das.das_init(ts)
        data = daq.data_init()
        trigger = daq.trigger_init()

        # UL 1741 SA Step 2: Set all AC source parameters to the nominal operating conditions for the EUT
        grid = gridsim.gridsim_init(ts)

        ts.log('********Parameters of the EUT*************')
        v_nom = 240.
        ts.log('Nominal AC Voltage (V): %.3f.' % v_nom)
        v_min = 211.
        v_max = 264.
        ts.log('AC Voltage Range with function enabled (V): %.3f to %.3f' % (v_min,v_max))
        ts.log('VAr Accuracy (VAr) - MSA_VAr: %.3f.' % msa_var)
        ts.log('Max reactive power ramp rate (VAr/s): %.3f.' % var_ramp_rate)
        Q_max_cap = 1600
        Q_max_ind = -1600  # negative
        ts.log('Minimum inductive (underexcited) reactive power - Q_max,ind: %.3f.' % Q_max_ind) # negative
        ts.log('Minimum capacitive (overexcited) reactive power - Q_max,cap: %.3f.' % Q_max_cap)
        ts.log('Maximum slope (VAr/V), K_varmax: %.3f.' % k_varmax)
        ts.log('Deadband range (V): [%.1f, %.1f].' % (v_deadband_min, v_deadband_max))
        ts.log('*******************************************')
        Q_min_cap = Q_max_cap/4.
        Q_min_ind = Q_max_ind/4. #negative
        v_min_dev = min(v_nom - v_min, v_max - v_nom)
        v_deadband_avg = (v_deadband_min + v_deadband_max)/2.
        k_varmin = Q_min_cap/(v_min_dev - v_deadband_max/2.)
        k_varavg = (k_varmin + k_varmax)/2.
        ts.log('Q_mid,cap = %.3f.' % Q_min_cap)
        ts.log('Q_mid,ind = %.3f.' % Q_min_ind)
        ts.log('K_varavg: %.3f.' % k_varavg)
        ts.log('K_varmin: %.3f.' % k_varmin)
        ts.log('Average voltage deadband: %.3f.' % v_deadband_avg)

        volt, var = volt_var_set(v_nom=240., volt=[], var=[], v_deadband_max=v_deadband_max,
                                 v_deadband_avg=v_deadband_avg, v_deadband_min=v_deadband_min, Q_max_cap=Q_max_cap,
                                 Q_max_ind=Q_max_ind, k_varmax=k_varmax, k_varavg=k_varavg,
                                 k_varmin=k_varmin, manualcurve=manualcurve)

        ######## Begin Test ########

        # the test points are on the (V,Q) points
        voltage_pct_test_points = np.linspace(0., 100., voltage_tests_per_line)
        ts.log('Test points will at %s %% of the volt-var curve segments.' % voltage_pct_test_points)

        lines_to_test = volt['index_count']+1  # There is 1 more line than there are (V,Q) points

        WMAXdch = 4.5
        WMAXch = -4.5

        for start_power in [WMAXdch, WMAXdch/2, 0, WMAXch/2, WMAXch]:

            if ts.confirm('Set EUT output power to %.3f.' % start_power) is False:
                ts.log('Aborted FW test because output power was not set.')

            if pretest_delay > 0:
                ts.log('    Waiting for pre-test delay of %d seconds' % pretest_delay)
                ts.sleep(pretest_delay)

            for j in xrange(lines_to_test):
                for i in voltage_pct_test_points:
                    #ts.log('    Testing the reactive power on curve segment %d at %d%% down the line segment.'
                    #       % (j+1,i))

                    # ts.log('volt = %s' % volt)
                    voltage_pct = grid_voltage_get(volt=volt, var=var, v_nom=v_nom,
                                                   line_to_test=j+1, voltage_pct_test_point=i)

                    if grid is not None:
                        #ts.log('        Setting ac voltage percentage = %.2f.%%. Simulator voltage = %.2f' %
                        #       (voltage_pct,(voltage_pct/100.)*gridsim_v_nom))

                        grid_sim_voltage = (voltage_pct/100.)*v_nom

                        gridsim_v_max = grid.v_max()

                        if grid_sim_voltage > gridsim_v_max:
                            grid.voltage(voltage=gridsim_v_max)
                            ts.log_warning('The grid simulator voltage is set to the simulator equipment limit.')
                        else:
                            grid.voltage(voltage=grid_sim_voltage)
                    else:
                        ts.confirm('Set ac voltage percentage to %.2f.%% with grid simulator voltage = %.2f' %
                                   (voltage_pct, (voltage_pct/100.)*v_nom))

                    #ts.log('        Waiting verification delay of %.3f' % (verification_delay))
                    time.sleep(verification_delay)

                    data.read()
                    #ts.log('das = %s' % data)
                    ts.log('volt, var = %.3f, %.3f' % (data.ac_voltage, data.ac_vars))

        result = script.RESULT_PASS

    except script.ScriptFail, e:
        reason = str(e)
        if reason:
            ts.log_error(reason)
    finally:
        if trigger:
            trigger.off()
        if disable == 'yes' and inv is not None:
            inv.volt_var.ModEna = 0
            inv.volt_var.write()

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

    sys.exit(rc)

info = script.ScriptInfo(name=os.path.basename(__file__), run=run, version='1.0.3')


info.param_group('vv', label='VV Configuration')
info.param_group('vv.settings', label='VV Settings')
info.param('vv.settings.var_ramp_rate', label='Maximum Ramp Rate (VAr/s)', default=1600,
           desc='Maximum Ramp Rate (VAr/s)')
info.param('vv.settings.MSA_VAr', label='Reactive Power Accuracy (VAr)', default=20,
           desc='Reactive Power Accuracy (VAr)')
info.param('vv.settings.k_varmax', label='Maximum Volt-Var curve slope (VAr/V)', default=800,
           desc='Maximum Volt-Var curve slope (VAr/V)')
info.param('vv.settings.v_deadband_min', label='Min deadband range (V)', default=2,
           desc='Min deadband voltage (V)')
info.param('vv.settings.v_deadband_max', label='Max deadband range (V)', default=10,
           desc='Max deadband voltage (V)')

# Define points for VV11 and VV12
info.param('vv.settings.manualcurve', label='Enter the Volt-Var Curves Manually?', default='Manual',
           values=['Manual','Enter Test Number'])
info.param('vv.settings.test_num', label='Enter the test number', default=1, values=[1,2,3,4,5],
           active='vv.settings.manualcurve', active_value=['Enter Test Number'],
           desc='Automatically calculates the volt-var curve points based on the test matrix.')

info.param('vv.settings.settling_time', label='Volt-Var Settling Time (s)', default=4.,
           desc='Volt-Var Settling Time (s). This determines the test duration')

info.param_group('invt', label='VV Timing and Pass/Fail Parameters')
info.param('invt.pretest_delay', label='Pre-Test Delay (seconds)', default=3,
           desc='Delay before beginning the test.')
info.param('invt.var_range', label='Var Pass/Fail Screen', default=15.,
           desc='+/- %Vars for Pass/Fail Screen (i.e., "5" = +/-5% of Max EUT Var Output)')
info.param('invt.verification_delay', label='Verification Delay (seconds)', default=5,
           desc='Wait time allowance before assigning failure for the time parameters.')
info.param('invt.posttest_delay', label='Post-Test Delay (seconds)', default=0,
           desc='Delay after finishing the test.')
info.param('invt.voltage_tests_per_line', label='Number of test points per volt-var line segment', default=3,
           desc='Number of test points per volt-var line segment (minimum = 3 per UL 1741)')
info.param('invt.test_on_vv_points', label='Test on the (V,Q) points?', default='No', values=['Yes', 'No'],
           desc='Test ac voltages that include the (V,Q) points or on the line segments?')

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



