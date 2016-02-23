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

# Test script for UL 1741 SA SS (Soft Start Ramp Rate)
# This test requires the following SunSpec Alliance Modbus models: inverter, controls, settings, nameplate

#!C:\Python27\python.exe

import sys
import os
import traceback
import time
import inverter
import pvsim
import gridsim
import numpy as np
import sunspec.core.client as client
import script

# returns: True if ramp meets UL 1741 criteria
def verify_ramp(inv, ramp, t_since_start, Irated, MSARR, das=None):
    result = True

    # SA 11.3.1.2 For each of the recorded time domain responses, the EUT ramp shall not exceed a region with the
    # upper limit defined by the ramp rate setting plus the stated ramp rate accuracy and with the lower limit defined
    # by the upper limit minus 5% of Irated.

    expected_current_pct = ramp*t_since_start
    upper_lim_pct = expected_current_pct + MSARR
    lower_lim_pct = upper_lim_pct - 0.05*Irated

    # Assume that the grid voltage is nominal so normalized AC power is proportional to AC current
    inv_curr_pct = inverter.get_power_norm(inv=inv, das=das)*100

    ts.log('EUT expected current is %0.2f%% and the actual current was %0.2f%%. Passing bounds are [%0.2f%%, %0.2f%%].'
           % (expected_current_pct, inv_curr_pct, lower_lim_pct, upper_lim_pct))

    if inv_curr_pct < lower_lim_pct or inv_curr_pct > upper_lim_pct:
        ts.log_warning('EUT response is not within the UL 1741 SA bounds, but additional analysis should be conducted.')
        ts.log_warning('Note: Stepwise or piecewise linear responses may pass the test despite containing sections of')
        ts.log_warning('response that exceed the ramp rate plus accuracy. With the lower limit aligned with any point')
        ts.log_warning('on the response, all points succeeding that point should fall below the upper limit.')

        result = False

    return result

def test_run():

    result = script.RESULT_FAIL
    das = None
    trigger = None
    inv = None
    pv = None
    disable = None

    try:

        # UL 1741 Test Protocol
        # SA 11.3.2 The soft-start test shall be carried out as follows:

        # a)	Connect the EUT according to the instructions and specifications provided by the manufacturer.

        # b)	Set all AC source parameters to the nominal operating conditions for the EUT.

        # c)	Set the input  source power level to provide  Irated from the EUT. Note: for units that do not
        # adjust output current as a function of their input such as units with energy storage or multimode products
        # the output power is to be commanded.

        # d)	Turn on the EUT.  Set the EUT ramp rate parameters according to Test 1 in Table SA 11.2.

        # e)	Adjust the AC voltage or frequency outside the near nominal range for a period exceeding setting the
        # AC voltage to zero for longer than the must-trip duration.

        # f)	Begin recording the time domain response of the EUT AC voltage and current, and DC voltage and current.

        # g)	Adjust the AC source to the rated nominal operating conditions for the EUT. The EUT shall not
        # commence exporting output current until nominal conditions have been achieved.

        # h)	Stop recording the time domain response after at least the reconnect time of the inverter
        # (e.g. 30 sec. to 5 minutes), plus ramp duration plus a manufacturer-specified dwell time as shown in SA 11.
        # Ramp duration is defined by 100/RRss as appropriate.

        # i)	Repeat steps e-h for a total of 3 repetitions.

        # j)	Repeat steps d-i for Tests 2-3 in Table 11.2.


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
        RRss_min = ts.param_value('ss.RRss_min')
        RRss_max = ts.param_value('ss.RRss_max')
        #Ilow = ts.param_value('ss.Ilow')
        Irated = 100.
        MSARR = ts.param_value('ss.MSARR')
        t_dwell = ts.param_value('ss.t_dwell')

        # Script timing and pass/fail criteria
        pretest_delay = ts.param_value('invt.pretest_delay')
        verification_delay = ts.param_value('invt.verification_delay')
        posttest_delay = ts.param_value('invt.posttest_delay')
        power_threshold = ts.param_value('invt.power_threshold')
        disable = ts.param_value('invt.disable')

        # Data acquisition and triggering methods
        datamethod = ts.param_value('datatrig.dsm_method')
        trigmethod = ts.param_value('datatrig.trigger_method')

        # Step f. Begin recording the time domain response of the EUT AC voltage and current, and DC voltage and current.

        # Step h. Stop recording the time domain response after at least the reconnect time of the inverter
        #         (e.g. 30 sec. to 5 minutes), plus ramp duration plus a manufacturer-specified dwell time as shown in
        #         SA 11. Ramp duration is defined by 100/RRss as appropriate.

        if datamethod == 'Sandia LabView DSM':
            import sandia_dsm as dsm
            das = dsm.Data()
            computer = ts.param_value('datatrig.das_comp')
            if computer == '10 node':
                node = ts.param_value('datatrig.node')

        # Setup trigger if available
        if trigmethod == 'Create Local File for Sandia LabView DSM':
            import sandia_dsm as dsm
            trigger = dsm.Trigger()
            trigger.off()

        # Step b.	Set all AC source parameters to the nominal operating conditions for the EUT.
        # Initialize pv simulation - This is before step (a) because PV power may be required for communications to EUT
        pv = pvsim.pvsim_init(ts)
        pv.power_on()

        grid = gridsim.gridsim_init(ts)

        # Communication is established between the Utility Management System Simulator and EUT
        ts.log('Scanning EUT')
        try:
            inv = client.SunSpecClientDevice(ifc_type, slave_id=slave_id, name=ifc_name, baudrate=baudrate,
                                             parity=parity, ipaddr=ipaddr, ipport=ipport)
        except Exception, e:
            raise script.ScriptFail('Error: %s' % e)

        # Step a.	Connect the EUT according to the instructions and specifications provided by the manufacturer.
        # It is assumed that the  Grid Simulator (if used) is connected to the EUT and operating properly
        inverter.set_power_factor(inv, power_factor=1., enable=0)

        # Step c. Set the input  source power level to provide Irated from the EUT. Note: for units that do not
        # adjust output current as a function of their input such as units with energy storage or multimode
        # products the output power is to be commanded.
        pv.irradiance_set(irradiance=1000)

        # UL 1741 Step j.	Repeat steps d-i for Tests 2-3 in Table 11.2.
        for ramp in [RRss_min, (RRss_min + RRss_max)/2, RRss_max]:

            # Step d.	Turn on the EUT. Set the EUT ramp rate parameters according to Test 1 in Table SA 11.2.
            if pretest_delay > 0:
                ts.log('Waiting for pre-test delay of %d seconds' % pretest_delay)
                ts.sleep(pretest_delay)

            # Verify EUT is in correct state before running the test.
            if inverter.get_conn_state(inv) is False:
                ts.log('Inverter not in correct state, setting state to connected.')
                inverter.set_conn_state(inv, state=1)
                if verify_conn_state_change(inv, orig_state=0, verification_delay=verification_delay,
                                            threshold=power_threshold, das=das) is False:
                    raise script.ScriptFail()

            ''' Revise when SS ramp rate exists in a SunSpec Model
            try:
                inv.settings.read()
                if inv.settings.SSWGra is not None:
                    inv.settings.SSWGra = ramp
                else:
                    ts.log_error('Unable to change ss ramp rate in the EUT.')
            except Exception, e:
                ts.log_error('Error changing ss ramp rate in the EUT: %s' % str(e))
            '''

            for i in xrange(3):  # UL 1741 Step i. Repeat steps e-h two times for a total of 3 repetitions.

                ts.log('Running test number %d with ramp rate %0.3f %%Irated/sec.' % (i+1, ramp))

                # e)	Adjust the AC voltage or frequency outside the near nominal range for a period exceeding
                # setting the AC voltage to zero for longer than the must-trip duration.
                grid.voltage(0)
                time.sleep(1)

                # g)	Adjust the AC source to the rated nominal operating conditions for the EUT. The EUT shall not
                # commence exporting output current until nominal conditions have been achieved.
                grid.voltage(grid.v_nom())
                start_time = time.time()

                # Determine reconnection time
                t_reconnection = 0
                while inverter.get_conn_state(inv) is False:
                    t_reconnection = time.time()-start_time  # Reconnection time updates until the inverter reconnects
                    time.sleep(0.1)

                data_update_rate = 1  # Hz ... parameterize sometime...
                check_duration = 100./ramp
                test_duration = t_dwell + check_duration
                duration = 0
                while duration < test_duration+verification_delay:
                    duration = time.time()-start_time-t_reconnection
                    if duration <= check_duration:  # only check the ramp response during the check_duration
                        ramp_in_bounds = verify_ramp(inv, ramp=ramp, t_since_start=duration, Irated=Irated, MSARR=MSARR,
                                                     das=das)
                        if ramp_in_bounds is False:
                            ts.log_error('Ramp response was not within limits')
                            # raise script.ScriptFail()
                    else:  # The EUT shall reach at least 95% of Irated at the end of the dwell time.
                        ts.log('EUT completed ramping. Waiting for dwell time to check current output. '
                               'Remaining time: %0.3f' % (test_duration - duration))
                        if duration >= test_duration:
                            current_pct = inverter.get_power_norm(inv=inv, das=das)*100
                            ts.log_error('EUT current is %0.3f%%' % current_pct)
                            if current_pct < 95:
                                ts.log_error('EUT did not reach at least 95% of Irated at the end of the dwell time.')
                                raise script.ScriptFail()
                            break
                    time.sleep(1/data_update_rate)  # todo: improve the loop timing

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

info.param_group('ss', label='SS Test Parameters')
#info.param('ss.Irated', label='Irated', default=100.,
#           desc='Output current max of function, i.e., 100% of rated current')
info.param('ss.RRss_max', label='RRss_max', default=100., desc='Maximum normal ramp-up rate (%Irated /sec)')
info.param('ss.RRss_min', label='RRss_min', default=0.5, desc='Minimum normal ramp-up rate  (%Irated /sec)')
#info.param('ss.Ilow', label='Ilow', default=20., desc='Output current min of function, i.e., 20% of rated current')
info.param('ss.MSARR', label='MSARR', default=0.2, desc='Ramp Rate Accuracy (%Irated /sec)')
info.param('ss.t_dwell', label='t_dwell', default=3., desc='Manufacturer specified dwell time (sec)')

info.param_group('invt', label='SS Timing and Pass/Fail Parameters')
info.param('invt.pretest_delay', label='Pre-Test Delay (seconds)', default=0,
           desc='Delay before beginning the test.')
info.param('invt.verification_delay', label='Verification Delay (seconds)', default=5,
           desc='Time allowed for INV1 operations. Applied to connect, disconnect, time window, and revert.')
info.param('invt.posttest_delay', label='Post-Test Delay (seconds)', default=10,
           desc='Delay after finishing the test.')

# PV simulator
pvsim.params(info)

# Grid simulator
gridsim.params(info)

# DAS
info.param_group('datatrig', label='Data Acquisition and Triggering', glob=True)
info.param('datatrig.trigger_method', label='Trigger Method', default='Disabled - Data from EUT',
           values=['Disabled - Data from EUT', 'Create Local File for Sandia LabView DSM'],
           desc='Each lab will need a different triggering method. Sandia writes a trigger file locally '
                'to be read by the DAQ.')
info.param('datatrig.dsm_method', label='Data Acquisition Method', default='Disabled - Data from EUT',
           values=['Disabled - Data from EUT', 'Sandia LabView DSM', 'TCP Stream for Sandia LabView DSM'],
           desc='Each lab will have different data acquisition methods. Sandia passes the data from the DAQ '
                'to python by writing the values locally or collecting them over the local TCP network.')
info.param('datatrig.das_comp', label='Data Acquisition Computer', default='10 Node',
           values=['10 Node', 'DAS 3', 'DAS 5', 'DAS 8'],
           active='datatrig.dsm_method', active_value=['Sandia LabView DSM'],
           desc='Selection of the data acquisition system (if there are multiple options).')
info.param('datatrig.node', label='Node at Sandia - Used to ID DAQ channel', default=10,  active='datatrig.das_comp',
           active_value=['10 Node'],
           desc='Selection of the EUT which will be used for the test (Sandia specific).')

# todo: Allow multiple DAQ channel IDs... change type to string. We may want to run multiple inverters at the same time
# todo: Same for the communications... this will be a while in the future.

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




