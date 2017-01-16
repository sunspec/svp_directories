
# #!C:\Python27\python.exe

import sys
import os
import traceback
import gridsim
import pvsim
import das
import der
import script

'''
    Open questions:

    - What should the sign of q_max_ind be? Currently implemented assuming -.

'''

test_labels = {
    1: 'Test 1 - Most Aggressive',
    2: 'Test 2 - Average',
    3: 'Test 3 - Least Aggressive',
    'Test 1 - Most Aggressive': [1],
    'Test 2 - Average': [2],
    'Test 3 - Least Aggressive: 3': [3],
    'All': [1, 2, 3]
}

def segment_points(start, end, count):
    ts.log('points - %s %s' % (str(start), str(end)))
    interval = (end - start)/(count + 1)
    points = [start]
    last = start
    for i in range(count):
        last = last + interval
        points.append(last)
    points.append(end)
    return points

def voltage_sample_points(v, segment_count=3):
    points = segment_points(v[0], v[1], segment_count)[1:]
    points.extend(segment_points(v[1], v[2], segment_count)[1:])
    points.extend(segment_points(v[2], v[3], segment_count)[1:])
    points.extend(segment_points(v[3], v[4], segment_count)[1:])
    points.extend(segment_points(v[4], v[5], segment_count)[1:-1])
    return points

def test_run():

    result = script.RESULT_FAIL
    daq = None
    pv = None
    grid = None

    try:
        # read test parameters
        tests_param = ts.param_value('general.tests')

        s_rated = ts.param_value('ratings.s_rated')
        p_rated = ts.param_value('ratings.p_rated')
        v_dc_min = ts.param_value('ratings.v_dc_min')  ##
        v_dc_max = ts.param_value('ratings.v_dc_max')  ##
        v_nom = ts.param_value('ratings.v_nom')
        v_min = ts.param_value('ratings.v_min')
        v_max = ts.param_value('ratings.v_max')
        #v_msa = ts.param_value('ratings.v_msa')
        var_msa = ts.param_value('ratings.var_msa')
        var_ramp_max = ts.param_value('ratings.var_ramp_max')
        q_max_cap = ts.param_value('ratings.q_max_cap')
        q_max_ind = ts.param_value('ratings.q_max_ind')
        k_var_max = ts.param_value('ratings.k_var_max')
        deadband_min = ts.param_value('ratings.deadband_min')
        deadband_max = ts.param_value('ratings.deadband_max')
        t_settling = ts.param_value('ratings.t_settling')
        power_priority = ts.param_value('ratings.power_priority')

        p_min_pct = ts.param_value('srd.p_min_pct')
        p_max_pct = ts.param_value('srd.p_max_pct')
        k_var_min_srd = ts.param_value('srd.k_var_min')
        try:
            k_var_min = float(k_var_min_srd)
        except ValueError:
            k_var_min = None
        segment_point_count = ts.param_value('srd.segment_point_count')

        # set power priorities to be tested
        if power_priority == 'Both':
            power_priorities = ['Active', 'Reactive']
        else:
            power_priorities = [power_priority]

        # default power range
        p_min = p_rated * .2
        p_max = p_rated

        # use values from SRD, if supplied
        if p_min_pct is not None:
            p_min = p_rated * (p_min_pct/100.)
        if p_max is not None:
            p_max = p_rated * (p_max_pct/100.)
        p_avg = (p_min + p_max)/2

        q_min_cap = q_max_cap/4
        q_min_ind = q_max_ind/4
        v_dev = min(v_nom - v_min, v_max - v_nom)
        # calculate k_var_min if not suppied in the SRD
        if k_var_min is None:
            k_var_min = (q_max_cap/4)/(v_dev - deadband_max/2)
        k_var_avg = (k_var_min + k_var_max)/2
        deadband_avg = (deadband_min + deadband_max)/2

        # list of active tests
        active_tests = test_labels[tests_param]

        # create test curves based on input parameters
        tests = [0] * 4

        '''
        The script only sets points 1-4 in the EUT, however they use v[0] and v[5] for testing purposes to define
        n points on the line segment to verify the reactive power
        '''
        # Test 1 - Characteristic 1 "Most Aggressive" Curve
        q = [0] * 5
        q[1] =q_max_cap    # Q1
        q[2] = 0
        q[3] = 0
        q[4] = q_max_ind
        v = [0] * 6
        v[2] = v_nom - deadband_min/2
        v[1] = v[2] - abs(q[1])/k_var_max
        v[0] = v_min
        v[3] = v_nom + deadband_min/2
        v[4] = v[3] + abs(q[4])/k_var_max
        v[5] = v_max

        tests[1] = [list(v), list(q)]

        # Test 2 - Characteristic 2 "Average" Curve
        q = [0] * 5
        q[1] = q_max_cap * .5
        q[2] = 0
        q[3] = 0
        q[4] = q_max_ind * .5
        v = [0] * 6
        v[2] = v_nom - deadband_avg/2
        v[1] = v[2] - abs(q[1])/k_var_avg
        v[0] = v_min
        v[3] = v_nom + deadband_avg/2
        v[4] = v[3] + abs(q[4])/k_var_avg
        v[5] = v_max
        tests[2] = [list(v), list(q)]

        # Test 3 - Characteristic 3 "Least Aggressive" Curve
        q = [0] * 5
        q[1] = q_min_cap
        q[2] = 0
        q[3] = 0
        q[4] = q_min_ind
        v = [0] * 6
        v[0] = v_min
        v[2] = v_nom - deadband_min/2
        v[3] = v_nom + deadband_min/2
        if k_var_min == 0:
            v[1] = 0.99*v[2]
            v[4] = 1.01*v[3]
        else:
            v[1] = v[2] - abs(q[1])/k_var_min
            v[4] = v[3] + abs(q[4])/k_var_min
        v[5] = v_max
        tests[3] = [list(v), list(q)]

        ts.log('tests = %s' % (tests))

        # list of tuples each containing (power level as % of max, # of test at power level)
        power_levels = [(1, 3), ((p_min/p_max), 3), (.66, 5)]

        '''
        1) Connect the EUT and measurement equipment according to the requirements in Sections 4 and 5 of
        IEEE Std 1547.1-2005 and specifications provided by the manufacturer.
        '''
        '''
        2) Set all AC source parameters to the nominal operating conditions for the EUT. Frequency is set at nominal
        and held at nominal throughout this test. Set the EUT power to Pmax.
        '''
        # grid simulator is initialized with test parameters and enabled
        grid = gridsim.gridsim_init(ts)

        # pv simulator is initialized with test parameters and enabled
        pv = pvsim.pvsim_init(ts)
        pv.power_set(p_max)
        pv.power_on()

        # initialize data acquisition
        daq = das.das_init(ts)

        '''
        3) Turn on the EUT. Set all L/HVRT parameters to the widest range of adjustability possible with the
        VV Q(V) enabled. The EUT's range of disconnect settings may depend on which function(s) are enabled.
        '''
        # it is assumed the EUT is on
        eut = der.der_init(ts)
        eut.config()

        for priority in power_priorities:
            '''
            4) If the EUT has the ability to set 'Active Power Priority' or 'Reactive Power Priority', select Priority
            being evaluated.
            '''
            '''
            5) Set the EUT to provide reactive power according to the Q(V) characteristic defined in Test 1 in
            Table SA13.1.
            '''
            for test in active_tests:
                ts.log('Starting test - %s' % (test_labels[test]))

                # create voltage settings along all segments of the curve
                v = tests[test][0]
                q = tests[test][1]
                voltage_points = voltage_sample_points(v, segment_point_count)
                ts.log('Voltage test points = %s' % (voltage_points))

                # set dependent reference type
                if priority == 'Active':
                    dept_ref = 'VAR_AVAL_PCT'
                elif priority == 'Reactive':
                    dept_ref = 'VAR_MAX_PCT'
                else:
                    raise script.ScriptFail('Unknown power priority setting: %s')

                # set volt/var curve
                eut.volt_var_curve(1, params={
                    # convert curve points to percentages and set DER parameters
                    'v': [v[1]/v_nom*100.0, v[2]/v_nom*100.0, v[3]/v_nom*100.0, v[4]/v_nom*100.0],
                    'var': [q[1]/q_max_cap*100.0, q[2]/q_max_cap*100.0, q[3]/q_max_cap*100.0, q[4]/q_max_cap*100.0],
                    'Dept_Ref': dept_ref
                })
                # enable volt/var curve
                eut.volt_var(params={
                    'Ena': True,
                    'ActCrv': 1
                })

                for level in power_levels:
                    power = level[0]
                    # set input power level
                    ts.log('    Setting the input power of the PV simulator to %0.2f' % (p_max * power))
                    pv.power_set(p_max * power)

                    count = level[1]
                    for i in xrange(1, count + 1):
                        '''
                        6) Set the EPS voltage to a value greater than V4 for a duration of not less than the settling
                        time.
                        '''
                        '''
                        7) Begin recording the time domain response of the EUT AC voltage and current, and DC voltage
                        and current. Step down the simulated EPS voltage (the rise/fall time of simulated EPS voltage
                        shall be < 1 cyc or < 1% of settling time) until at least three points are recorded in each
                        line segment of the characteristic curve or the EUT trips from the LVRT must trip requirements.
                        Continue recording the time domain response for at least twice the settling time after each
                        voltage step.
                        '''
                        '''
                        8) Set all AC source parameters to the nominal operating conditions for the EUT. Frequency is
                        set at nominal and held at nominal throughout this test. Set the EUT power to Pmax then repeat
                        Repeat Step (7), except raising, instead of dropping, the simulated EPS voltage (the rise/fall
                        time of simulated EPS voltage shall be < 1 cyc or < 1% of settling time) until at least three
                        points are recorded in each line segment of the characteristic curve or the EUT trips from HVRT
                        must trip requirements.
                        '''

                        # test voltage high to low
                        # start capture
                        test_str = 'VV_high_%s_%s_%s' % (str(test), str(power), str(i))
                        ts.log('Starting data capture for test %s, testing voltage high to low, with %s, '
                               'Power = %s%%, and sweep = %s' % (test_str, test_labels[test], power*100., i))
                        daq.data_capture(True)

                        for v in reversed(voltage_points):
                            ts.log('        Setting the grid voltage to %0.2f and waiting %0.1f seconds.' %
                                   (v, t_settling))
                            grid.voltage(v)
                            ts.sleep(t_settling)

                        # stop capture and save
                        daq.data_capture(False)
                        ds = daq.data_capture_dataset()
                        ds.to_csv(ts.result_file('%s.csv') % (test_str))
                        ts.log('Saving data capture')

                        # test voltage low to high
                        # start capture
                        test_str = 'VV_low_%s_%s_%s' % (str(test), str(power), str(i))
                        ts.log('Starting data capture for test %s, testing voltage low to high, with %s, '
                               'Power = %s%%, and sweep = %s' % (test_str, test_labels[test], power*100., i))
                        daq.data_capture(True)

                        for v in voltage_points:
                            ts.log('        Setting the grid voltage to %0.2f and waiting %0.1f seconds.' %
                                   (v, t_settling))
                            grid.voltage(v)
                            ts.sleep(t_settling)

                        # stop capture and save
                        daq.data_capture(False)
                        ds = daq.data_capture_dataset()
                        ds.to_csv(ts.result_file('%s.csv') % (test_str))
                        ts.log('Saving data capture')

                        '''
                        9) Repeat test Steps (6) - (8) at power levels of 20 and 66%; as described by the following:
                           a) For the 20% test, the EUT output power set to 20% of its Prated nominal rating
                           b) For the 66% test the test input source is to be adjusted to limit the EUT output power to
                           a value between 50% and 95% of rated output power.
                           c) The 66% power level, as defined in (b), shall be repeated for a total of five sweeps of
                           the Q(V) curve to validate consistency.
                        '''
                '''
                10) Repeat steps (6) - (9) for the remaining tests in Table SA13.1. Other than stated in (9) (c), the
                required number of sweeps for each of these repetitions is three. In the case of EUT without adjustable
                (V, Q) points, this step may be eliminated.
                '''
            '''
            11) If the EUT has the ability to set 'Active Power Priority' and 'Reactive Power Priority', select the
            other Priority, return the simulated EPS voltage to nominal, and repeat steps (5) - (10).
            '''

        result = script.RESULT_COMPLETE

    except script.ScriptFail, e:
        reason = str(e)
        if reason:
            ts.log_error(reason)
    finally:
        if daq is not None:
            daq.close()
        if pv is not None:
            pv.close()
        if grid is not None:
            grid.close()

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

info.param_group('general', label='General Parameters')
info.param('general.tests', label='Tests to run', default='All', values=['All','Test 1 - Most Aggressive',
                                                                         'Test 2 - Average',
                                                                         'Test 3 - Least Aggressive'])
info.param_group('ratings', label='DER Ratings')
info.param('ratings.s_rated', label='Apparent power rating (VA)', default=0.0)
info.param('ratings.p_rated', label='Output power rating (W)', default=0.0)
info.param('ratings.v_nom', label='Nominal AC voltage (V)', default=0.0, desc='Nominal voltage for the AC simulator.')
info.param('ratings.v_min', label='Minimum AC voltage (V)', default=0.0)
info.param('ratings.v_max', label='Maximum AC voltage (V)', default=0.0)
info.param('ratings.v_msa', label='AC voltage manufacturers stated accuracy (V)', default=0.0)
info.param('ratings.var_msa', label='Reactive power manufacturers stated accuracy (Var)', default=0.0)
info.param('ratings.var_ramp_max', label='Maximum ramp rate', default=0.0)
info.param('ratings.q_max_cap', label='Maximum reactive power production (capacitive) (Var)', default=0.0)
info.param('ratings.q_max_ind', label='Maximum reactive power absorbtion (inductive) (Var)', default=0.0)
info.param('ratings.k_var_max', label='Maximum slope (Var/V)', default=0.0)
info.param('ratings.deadband_min', label='Deadband minimum range (V)', default=0.0)
info.param('ratings.deadband_max', label='Deadband maximum range (V)', default=0.0)
info.param('ratings.t_settling', label='Settling time (t)', default=0.0)
info.param('ratings.power_priority', label='Supported power priority', default='Active', values=['Both', 'Active',
                                                                                                 'Reactive'])
info.param_group('srd', label='Source Requirements Document')
info.param('srd.p_min_pct', label='Minimum tested output power (% of nameplate power rating)', default=20.)
info.param('srd.p_max_pct', label='Maximum tested output power (% of nameplate power rating)', default=100.)
info.param('srd.k_var_min', label='Minimum slope (Var/V)', default='')
info.param('srd.segment_point_count', label='Measurement points per curve segment', default=3)

der.params(info)
gridsim.params(info)
pvsim.params(info)
das.params(info)

info.logo('sunspec.gif')

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



