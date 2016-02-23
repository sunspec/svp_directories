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

# Test script for UL 1741 SA RR (Normal Ramp Rate)
# This test requires the following SunSpec Alliance Modbus models: inverter, controls, settings, nameplate

#!C:\Python27\python.exe

import sys
import os
import traceback
import time
import inverter
import pvsim
import das
import numpy as np
import sunspec.core.client as client
import script

# returns: True if ramp meets UL 1741 criteria
def verify_ramp(inv, ramp, t_since_step, Ilow, Irated, MSARR, data=None):
    result = True

    # SA 11.2.4.3 For each of the recorded time domain responses, the EUT ramp shall not exceed a
    # region with the upper limit defined by the ramp rate setting plus the stated ramp rate accuracy
    # and with the lower limit defined by the upper limit minus 5% of Irated.

    expected_current_pct = Ilow + ramp*t_since_step
    upper_lim_pct = expected_current_pct + MSARR
    lower_lim_pct = upper_lim_pct - 0.05*Irated

    # Assume that the grid voltage is nominal so normalized AC power is proportional to AC current
    inv_curr_pct = inverter.get_power_norm(inv=inv, das=data)*100

    ts.log('EUT expected current is %0.2f%% and the actual current was %0.2f%%. Passing bounds are [%0.2f%%, %0.2f%%].' %
           (expected_current_pct, inv_curr_pct, lower_lim_pct, upper_lim_pct))

    if inv_curr_pct < lower_lim_pct or inv_curr_pct > upper_lim_pct:
        ts.log_warning('EUT response is not within the UL 1741 SA bounds, but additional analysis should be conducted.')
        ts.log_warning('Note: Stepwise or piecewise linear responses may pass the test despite containing sections of')
        ts.log_warning('response that exceed the ramp rate plus accuracy. With the lower limit aligned with any point')
        ts.log_warning('on the response, all points succeeding that point should fall below the upper limit.')

        result = False

    return result

def test_run():

    result = script.RESULT_FAIL
    data = None
    trigger = None
    inv = None
    pv = None
    disable = None

    try:

        # UL 1741 Test Protocol
        # a.	Connect the EUT according to the Requirements in Sec. 11.2.4 and specifications provided by the
        #       manufacturer. Set the EUT to maximum power factor.

        # b.	Set all AC source parameters to the nominal operating conditions for the EUT.

        # c.	Set the input power level to provide Ilow from the EUT. Note: for units that do not adjust output
        #       current as a function of their input such as units with energy storage or multimode products the output
        #       power is to be commanded.

        # d.	Turn on the EUT.  Allow the EUT to reach steady state, e.g., maximum power point.

        # e.	Set the EUT ramp rate parameters according to Test 1 in Table SA 11.1.

        # f.	Begin recording the time domain response of the EUT AC voltage and current, and DC voltage and current.

        # g.	Increase the available input power to provide Irated from the EUT according to the step function
        #       described in SA 11.

        # h.	Stop recording the time domain response after the ramp duration plus a manufacturer-specified dwell
        #       time. Ramp duration is defined by 100/RRnorm_up as appropriate for the test settings.

        # i.	Repeat steps c-h two times for a total of 3 repetitions.

        # j.	Repeat steps c-i for Tests 2-3 in Table SA 11.1.

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

        # RR parameters
        RRnorm_up_min = ts.param_value('rr.RRnorm_up_min')
        RRnorm_up_max = ts.param_value('rr.RRnorm_up_max')
        Ilow = ts.param_value('rr.Ilow')
        Irated = ts.param_value('rr.Irated')
        MSARR = ts.param_value('rr.MSARR')
        t_dwell = ts.param_value('rr.t_dwell')

        # Script timing and pass/fail criteria
        pretest_delay = ts.param_value('invt.pretest_delay')
        verification_delay = ts.param_value('invt.verification_delay')
        posttest_delay = ts.param_value('invt.posttest_delay')
        power_threshold = ts.param_value('invt.power_threshold')
        disable = ts.param_value('invt.disable')

        # initialize data acquisition system
        daq = das.das_init(ts)
        data = daq.data_init()
        trigger = daq.trigger_init()

        # Step b.	Set all AC source parameters to the nominal operating conditions for the EUT.
        # Initialize pv simulation - This is before step (a) because PV power may be required for communications to EUT
        pv = pvsim.pvsim_init(ts)
        pv.power_on()

        # Communication is established between the Utility Management System Simulator and EUT
        ts.log('Scanning EUT')
        try:
            inv = client.SunSpecClientDevice(ifc_type, slave_id=slave_id, name=ifc_name, baudrate=baudrate,
                                             parity=parity, ipaddr=ipaddr, ipport=ipport)
        except Exception, e:
            raise script.ScriptFail('Error: %s' % e)

        # Step a.	Connect the EUT according to the Requirements in Sec. 11.2.4 and specifications provided by the
        #       manufacturer. Set the EUT to maximum power factor.
        # It is assumed that the  Grid Simulator (if used) is connected to the EUT and operating properly
        inverter.set_power_factor(inv, power_factor=1., enable=0)

        # UL 1741 Step j.	Repeat steps c-i for Tests 2-3 in Table SA 11.1.
        for ramp in [RRnorm_up_min, (RRnorm_up_min + RRnorm_up_max)/2, RRnorm_up_max]:

            for i in xrange(3):  # UL 1741 Step i. Repeat steps c-h two times for a total of 3 repetitions.

                ts.log('Running test number %d with ramp rate %0.3f %%Irated/sec.' %
                       (i+1, ramp))

                # Step c. Set the input power level to provide Ilow from the EUT. Note: for units that do not adjust
                #       output current as a function of their input such as units with energy storage or multimode
                #       products the output power is to be commanded.
                pv.irradiance_set(irradiance=Ilow*10)

                # Step d.	Turn on the EUT.  Allow the EUT to reach steady state, e.g., maximum power point.
                if pretest_delay > 0:
                    ts.log('Waiting for pre-test delay of %d seconds' % pretest_delay)
                    ts.sleep(pretest_delay)

                # Verify EUT is in correct state before running the test.
                if inverter.get_conn_state(inv) is False:
                    ts.log('Inverter not in correct state, setting state to connected.')
                    inverter.set_conn_state(inv, state=1)
                    if verify_conn_state_change(inv, orig_state=0, verification_delay=verification_delay,
                                                threshold=power_threshold, data=data) is False:
                        raise script.ScriptFail()

                # Step e.	Set the EUT ramp rate parameters according to Test 1 in Table SA 11.1.
                try:
                    inv.settings.read()
                    if inv.settings.WGra is not None:
                        inv.settings.WGra = ramp
                    else:
                        ts.log_error('Unable to change ramp rate in the EUT.')
                except Exception, e:
                    ts.log_error('Error changing ramp rate in the EUT: %s' % str(e))

                # Step g.	Increase the available input power to provide Irated from the EUT according to the step
                #           function described in SA 11.
                pv.irradiance_set(irradiance=1000)
                start_time = time.time()

                # Step h.	Stop recording the time domain response after the ramp duration plus a
                #           manufacturer-specified dwell time.
                data_update_rate = 1  # Hz
                check_duration = (Irated-Ilow)/ramp
                test_duration = t_dwell + check_duration
                duration = 0
                while duration < test_duration+verification_delay:
                    duration = time.time()-start_time
                    ts.log_debug('duration = %0.2f, check duration = %0.2f' % (duration, check_duration))
                    if duration <= check_duration:  # only check the ramp response during the check_duration
                        ramp_in_bounds = verify_ramp(inv, ramp=ramp, t_since_step=duration, Ilow=Ilow,
                                                     Irated=Irated, MSARR=MSARR, data=data)
                        if ramp_in_bounds is False:
                            ts.log_error('Ramp response was not within limits')
                            # raise script.ScriptFail()
                    else:  # The EUT shall reach at least 95% of Irated at the end of the dwell time.
                        ts.log('EUT completed ramping. Waiting for dwell time to check current output. '
                               'Remaining time: %0.3f' % (test_duration - duration))
                        if duration >= test_duration:
                            current_pct = inverter.get_power_norm(inv=inv, das=data)*100
                            ts.log_error('EUT current is %0.3f%%' % current_pct)
                            if current_pct < 95:
                                ts.log_error('EUT did not reach at least 95% of Irated at the end of the dwell time.')
                                raise script.ScriptFail()
                            break
                    time.sleep(1/data_update_rate)  # todo: should improve the loop timing

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
        if pv is not None:
            pv.close()

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

info.param_group('rr', label='RR Test Parameters')
info.param('rr.RRnorm_up_min', label='RRnorm_up_min', default=0.5,
           desc='Minimum normal ramp-up rate  (%Irated /sec)')
info.param('rr.RRnorm_up_max', label='RRnorm_up_max', default=100.,
           desc='Maximum normal ramp-up rate (%Irated /sec)')
info.param('rr.Ilow', label='Ilow', default=20.,
           desc='Output current min of function, i.e., 20% of rated current')
info.param('rr.Irated', label='Irated', default=100.,
           desc='Output current max of function, i.e., 100% of rated current')
info.param('rr.MSARR', label='MSARR', default=0.2,
           desc='Ramp Rate Accuracy (%Irated /sec)')
info.param('rr.t_dwell', label='t_dwell', default=3.,
           desc='Manufacturer specified dwell time (sec)')

info.param_group('invt', label='RR Timing and Pass/Fail Parameters')
info.param('invt.pretest_delay', label='Pre-Test Delay (seconds)', default=0,
           desc='Delay before beginning the test.')
info.param('invt.verification_delay', label='Verification Delay (seconds)', default=5,
           desc='Time allowed for INV1 operations. Applied to connect, disconnect, time window, and revert.')
info.param('invt.posttest_delay', label='Post-Test Delay (seconds)', default=10,
           desc='Delay after finishing the test.')

#PV simulator
pvsim.params(info)

info.param_group('pvsim_profile', label='PV Simulator Profile', active='pvsim.mode', active_value=['TerraSAS'])
info.param('pvsim_profile.profile_name', label='TerraSAS Profile Name', default='None',
           values=['None', 'STPsIrradiance'],
           active='pvsim.mode', active_value=['TerraSAS'],
           desc='Enter text name or leave blank to not run a profile.')
info.param('pvsim_profile.irr_start', label='Initial Irradiance (W/m^2)', default=1000.0, active='pvsim.mode',
           active_value=['TerraSAS'],
           desc='Irradiance at the beginning of the profile. Use 1000 W/m^2 for the Sandia Test Protocols.')

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




