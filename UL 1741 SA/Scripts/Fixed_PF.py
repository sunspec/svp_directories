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

# Test script for UL 1741 SA Fixed Power Factor
# This test requires the following SunSpec Alliance Modbus models: inverter, controls, settings, nameplate

#!C:\Python27\python.exe

import sys
import os
import traceback
import math
import time
import pvsim
import das

import sunspec.core.client as client
import script

import inverter

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

# get the screening range for the INV3 test
def calculate_pf_range(power_factor, power_factor_range):
    #Note 1: 'lower' and 'upper' are defined by vertical position on P-Q plane (not based on numerical value)
    #Note 2: Within Q1 and Q4 the 'upper' value is greater than the PF and the 'lower' value is less than the PF
    #Note 3: Q1 is negative, Q4 is positive
    if power_factor < 0 and power_factor_range - power_factor >= 1: #in Q1 with range back into Q4
        power_factor_upper = power_factor + power_factor_range
        power_factor_lower = 1 - (power_factor_range - (1 + power_factor))
    else: 
        if power_factor > 0 and power_factor_range + power_factor > 1: #in Q4 (and unity) with range back to Q1
            power_factor_upper = (power_factor_range - (1 - power_factor)) - 1
            power_factor_lower = power_factor - power_factor_range
        else: #in Q1 or Q4 with range in same quadrant 
            power_factor_upper = power_factor + power_factor_range
            power_factor_lower = power_factor - power_factor_range
    return (power_factor_upper, power_factor_lower)

# Function reports if the EUT PF out of range
def pf_out_of_range(power_factor, power_factor_lower, power_factor_upper, power_factor_range):
    # False = in range, True = out of range
    # Note: Q1 is negative, Q4 is positive
    
    if power_factor_lower*power_factor_upper < 0: #range includes both Q1 and Q4
        if power_factor > 0 and power_factor > power_factor_lower: # between limits in Q4
            #Note: since the PF is assumed to be the correct sign, you do not have to check the other side of unity
            return False
        elif power_factor <= 0 and power_factor < power_factor_upper: # between limits in Q1
            #Note: since the PF is assumed to be the correct sign, you do not have to check the other side of unity
            return False
        else:
            return True
    else: #in Q1 or Q4 with range in same quadrant
        if power_factor > 0: # Q4
            if power_factor > power_factor_lower and power_factor < power_factor_upper:
                #ts.log_debug('power_factor > power_factor_lower = %.3f > %.3f, ' \
                #      'power_factor < power_factor_upper = %.3f < %.3f' \
                #      %  (power_factor, power_factor_lower, power_factor, power_factor_upper))
                return False
            else:
                return True
        else: # Q1
            if power_factor > power_factor_lower and power_factor < power_factor_upper:
                #ts.log_debug('power_factor > power_factor_lower = %.3f > %.3f, ' \
                #      'power_factor < power_factor_upper = %.3f < %.3f' \
                #      %  (power_factor, power_factor_lower, power_factor, power_factor_upper))
                return False
            else:
                return True

# Log the connection status and the current output power
def log_conn_state(inv, data=None):
    try:
        connected = inverter.get_conn_state(inv)
        power = inverter.get_power(inv, data)
        pf = inverter.get_power_factor(inv, data)
        ts.log('Current connection state is %s. Power output = %0.3f W. power factor %0.3f.' %
               (inverter.conn_state_str(connected), power, pf))
    except Exception, e:
        ts.log_error('Error logging connect state: %s' % str(e))
        raise

def test_run():

    result = script.RESULT_FAIL
    data = None
    trigger = None
    inv = None
    pv = None
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

        power_factor = ts.param_value('inv3.power_factor')
        msa_vac = ts.param_value('inv3.MSA_Vac')
        msa_vdc = ts.param_value('inv3.MSA_Vdc')
        p_low = ts.param_value('inv3.p_low')
        p_high = ts.param_value('inv3.p_high')
        v_low = ts.param_value('inv3.v_low')
        v_high = ts.param_value('inv3.v_high')
        pf_acc = ts.param_value('inv3.pf_acc')
        pf_settling_time = ts.param_value('inv3.pf_settling_time')
        dc_nom = ts.param_value('inv3.dc_nom')

        pretest_delay = ts.param_value('invt.pretest_delay')
        power_factor_range = ts.param_value('invt.power_factor_range')
        setpoint_failure_count = ts.param_value('invt.setpoint_failure_count')
        verification_delay = ts.param_value('invt.verification_delay')
        posttest_delay = ts.param_value('invt.posttest_delay')
        disable = ts.param_value('invt.disable')

        # initialize data acquisition system
        daq = das.das_init(ts)
        data = daq.data_init()
        trigger = daq.trigger_init()

        # Initialize pv simulation - Part of UL 1741 Step 1
        pv = pvsim.pvsim_init(ts)
        pv.power_on()

        # Communication is established between the Utility Management System Simulator and EUT
        ts.log('Scanning EUT')
        try:
            inv = client.SunSpecClientDevice(ifc_type, slave_id=slave_id, name=ifc_name, baudrate=baudrate,
                                             parity=parity, ipaddr=ipaddr, ipport=ipport)
        except Exception, e:
            raise script.ScriptFail('Error: %s' % (e))

        # Make sure the EUT is on and operating
        ts.log('Verifying EUT is in connected state. Waiting up to %d seconds for EUT to begin power export.'
               % (verification_delay+pretest_delay))
        if verify_initial_conn_state(inv, state=inverter.CONN_CONNECT,
                                     time_period=verification_delay+pretest_delay, data=data) is False:
                ts.log_error('Inverter unable to be set to connected state.')
                raise script.ScriptFail()

        # Get parameters
        try:
            # This test follows the IEEE Std-1459-2000 reactive power sign convention, in which a leading, capacitive,
            # overexcited power factor is positive and a lagging, inductive, underexcited power factor is negative.

            #  get min/max PF settings
            inv.nameplate.read()
            min_ind_PF = float(inv.nameplate.PFRtgQ1) # negative
            min_cap_PF = float(inv.nameplate.PFRtgQ4) # positive

            inv.controls.read()
            inv.settings.read()
            inv.inverter.read()
            OutPFSet_Ena = inv.controls.OutPFSet_Ena
            ts.log('Power factor is %0.3f.' % float(inv.inverter.PF))
            if OutPFSet_Ena:
                ts.log('Power factor mode is enabled.')
            else:
                ts.log('Power factor mode is not enabled.')

            ts.log('********Parameters of the EUT*************')
            S_rated = float(inv.nameplate.VARtg)
            ts.log('Apparent Power Rating (VA) - S_rated: %.3f.' % S_rated)
            ts.log('EUT Input Power Rating (W) - P_rated: %.3f.' % float(inv.nameplate.WRtg))
            ts.log('DC Voltage range with function enabled (V) - [V_low, V_high]: [%.1f, %.1f].' % (v_low, v_high))
            ts.log('Nominal DC Voltage (V): %.3f.' % dc_nom)
            ts.log('Nominal AC Voltage (V): %.3f.' % float(inv.settings.VRef))
            ts.log('AC Voltage Range with function enabled (V): %.3f to %.3f' %
                   (float(inv.settings.VMin),float(inv.settings.VMax)))
            ts.log('AC Voltage Accuracy (V) - MSA_Vac: %.3f.' % msa_vac)
            ts.log('DC Voltage Accuracy (V) - MSA_Vdc: %.3f.' % msa_vdc)
            ts.log('Active power range of function (%%nameplate) - [P_low, P_high]: [%.1f, %.1f].' % (p_low, p_high))
            ts.log('Power Factor Accuracy: %.3f.' % pf_acc)
            ts.log('Power Factor Settling Time: %.3f.' % pf_settling_time)
            ts.log('Minimum inductive (underexcited) power factor - PF_min,ind: %.3f.' % min_cap_PF)
            ts.log('Minimum capacitive (overexcited) power factor - PF_min,cap: %.3f.' % min_ind_PF)
            ts.log('*******************************************')
            mid_cap_PF = (-1. - min_cap_PF)/2.
            mid_ind_PF = (1. - min_ind_PF)/2.
            ts.log('Power factor target for the test - PF: %.3f.' % power_factor)
            ts.log('PF_mid,cap = half the EUT capacitive range: %.3f.' % mid_cap_PF)
            ts.log('PF_mid,ind = half the EUT inductive range: %.3f.' % mid_ind_PF)
            ts.log('P_limit, the maximum output power (W): %.3f.' % float(inv.settings.WMax))
            ts.log('Q_rated, the reactive power rating of the EUT (VAr): %.3f.' % float(inv.settings.VArMaxQ1))
            p_x = math.fabs(power_factor)*100
            ts.log('P_X, the maximum input power which an "Active Power Priority" mode maintains the PF '
                   'command (%%nameplate): %.3f.' % p_x)
            ts.log('*******************************************')

        except Exception, e:
            raise script.ScriptFail('Unable to get PF limits or other data from EUT: %s' % str(e))


        # UL 1741 Step 4: Set the power factor priority
        # Assumed at this point...

        ts.log('Power levels for testing are %.2f, %.2f, %.2f, %.2f, and %.2f as a %% of nameplate.' %
                   (p_low, (p_low + p_x)/2 ,p_x, (p_x + p_high)/2, p_high))

        # UL 1741 Step 8: Repeat fixed power factor test at 5 different DC power levels
        for power_level in [p_low, (p_low + p_x)/2 ,p_x, (p_x + p_high)/2, p_high]:

            # change the irradiance - this should be changed to a new method in pvsim
            irradiance_level = power_level*10 # scale the %nameplate power to irradiance (100% = 1000 W/m^2)

            ts.log('DC power level is %.3f %% nameplate, so the simulator power level is set to %.1f W/m^2' %
                   (power_level, irradiance_level))
            pv.irradiance_set(irradiance=irradiance_level)
            pv.power_on()

            # Find pass/fail bounds
            # todo: fix this function for 'watt priority'
            (power_factor_upper, power_factor_lower) = calculate_pf_range(power_factor, power_factor_range)
            ts.log('Target power factor: %.3f. Pass limits for screening: lower = %.3f, upper = %.3f' %
                   (power_factor, power_factor_lower, power_factor_upper))

            for i in xrange(3): # UL 1741 Step 7: Repeat the test 3 times

                ts.log('Running test number %d at power level %0.3f. Setting power factor to unity.' %
                       (i+1, power_level))

                if trigger:
                    trigger.off()

                # UL 1741 Step 5: Set power factor to unity
                # Trigger set immediately before sending the enable command to the DER
                inverter.set_power_factor(inv, power_factor=1.0, enable=1)

                if pretest_delay > 0:
                    ts.log('Waiting for pre-test delay of %d seconds' % pretest_delay)
                    ts.sleep(pretest_delay)

                # Store fixed power factor execution time for determining when time window and timeout period occur
                start_time = time.time()
                elapsed_time = 0

                # UL 1741 Step 6: Start recording the data - should already be running.  Then set PF to value in 1741
                # SA Table
                ts.log('Setting target power factor in the EUT to %0.3f.' % power_factor)
                inverter.set_power_factor(inv, power_factor=power_factor, enable=1, trigger=trigger)

                test_duration = pf_settling_time*2. + verification_delay
                ts.log('Waiting up to %0.2f seconds for power factor change with a verification period of %d seconds.' %
                       (pf_settling_time*2., verification_delay))

                # Initialize consecutive failure count to not script fail on transient behavior
                failures = 0

                while elapsed_time <= test_duration:
                    ts.sleep(0.93)
                    elapsed_time = time.time()-start_time

                    pf = inverter.get_power_factor(inv, data)

                    # Cheating here because the PF is unsigned in inv.inverter.PF and data.ac_pf
                    # With a good data acquisition system, this code block can be deleted.
                    if power_factor < 0 and pf > 0:
                        # assume the PF is the correct sign
                        pf = -pf

                    # Screening: determine if the PF is in the target range
                    out_of_range = pf_out_of_range(pf, power_factor_lower, power_factor_upper, power_factor_range)

                    ts.log('PF Target = %.3f, PF = %.3f (Total Error = %.3f%%), Time: %0.3f seconds.' %
                           (power_factor, pf, (pf - power_factor)*100.0, elapsed_time))

                    # if pf is out of range
                    if out_of_range is True:
                        failures += 1
                        if failures >= setpoint_failure_count:
                            ts.log_error('Inverter exceeded PF setpoint + buffer after %0.3f seconds. '
                                         'Fail count = %d.' % (elapsed_time,failures))
                            raise script.ScriptFail()
                        else:
                            ts.log_warning('Inverter exceeded PF setpoint + buffer after %0.3f seconds. '
                                           'Fail count = %d.' % (elapsed_time,failures))
                    else:
                        failures = 0

        if posttest_delay > 0:
              ts.log('Waiting for post-test delay of %d seconds.' % posttest_delay)
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
        if disable == 'yes' and inv is not None:
            inv.controls.OutPFSet_Ena = 0
            inv.controls.write()

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

    #ts.log('Returning to default power factor settings')   
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

info.param_group('inv3', label='Manufacturers Parameters')
info.param('inv3.power_factor', label='Power Factor (negative = underexcited)', default=1.0,
           desc='Positive PF is underexcited, leading, absorbing reactive power, sinking vars like a capacitive source'
                'or inductive load.')
info.param('inv3.MSA_Vac', label='AC voltage accuracy (V) - MSAVac', default=1.0,
           desc='AC voltage accuracy (V) - MSAVac')
info.param('inv3.MSA_Vdc', label='DC voltage accuracy (V) - MSAVdc', default=1.0,
           desc='DC voltage accuracy (V) - MSAVdc')
info.param('inv3.p_low', label='Lowest dc power for the function (% of nameplate)', default=20.,
           desc='Active power range of function, i.e., 20-100% of nameplate - [Plow,  Phigh]')
info.param('inv3.p_high', label='Highest dc power for the function (% of nameplate)', default=100.,
           desc='Active power range of function, i.e., 20-100% of nameplate - [Plow,  Phigh]')
info.param('inv3.v_low', label='Lowest dc voltage for the function (V)', default=200.,
           desc='Active voltage range of function - [Vlow,  Vhigh]')
info.param('inv3.v_high', label='Highest voltage for the function (V)', default=600.,
           desc='Active voltage range of function - [Vlow,  Vhigh]')
info.param('inv3.pf_acc', label='Power Factor Accuracy', default=0.01,
           desc='Power Factor Accuracy')
info.param('inv3.pf_settling_time', label='Power Factor Settling Time (s)', default=5.,
           desc='Power Factor Settling Time (s). This determines the test duration')
info.param('inv3.dc_nom', label='Nominal DC voltage (V)', default=460.,
           desc='Nominal DC voltage (V)')

info.param_group('invt', label='INV3 Timing and Pass/Fail Parameters')
info.param('invt.pretest_delay', label='Pre-Test Delay (seconds)', default=35,
           desc='Delay before beginning the test.')
info.param('invt.power_factor_range', label='Power Factor Pass/Fail Screen', default=0.05,
           desc='Entering a value of 0.03 means the PF can be within +/-0.03 of the target PF.')
info.param('invt.setpoint_failure_count', label='Setpoint Failure Count', default=5,
           desc='Number of consecutive failures (power factor excursions beyond target PF) which does not '
                'produce a script fail. This accounts for EUT settling times due to DC input transients.')
info.param('invt.verification_delay', label='Verification Delay (seconds)', default=5,
           desc='Wait time allowance before assigning failure for the time parameters.')
info.param('invt.posttest_delay', label='Post-Test Delay (seconds)', default=0,
           desc='Delay after finishing the test.')
info.param('invt.disable', label='Disable INV3 function at end of test?', default='No', values=['Yes', 'No'])

#PV simulator
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


