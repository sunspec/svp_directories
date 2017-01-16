

import sys
import os
import traceback
import gridsim
import pvsim
import das
import der
import script
import openpyxl

def test_run():

    result = script.RESULT_FAIL
    daq = None

    try:

        p_rated = ts.param_value('ratings.p_rated')
        pf_min_ind = ts.param_value('ratings.pf_min_ind')
        pf_min_cap = ts.param_value('ratings.pf_min_cap')
        pf_settling_time = ts.param_value('ratings.pf_settling_time')
        pf_target = ts.param_value('ratings.pf_target')

        p_low = p_rated * .2
        pf_mid_ind = (1 + pf_min_ind)/2
        pf_mid_cap = (-1 + pf_min_cap)/2

        pf_target_value = {'PF_min_ind': pf_min_ind, 'PF_mid_ind': pf_mid_ind,
                           'PF_min_cap': pf_min_cap, 'PF_mid_cap': pf_mid_cap}


        '''
        2) Set all AC source parameters to the normal operating conditions for the EUT. 
        '''
        # grid simulator is initialized with test parameters and enabled
        grid = gridsim.gridsim_init(ts)

        # pv simulator is initialized with test parameters and enabled
        pv = pvsim.pvsim_init(ts)
        pv.power_set(p_low)
        pv.power_on()

        # initialize data acquisition
        daq = das.das_init(ts)

        '''
        3) Turn on the EUT. It is permitted to set all L/HVRT limits and abnormal voltage trip parameters to the
        widest range of adjustability possible with the SPF enabled in order not to cross the must trip
        magnitude threshold during the test.
        '''
        # it is assumed the EUT is on
        eut = der.der_init(ts)
        eut.config()

        '''
        4) Select 'Fixed Power Factor' operational mode.
        '''
        # fixed power factor mode is enabled in test

        # table SA 12.1 - SPF test parameters
        if pf_target == 'All':
            pf_table = [pf_min_ind, pf_mid_ind, pf_min_cap, pf_mid_cap]
        else:
            pf_table = [pf_target_value.get(pf_target)]

        for pf in pf_table:
            for power_level in [1, .2, .5]:
                '''
                5) Set the input source to produce Prated for the EUT.
                '''
                pv.power_set(p_rated * power_level)
                ts.log('*** Setting power level to %s W (rated power * %s)' % ((p_rated * power_level), power_level))

                for count in range(1, 4):
                    ts.log('Starting pass %s' % (count))
                    '''
                    6) Set the EUT power factor to unity. Measure the AC source voltage and EUT current to measure the
                    displacement
                    '''
                    #ts.log('Fixed PF settings: %s' % eut.fixed_pf())
                    eut.fixed_pf(params={'Ena': True, 'PF': 1.0})
                    ts.log('Starting data capture for pf = %s' % (1.0))
                    daq.data_capture(True)
                    ts.sleep(pf_settling_time * 3)
                    daq.data_capture(False)
                    ds = daq.data_capture_dataset()
                    ds.to_csv(ts.result_file('PF_1_%s_%s.csv') % (str(power_level), str(count)))
                    ts.log('Saving data capture')

                    '''
                    7) Set the EUT power factor to the value in Test 1 of Table SA12.1. Measure the AC source voltage
                    and EUT current to measure the displacement power factor and record all data.
                    '''
                    eut.fixed_pf(params={'Ena': True, 'PF': pf})
                    ts.log('Starting data capture for pf = %s' % (pf))
                    daq.data_capture(True)
                    ts.sleep(pf_settling_time * 3)
                    daq.data_capture(False)
                    ds = daq.data_capture_dataset()
                    ds.to_csv(ts.result_file('PF_%s_%s_%s.csv') % (str(pf), str(power_level), str(count)))

                    '''
                    8) Repeat steps (6) - (8) for two additional times for a total of three repetitions.
                    '''
                '''
                9) Repeat steps (5) - (7) at two additional power levels. One power level shall be a Pmin or 20% of
                Prated and the second at any power level between 33% and 66% of Prated.
                '''
            '''
            10) Repeat Steps (6) - (9) for Tests 2 - 5 in Table SA12.1
            '''

        '''
        11) In the case of bi-directional inverters, repeat Steps (6) - (10) for the active power flow direction
        '''

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

info.param_group('ratings', label='DER Ratings')
info.param('ratings.p_rated', label='P_rated', default=3000)
info.param('ratings.pf_min_ind', label='PF_min_ind', default=.850)
info.param('ratings.pf_min_cap', label='PF_min_cap', default=-.850)
info.param('ratings.pf_settling_time', label='PF Settling Time', default=1)
info.param('ratings.pf_target', label='PF Target', default='All', values=['All', 'PF_min_ind', 'PF_mid_ind',
                                                                          'PF_min_cap', 'PF_mid_cap'])

der.params(info)
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


