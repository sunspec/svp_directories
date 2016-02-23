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

# Test script for UL 1741 SA Volt/Var Function

#!C:\Python27\python.exe

import sys
import os
import math
import time
import traceback
import sunspec.core.client as client
import numpy as np

import script

import inverter
import terrasas
import gridsim
import das
import pvsim

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

# returns: current ac voltage
def get_ac_voltage_pct(inv, data=None):
    try:

        #only use the das (data acquisition system) if it is available
        if data:
            data.read()
            gridVraw = data.ac_voltage
        # without the das use the EUT to report the power level
        else:
            inv.inverter.read()
            gridVraw = float(inv.inverter.PhVphA)

        inv.settings.read()
        Vgrid_nom = float(inv.settings.VRef)

        return (gridVraw/Vgrid_nom)*100.0

    except Exception, e:
        raise script.ScriptFail('Unable to get ac voltage from das or EUT: %s' % str(e))

def var_pass_fail_band(inv, volt=None, var=None, n_points=4, var_range=50., deptRef = 2, data=None):

    varTarg = None
    var_upper = None
    var_lower = None

    #Check to be sure the voltages are monotonically increasing.
    for i in xrange(1, n_points-1):
        if volt[i] > volt[i+1]:
            ts.log_error('Voltages are not monotonically increasing in volt-var curve.')
        break

    lots_of_output = False #Flag to turn on data dumps to help debugging
    if lots_of_output:
        ts.log_debug('deptRef: %s' % deptRef)

    # get var settings
    try:
        inv.nameplate.read()
        max_Var = float(inv.nameplate.VArRtgQ1) #Q1 is pos
        max_VA = float(inv.nameplate.VARtg) #Q1 is pos
        max_W = float(inv.nameplate.WRtg) #Q1 is pos
        if lots_of_output:
            ts.log_debug('max_Var = %0.3f, max_VA = %0.3f, and max_W = %0.3f.' % (max_Var, max_VA, max_W))
    except Exception, e:
        ts.log_error('Unable to get var limits from EUT: %s' % str(e))
        raise
        #return script.RESULT_FAIL

    #Get grid voltage to determine the proper EUT vars
    gridV = get_ac_voltage_pct(inv, data)

    if deptRef == inverter.VOLTVAR_WMAX:
        if gridV < volt[1]: #Vgrid is below the 1st point - extrapolate
            varAval = math.sqrt(math.pow(max_VA,2) - math.pow(max_W,2)) # units of vars
            varAvalTargPct = var[1]/100.
            varTarg = varAval*varAvalTargPct # units of vars
            var_upper = varTarg + var_range*max_Var/100. #units of vars #var_range is %max_Var
            var_lower = varTarg - var_range*max_Var/100. #units of vars #var_range is %max_Var
            if lots_of_output:
                ts.log_debug('Low')
                ts.log_debug('varAval, varAvalTarg Fraction, varTarg, var_upper, var_lower')
                ts.log_debug('%.3f, %.3f, %.3f, %.3f, %.3f' %
                             (varAval, varAvalTargPct, varTarg, var_upper, var_lower))
        elif gridV > volt[n_points]: #Vgrid is above the last point - extrapolate
            varAval = math.sqrt(math.pow(max_VA,2) - math.pow(max_W,2)) # units of vars
            varAvalTargPct = var[n_points]/100.
            varTarg = varAval*varAvalTargPct # units of vars
            var_upper = varTarg + var_range*max_Var/100. #units of vars #var_range is %max_Var
            var_lower = varTarg - var_range*max_Var/100. #units of vars #var_range is %max_Var
            if lots_of_output:
                ts.log_debug('High')
                ts.log_debug('varAval, varAvalTarg Fraction, varTarg, var_upper, var_lower')
                ts.log_debug('%.3f, %.3f, %.3f, %.3f, %.3f' %
                             (varAval, varAvalTargPct, varTarg, var_upper, var_lower))
        else:
            # pointwise algorithm to find target vars
            for i in xrange(1, n_points):
                if lots_of_output:
                    ts.log_debug('Grid voltage is %.3f' % (gridV))
                    ts.log_debug('i = %d' % i)
                    ts.log_debug('gridV >= volt[i] and gridV <= volt[i+1]')
                    ts.log_debug('%.3f >= %.3f and %.3f <= %.3f' % (gridV, volt[i], gridV, volt[i+1]))

                if gridV >= volt[i] and gridV <= volt[i+1]: #curve interpolation
                    varAval = math.sqrt(math.pow(max_VA,2) - math.pow(max_W,2)) # units of vars
                    #varTarg = Qi + (Qi+1 - Qi)*((gridV - Vi)/(Vi+1 - Vi))
                    varAvalTargPct = (var[i] + (var[i+1] - var[i]) * ((gridV - volt[i])/(volt[i+1] - volt[i])))/100.
                    varTarg = varAval*varAvalTargPct # units of vars
                    var_upper = varTarg + var_range*max_Var/100. #units of vars #var_range is %max_Var
                    var_lower = varTarg - var_range*max_Var/100. #units of vars #var_range is %max_Var
                    if lots_of_output:
                        ts.log_debug('Interpolated')
                        ts.log_debug('varAval, varAvalTarg Fraction, varTarg, var_upper, var_lower')
                        ts.log_debug('%.3f, %.3f, %.3f, %.3f, %.3f' %
                                     (varAval, varAvalTargPct, varTarg, var_upper, var_lower))
                    break

    elif deptRef == inverter.VOLTVAR_VARMAX:
        if gridV < volt[1]: #Vgrid is below the 1st point - extrapolate
            varTargPct = var[1]/100.
            varTarg = max_Var*varTargPct # units of vars
            var_upper = varTarg + var_range*max_Var/100. #units of vars #var_range is %max_Var
            var_lower = varTarg - var_range*max_Var/100. #units of vars #var_range is %max_Var
            if lots_of_output:
                print 'volt[1], var[1]'
                print volt[1], var[1]
                ts.log_debug('Low')
                ts.log_debug('varTarg Fraction, varTarg, var_upper, var_lower')
                ts.log_debug('%.3f, %.3f, %.3f, %.3f' % (varTargPct, varTarg, var_upper, var_lower))
        elif gridV > volt[n_points]: #Vgrid is above the last point - extrapolate
            varTargPct = var[n_points]/100.
            varTarg = max_Var*varTargPct # units of vars
            var_upper = varTarg + var_range*max_Var/100. #units of vars #var_range is %max_Var
            var_lower = varTarg - var_range*max_Var/100. #units of vars #var_range is %max_Var
            if lots_of_output:
                print 'volt[n_points], var[n_points]'
                print volt[n_points], var[n_points]
                ts.log_debug('High')
                ts.log_debug('varTarg Fraction, varTarg,  var_upper, var_lower')
                ts.log_debug('%.3f, %.3f, %.3f, %.3f' % (varTargPct, varTarg, var_upper, var_lower))
        else:
            # pointwise algorithm to find target vars
            for i in xrange(1, n_points):
                if lots_of_output:
                    ts.log_debug('Grid voltage is %.3f' % (gridV))
                    ts.log_debug('i = %d' % i)
                    ts.log_debug('gridV >= volt[i] and gridV <= volt[i+1]')
                    ts.log_debug('%.3f >= %.3f and %.3f <= %.3f' % (gridV, volt[i], gridV, volt[i+1]))
                    #ts.log('var_range = %.3f' % var_range)
                if gridV >= volt[i] and gridV <= volt[i+1]: #curve interpolation
                    #varTarg = Qi + (Qi+1 - Qi)*((gridV - Vi)/(Vi+1 - Vi))
                    varTargPct = (var[i]+(var[i+1]-var[i])*((gridV-volt[i])/(volt[i+1]-volt[i])))/100.
                    varTarg = max_Var*varTargPct
                    var_upper = varTarg + var_range*max_Var/100. #var_range is %VarAval
                    var_lower = varTarg - var_range*max_Var/100. #var_range is %VarAval
                    if lots_of_output:
                        print 'var[i], var[i+1], var[i], gridV, volt[i], volt[i+1], volt[i]'
                        print var[i], var[i+1], var[i], gridV, volt[i], volt[i+1], volt[i]
                        print 'var[i] + (var[i+1]-var[i])*((gridV-volt[i])/(volt[i+1]-volt[i]))'
                        print var[i] + (var[i+1]-var[i])*((gridV-volt[i])/(volt[i+1]-volt[i]))
                        ts.log_debug('Interpolated - VV12')
                        ts.log_debug('varTarg Fraction, varTarg, var_upper, var_lower')
                        ts.log_debug('%.3f, %.3f, %.3f, %.3f' % (varTargPct, varTarg, var_upper, var_lower))
                    break


    elif deptRef == inverter.VOLTVAR_VARAVAL:
        fixedVarPct = var[1]/100. ###NOTE: fixedVarPct is a decimal, not in units of percent
        if volt[1] == 1: # %VarAval
            varAval = math.sqrt(math.pow(max_VA,2) - math.pow(max_W,2)) # units of vars
            varTarg = varAval*fixedVarPct # units of vars
            var_upper = varTarg + var_range/100.*max_Var #units of vars #var_range is %max_Var
            var_lower = varTarg - var_range/100.*max_Var #units of vars #var_range is %max_Var
        elif volt[1] == 2: # %WMax
            varTarg = max_W*fixedVarPct
            var_upper = varTarg + var_range/100.*max_Var #var_range is %max_Var
            var_lower = varTarg - var_range/100.*max_Var #var_range is %max_Var
        else: # %VarMax
            varTarg = max_Var*fixedVarPct # units of vars
            var_upper = varTarg + var_range/100.*max_Var #var_range is %max_Var
            var_lower = varTarg - var_range/100.*max_Var #var_range is %max_Var

    else:
        varTarg = 0
        var_upper = varTarg + var_range/100.*max_Var #var_range is %max_Var
        var_lower = varTarg - var_range/100.*max_Var #var_range is %max_Var

    return (varTarg, var_upper, var_lower)

def grid_voltage_get(inv, volt=None, var=None, v_nom = 240., line_to_test=1, voltage_pct_test_point=0.):

    v_min_pct = 100.*(float(inv.settings.VMin)/v_nom)
    v_max_pct = 100.*(float(inv.settings.VMax)/v_nom)
    v_min_lvrt_pct = v_min_pct # not implemented now because it's not in many EUT modbus mappings
    v_max_lvrt_pct = v_max_pct # not implemented now because it's not in many EUT modbus mappings

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

    #ts.log_debug('Min Curve Voltage Percentage = %0.2f, Max Curve Voltage Percentage = %0.2f, ' % (Vmin_pct, Vmax_pct))
    #ts.log_debug('AC Voltage Percentage= %0.2f' % voltage_pct)

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
    pv = None
    inv = None
    volt = {}
    var = {}
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

        var_ramp_rate = ts.param_value('vv.settings.var_ramp_rate')  # time to ramp
        msa_var = ts.param_value('vv.settings.MSA_VAr')
        v_low = ts.param_value('vv.settings.v_low')
        v_high = ts.param_value('vv.settings.v_high')
        k_varmax = ts.param_value('vv.settings.k_varmax')
        v_deadband_min = ts.param_value('vv.settings.v_deadband_min')
        v_deadband_max = ts.param_value('vv.settings.v_deadband_max')
        manualcurve = ts.param_value('vv.settings.manualcurve')
        settling_time = ts.param_value('vv.settings.settling_time')

        vv_mode = ts.param_value('vv.settings.vv_mode')
        if vv_mode == 'VV11 (watt priority)':
            deptRef = inverter.VOLTVAR_WMAX
        elif vv_mode == 'VV12 (var priority)':
            deptRef = inverter.VOLTVAR_VARMAX
        elif vv_mode == 'VV13 (fixed var)':
            deptRef = inverter.VOLTVAR_VARAVAL
            fixedVar = ts.param_value('vv.settings.fixedVar')
            var[1] = fixedVar # Not very clean - will pull 'points' info out later for pass/fail bounds
            fixedVarRef = ts.param_value('vv.settings.fixedVarRef')
            if fixedVarRef == '%VarAval':
                volt[1] = 1 # Not very clean - will pull 'points' info out later for pass/fail bounds
            elif fixedVarRef ==  '%WMax':
                volt[1] = 2 # Not very clean - will pull 'points' info out later for pass/fail bounds
            else: #fixedVarRef == '%VarMax'
                volt[1] = 3 # Not very clean - will pull 'points' info out later for pass/fail bounds
        else:
            deptRef = 4

        if vv_mode == 'VV11 (watt priority)' or vv_mode == 'VV12 (var priority)':
            curve_num = ts.param_value('vv.settings.curve_num')
            volt = ts.param_value('vv.curve.volt')
            var = ts.param_value('vv.curve.var')
            if manualcurve is 'Manual':
                n_points = ts.param_value('vv.settings.n_points')
            else:
                n_points = 4

        var_range = ts.param_value('invt.var_range')
        pretest_delay = ts.param_value('invt.pretest_delay')
        verification_delay = ts.param_value('invt.verification_delay')
        posttest_delay = ts.param_value('invt.posttest_delay')
        voltage_tests_per_line = ts.param_value('invt.voltage_tests_per_line')
        test_on_vv_points = ts.param_value('invt.test_on_vv_points')
        disable = ts.param_value('invt.disable')

        ''' UL 1741 requirements from the Feb 2015 Draft
        1. Connect the EUT according to the Requirements in Sec. 4.3.1 and specifications provided by the manufacturer.
        2. Set all AC source parameters to the nominal operating conditions for the EUT. Frequency is set at nominal
        and held at nominal throughout this test. Set the input power to the value to Prated.
        3. Turn on the EUT.  Set all R21-1-L/HVRT parameters to the widest range of adjustability possible with the
        R21-1-VV11 enabled.
        4. If the EUT has the ability to set "Real Power Priority" or "Reactive Power Priority", select
        "Reactive Power Priority".
        5. Set the EUT to provide reactive power according to the Q(V) characteristic defined in Test 1 in Table 10.
        6. Begin recording the time domain response of the EUT AC voltage and current, and DC voltage and current.
        Step down the AC voltage until at least three points  are recorded in each line segment of the characteristic
        curve or the EUT trips from the LVRT must trip requirements.  Continue recording the time domain response for
        at least twice the settling time after each voltage step.
        7. Repeat Step 6, raising the AC voltage until at least three points  are recorded in each line segment of the
        characteristic curve or the EUT trips from HVRT must trip requirements.
        8. Repeat steps 6 - 7 four more times, for a total of five sweeps  of the Q(V) curve.
        9. Repeat test steps 5 - 8 at power levels 20% and 60% of Prated by reducing the DC voltage of the Input
        Source.
        10. Repeat steps 6 - 9 for the remaining tests in Table 10.
        '''

        # initialize data acquisition system
        daq = das.das_init(ts)
        data = daq.data_init()
        trigger = daq.trigger_init()

        # initialize pv simulation
        pv = pvsim.pvsim_init(ts)
        pv.power_on()

        # UL 1741 SA Step 2: Set all AC source parameters to the nominal operating conditions for the EUT
        # initialize grid simulation
        grid = gridsim.gridsim_init(ts)
        if grid:
            gridsim_v_nom = grid.v_nom()

        #Put inverter scan after grid and PV simulation setup so that Modbus registers can be read.
        ts.log('Scanning inverter')
        inv = client.SunSpecClientDevice(ifc_type, slave_id=slave_id, name=ifc_name, baudrate=baudrate, parity=parity,
                                         ipaddr=ipaddr, ipport=ipport)

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
            inv.controls.read()
            inv.settings.read()
        except Exception, e:
            raise script.ScriptFail('Unable to get parameters from EUT: %s' % str(e))

        ts.log('********Parameters of the EUT*************')
        S_rated = float(inv.nameplate.VARtg)
        ts.log('Apparent Power Rating (VA) - S_rated: %.3f.' % S_rated)
        ts.log('EUT Input Power Rating (W) - P_rated: %.3f.' % float(inv.nameplate.WRtg))
        ts.log('DC Voltage range with function enabled (V) - [V_low, V_high]: [%.1f, %.1f].' % (v_low, v_high))
        v_nom = float(inv.settings.VRef)
        ts.log('Nominal AC Voltage (V): %.3f.' % v_nom)
        v_min = float(inv.settings.VMin)
        v_max = float(inv.settings.VMax)
        ts.log('AC Voltage Range with function enabled (V): %.3f to %.3f' % (v_min,v_max))
        ts.log('VAr Accuracy (VAr) - MSA_VAr: %.3f.' % msa_var)
        ts.log('Max reactive power ramp rate (VAr/s): %.3f.' % var_ramp_rate)
        Q_max_cap = float(inv.settings.VArMaxQ1)
        Q_max_ind = float(inv.settings.VArMaxQ4) # negative
        ts.log('Minimum inductive (underexcited) reactive power - Q_max,ind: %.3f.' % Q_max_ind) # negative
        ts.log('Minimum capacitive (overexcited) reactive power - Q_max,cap: %.3f.' % Q_max_cap)
        ts.log('Maximum slope (VAr/V), K_varmax: %.3f.' % k_varmax)
        ts.log('Deadband range (V): [%.1f, %.1f].' % (v_deadband_min, v_deadband_max))
        ts.log('*******************************************')
        Q_min_cap = Q_max_cap/4.
        Q_min_ind = Q_max_ind/4. #negative
        #v_avg = (v_min + v_max)/2.
        v_min_dev = min(v_nom - v_min, v_max - v_nom)
        v_deadband_avg = (v_deadband_min + v_deadband_max)/2.
        k_varmin = Q_min_cap/(v_min_dev - v_deadband_max/2.)
        k_varavg = (k_varmin + k_varmax)/2.
        ts.log('Q_mid,cap = half the EUT capacitive VAr range: %.3f.' % Q_min_cap)
        ts.log('Q_mid,ind = half the EUT inductive VAr range: %.3f.' % Q_min_ind)
        #ts.log('V_avg = halfway point for the operating ac voltage of the function: %.3f.' % v_avg)
        ts.log('K_varavg: %.3f.' % k_varavg)
        ts.log('K_varmin: %.3f.' % k_varmin)
        ts.log('Average voltage deadband: %.3f.' % v_deadband_avg)

        ts.log('********Required Test Points for UL 1741*************')
        volt, var = volt_var_set(v_nom=240., volt=volt, var=var, v_deadband_max=v_deadband_max,
                                 v_deadband_avg=v_deadband_avg, v_deadband_min=v_deadband_min, Q_max_cap=Q_max_cap,
                                 Q_max_ind=Q_max_ind, k_varmax=k_varmax, k_varavg=k_varavg,
                                 k_varmin=k_varmin, manualcurve=manualcurve)

        ######## Begin Test ########
        # UL 1741 SA Step 3: if applicable set LVRT/HVRT settings here.

        # Request status from EUT and display vars
        var_original = inverter.get_var(inv, das=data)
        ts.log('Current reactive power is %.3f VAr' % var_original)

        # UL 1741 SA Step 4 (using deptRef) and Step 5 (setting the Q(V) characteristic curve)
        inverter.set_volt_var(inv, volt=volt, var=var, n_points=n_points,
                              curve_num=curve_num, deptRef=deptRef, enable=1)

        #voltage_pct_test_points = np.linspace(0., 100., voltage_tests_per_line)
        #ts.log('test_on_vv_points == Yes: %s' % voltage_pct_test_points)
        #voltage_pct_test_points = np.linspace(0., 100., voltage_tests_per_line+2)
        #voltage_pct_test_points = voltage_pct_test_points[1:-1]
        #ts.log('test_on_vv_points == No: %s' % voltage_pct_test_points)

        if test_on_vv_points == 'Yes':
            # the test points are on the (V,Q) points
            voltage_pct_test_points = np.linspace(0., 100., voltage_tests_per_line)
            ts.log('Test points will at %s %% of the volt-var curve segments.' % voltage_pct_test_points)
        else:
            # the test points are not on the (V,Q) points
            voltage_pct_test_points = np.linspace(0., 100., voltage_tests_per_line+2)
            voltage_pct_test_points = voltage_pct_test_points[1:-1]
            ts.log('Test points will at %s %% of the volt-var curve segments.' % voltage_pct_test_points)

        lines_to_test = volt['index_count']+1 # There are 1 more line than there are (V,Q) points

        for irradiance in [1000, 200, 600]:
            ts.log('DC power level is %.3f %% nameplate, so the simulator power level is set to %.1f W/m^2' %
                   (irradiance/10., irradiance))
            pv.irradiance_set(irradiance=irradiance)

            for repeats in xrange(1,6): # UL 1741 Step 8: Repeat the test 5 times
                ts.log('    Running volt-var sweep number %d.' % (repeats))

                if pretest_delay > 0:
                    ts.log('    Waiting for pre-test delay of %d seconds' % pretest_delay)
                    ts.sleep(pretest_delay)

                for j in xrange(lines_to_test):
                    for i in voltage_pct_test_points:
                        ts.log('    Testing the reactive power on curve segment %d at %d%% down the line segment.'
                               % (j+1,i))
                        voltage_pct = grid_voltage_get(inv, volt=volt, var=var, v_nom=v_nom,
                                                       line_to_test=j+1, voltage_pct_test_point=i)

                        # Set grid simulator voltage immediately prior to triggering
                        if grid is not None:
                            ts.log('        Setting ac voltage percentage = %.2f.%%. Simulator voltage = %.2f' %
                                   (voltage_pct,(voltage_pct/100.)*gridsim_v_nom))

                            grid_sim_voltage = (voltage_pct/100.)*gridsim_v_nom
                            gridsim_v_max = grid.v_max()
                            if grid_sim_voltage > gridsim_v_max:
                                grid.voltage(voltage=gridsim_v_max)
                                ts.log_warning('The grid simulator voltage is set to the simulator equipment limit.')
                            else:
                                grid.voltage(voltage=grid_sim_voltage)
                        else:
                            ts.confirm('Set ac voltage percentage to %.2f.%% with grid simulator voltage = %.2f' %
                                   (voltage_pct,(voltage_pct/100.)*gridsim_v_nom))

                        if trigger:
                            trigger.on()
                        start_time = time.time()

                        inv.nameplate.read()
                        VarAval = inv.nameplate.VArRtgQ1

                        varTarg, var_upper, var_lower = var_pass_fail_band(inv, volt=volt, var=var, n_points=n_points,
                                                                        var_range=var_range, deptRef=deptRef, das=das)
                        ts.log('        Target vars: %.3f. Pass limits for screening: lower = %.3f  upper = %.3f' %
                               (varTarg, var_lower, var_upper))

                        ts.log('        Waiting settling time of %.3f' % (settling_time))
                        time.sleep(settling_time-0.25) # computer specific time correction

                        current_vars = inverter.get_var(inv, das=data)

                        # Cheat a little since var is unsigned from das (and inverter?)
                        if varTarg < 0 and current_vars > 0:
                            current_vars = -current_vars

                        elapsed_time = time.time()-start_time
                        ts.log('        Var Target = %.3f [%.3f to %.3f], Vars = %.3f (Total Error = %.3f%%), '
                               'Time: %0.3f seconds.' %
                               (varTarg, var_lower, var_upper, current_vars, (current_vars - varTarg)/VarAval*100.0,
                                elapsed_time))

                        # if vars out of range
                        if current_vars < var_lower or current_vars > var_upper:
                            ts.log('        Acceptable reactive power levels were not reacted after the settling time.')
                            raise script.ScriptFail()
                        else:
                            # Criteria
                            # For each voltage step, the EUT reactive power measurement should remain within the
                            # manufacturers stated accuracy of the Q(V) value except when the voltage is changing.
                            # The EUT shall obtain the Q(V) characteristic within its stated accuracy within the
                            # stated settling time.
                            ts.log('        Reactive power level was within the bounds after the settling time.')
                        if trigger:
                            trigger.off()
                            if posttest_delay > 0:
                                ts.log('        Waiting for post-test delay of %d seconds' % posttest_delay)
                                ts.sleep(posttest_delay)

        result = script.RESULT_PASS

    except script.ScriptFail, e:
        reason = str(e)
        if reason:
            ts.log_error(reason)
    finally:
        if trigger:
            trigger.off()
        if pv:
            pv.close()
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


info.param_group('vv', label='VV Configuration')
info.param_group('vv.settings', label='VV Settings')
info.param('vv.settings.vv_mode', label='Volt-Var Mode', default='VV12 (var priority)',
           values=['VV11 (watt priority)','VV12 (var priority)'])
           #values=['VV11 (watt priority)', 'VV12 (var priority)', 'VV13 (fixed var)', 'VV14 (no volt-var)'])
info.param('vv.settings.var_ramp_rate', label='Maximum Ramp Rate (VAr/s)', default=1600,
           desc='Maximum Ramp Rate (VAr/s)')
info.param('vv.settings.MSA_VAr', label='Reactive Power Accuracy (VAr)', default=20,
           desc='Reactive Power Accuracy (VAr)')
info.param('vv.settings.v_low', label='Min dc voltage range with function enabled (V)', default=200,
           desc='Min dc voltage range with function enabled (V)')
info.param('vv.settings.v_high', label='Max dc voltage range with function enabled (V)', default=600,
           desc='Max dc voltage range with function enabled (V)')
info.param('vv.settings.k_varmax', label='Maximum Volt-Var curve slope (VAr/V)', default=800,
           desc='Maximum Volt-Var curve slope (VAr/V)')
info.param('vv.settings.v_deadband_min', label='Min deadband range (V)', default=2,
           desc='Min deadband voltage (V)')
info.param('vv.settings.v_deadband_max', label='Max deadband range (V)', default=10,
           desc='Max deadband voltage (V)')

# Define points for VV11 and VV12
info.param('vv.settings.curve_num', label='Curve number (1-4)', default=1, values=[1,2,3,4])
info.param('vv.settings.n_points', label='Number of (Volt, VAr) pairs (2-10)', default=4, values=[2,3,4,5,6,7,8,9,10],
           active='vv.settings.vv_mode',  active_value=['VV11 (watt priority)', 'VV12 (var priority)'])
info.param('vv.settings.manualcurve', label='Enter the Volt-Var Curves Manually?', default='Manual',
           values=['Manual','Enter Test Number'])
info.param('vv.settings.test_num', label='Enter the UL 1741 test number', default=1, values=[1,2,3,4,5],
           active='vv.settings.manualcurve', active_value=['Enter Test Number'],
           desc='Automatically calculates the volt-var curve points based on the UL 1741 SA procedure.')

info.param('vv.settings.settling_time', label='Volt-Var Settling Time (s)', default=4.,
           desc='Volt-Var Settling Time (s). This determines the test duration')

info.param_group('vv.curve', label='VV Curve Points', index_count='vv.settings.n_points', index_start=1,
                 active='vv.settings.manualcurve', active_value=['Manual'])
info.param('vv.curve.volt', label='Volt', default=100.,
           desc='Volt curve point')
info.param('vv.curve.var', label='VAr', default=0.,
           desc='VAr curve point')

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
info.param('invt.disable', label='Disable volt-var function at end of test?', default='No', values=['Yes', 'No'])

# Grid simulator
gridsim.params(info)

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



