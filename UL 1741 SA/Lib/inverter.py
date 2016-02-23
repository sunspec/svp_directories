"""
  Copyright (c) 2015, SunSpec Alliance
  All Rights Reserved

  Software created under the SunSpec Alliance - Sandia National Laboratories CRADA 1831.00
"""



import time

# connection state control enumeration as specified in SunSpec model 123
CONN_DISCONNECT = 0
CONN_CONNECT = 1

# connection state status bitmasks as specified in SunSpec model 122
PVCONN_CONNECTED = (1 << 0)
PVCONN_AVAILABLE = (1 << 1)
PVCONN_OPERATING = (1 << 2)
PVCONN_TEST = (1 << 3)

# Status Active Control bitmasks as specified in SunSpec model 122
STACTCTL_FIXED_W = (1 << 0)
STACTCTL_FIXED_VAR = (1 << 1)
STACTCTL_FIXED_PF = (1 << 2)
STACTCTL_VOLT_VAR = (1 << 3)
STACTCTL_FREQ_WATT_PARAM = (1 << 4)
STACTCTL_FREQ_WATT_CURVE = (1 << 5)
STACTCTL_DYN_REACTIVE_POWER = (1 << 6)
STACTCTL_LVRT = (1 << 7)
STACTCTL_HVRT = (1 << 8)
STACTCTL_WATT_PF = (1 << 9)
STACTCTL_VOLT_WATT = (1 << 10)
STACTCTL_SCHEDULED = (1 << 12)
STACTCTL_LFRT = (1 << 13)
STACTCTL_HFRT = (1 << 14)

VOLTVAR_WMAX = 1
VOLTVAR_VARMAX = 2
VOLTVAR_VARAVAL = 3


class InverterError(Exception):
    pass

# returns a string associated with the connection state for output purposes
def conn_state_str(state):
    if state == CONN_DISCONNECT:
        return 'disconnected'
    elif state == CONN_CONNECT:
        return 'connected'
    return 'unknown'

# returns: 0 if disconnected, 1 if connected
def get_conn_state(inv):
    try:
        inv.status.read()
        connected = inv.status.PVConn & PVCONN_CONNECTED
        return connected
    except Exception, e:
        raise InverterError('Unable to read connection status: %s' % str(e))

# returns: 0 if not enabled, 1 if enabled
def get_active_control_status(inv, control):
    try:
        inv.status.read()
        enabled = (inv.status.StActCtl & control) == control
        return enabled
    except Exception, e:
        raise InverterError('Unable to read status: %s' % str(e))

# writes the INV1 parameters and executes the command with an optional trigger
def set_conn_state(inv, state, time_window=0, timeout_period=0, trigger=None):
    try:
        inv.controls.read()
        inv.controls.Conn_WinTms = time_window
        inv.controls.Conn_RvrtTms = timeout_period
        inv.controls.write()
        inv.controls.Conn = state
        # trigger sent just before the EUT has the connect/disconnect command written
        if trigger is not None:
            trigger.on()
        inv.controls.write()
    except Exception, e:
        raise InverterError('Unable to set connection state: %s' % str(e))

# returns: current power generation in watts
def get_power(inv, das=None):
    try:
        #only use the das (data acquisition system) if it is available
        if das:
            das.read()
            return das.ac_watts
        # without the das use the EUT to report the power level
        else:
            inv.inverter.read()
            return inv.inverter.W
    except Exception, e:
        raise InverterError('Unable to get power from das or EUT: %s' % str(e))

# returns: current power generation in watts
def get_time(das=None):
    try:
        #only use the das (data acquisition system) if it is available
        if das:
            das.read()
            return das.time
        # without the das use the EUT to report the power level
        else:
            import time
            return time.time()
    except Exception, e:
        raise InverterError('Unable to get power from das or EUT: %s' % str(e))

# returns: current power generation normalized by nameplate power (0 to 1)
def get_power_norm(inv, das=None):
    try:
        power = get_power(inv, das=das)
        inv.nameplate.read()
        return float(power) / float(inv.nameplate.WRtg)
    except Exception, e:
        raise InverterError('Unable to get power from das or EUT: %s' % str(e))

# returns: current
def get_current(inv, das=None):
    try:
        #only use the das (data acquisition system) if it is available
        if das:
            das.read()
            return float(das.ac_current)
        # without the das use the EUT to report the current
        else:
            inv.inverter.read()
            return float(inv.inverter.A)
            # in the future, could return current on all phases
            # return (float(inv.inverter.AphA),float(inv.inverter.AphB),float(inv.inverter.AphC))
    except Exception, e:
        raise InverterError('Unable to get current from das or EUT: %s' % str(e))

# returns: current normalize by the EUT rating (0 to 1)
def get_current_norm(inv, das=None):
    try:
        current = get_current(inv, das=das)
        inv.nameplate.read()
        return float(current) / float(inv.nameplate.ARtg)
    except Exception, e:
        raise InverterError('Unable to get current from das or EUT: %s' % str(e))

# returns: current ac voltage
def get_ac_voltage(inv, das=None):
    try:
        #only use the das (data acquisition system) if it is available
        if das:
            das.read()
            gridVraw = das.ac_voltage
        # without the das use the EUT to report the voltage
        else:
            inv.inverter.read()
            gridVraw = float(inv.inverter.PhVphA)
        return float(gridVraw)
    except Exception, e:
        raise script.ScriptFail('Unable to get ac voltage from das or EUT: %s' % str(e))

def get_ac_voltage_norm(inv, das=None):
    try:
        voltage = get_ac_voltage(inv, das=das)
        inv.settings.read()
        Vgrid_nom = float(inv.settings.VRef)
        return voltage/Vgrid_nom
    except Exception, e:
        raise script.ScriptFail('Unable to normalize ac voltage with inv.settings.VRef, %s' % str(e))

def get_ac_voltage_pct(inv, das=None):
    try:
        return get_ac_voltage(inv, das=das)*100.0
    except Exception, e:
        raise script.ScriptFail('Unable to convert normalized ac voltage to percent, %s' % str(e))

# returns: grid frequency in hertz
def get_freq(inv, das=None):
    try:
        #only use the das (data acquisition system) if it is available
        if das:
            das.read()
            return das.ac_freq
        # without the das use the EUT to report the power level
        else:
            inv.inverter.read()
            return inv.inverter.Hz
    except Exception, e:
        raise InverterError('Unable to get power from das or EUT: %s' % str(e))

# returns: grid frequency in hertz
def get_freq_norm(inv, das=None):
    try:
        freq = get_freq(inv, das=das)
        inv.settings.read()
        return freq / float(inv.settings.ECPNomHz)  # need to verify
    except Exception, e:
        raise InverterError('Unable to get power from das or EUT: %s' % str(e))

# returns: current power factor
def get_power_factor(inv, das=None):
    try:
        #only use the das (data acquisition system) if it is available
        if das:
            das.read()
            return das.ac_pf
        # without the das use the EUT to report the power level
        else:
            inv.inverter.read()
            pf = inv.inverter.PF
            if pf is not None and pf > 1.0:
                pf = pf/100.0
            return pf
    except Exception, e:
        raise InverterError('Unable to get power factor from das or EUT: %s' % str(e))

# returns: True if state == current connection state, False if not
def in_conn_state(inv, state):
    try:
        connected = get_conn_state(inv)
        if state == CONN_DISCONNECT and not connected:
            return True
        elif state == CONN_CONNECT and connected:
            return True
    except Exception, e:
        raise InverterError('Unable to read connection status: %s' % str(e))
    
    return False

# returns: True if power generation matches threshold expectation for current state, False if not
def verify_conn_state_power(inv, state, threshold=50, das=None):
    try:
        power = get_power(inv, das)
        # the state is 0 (disconnected) or 1 (connected)
        if state == CONN_DISCONNECT:
            # use a power threshold to determine if the EUT has performed the INV1 command
            if power <= threshold:
                return True
        elif state == CONN_CONNECT:
            # use a power threshold to determine if the EUT has performed the INV1 command
            if power >= threshold:
                return True
        else:
            raise Exception('Unknown state: %s' % str(state))
    except Exception, e:
        raise InverterError('Unable to verify power: %s' % str(e))

    return False

# returns: True if state == current connection state and power generation matches threshold expectation, False if not
def verify_conn_state(inv, state, threshold=50, das=None):
    return in_conn_state(inv, state) and verify_conn_state_power(inv, state, threshold, das)

def set_power_limit(inv, time_window=0, timeout_period=0, ramp_time=0, power_limit_pct=100, enable=0, trigger=None):
    try:
        inv.controls.read()
        inv.controls.WMaxLimPct_WinTms = time_window
        inv.controls.WMaxLimPct_RvrtTms = timeout_period
        inv.controls.WMaxLimPct_RmpTms = ramp_time
        inv.controls.WMaxLimPct = power_limit_pct
        inv.controls.write()
        inv.controls.WMaxLim_Ena = enable
        # trigger sent just before the EUT has the connect/disconnect command written
        if trigger is not None:
            trigger.on()
        inv.controls.write()
    except Exception, e:
        raise InverterError('Unable to set power limit: %s' % str(e))

def set_power_factor(inv, time_window=0, timeout_period=0, ramp_time=0, power_factor=1, enable=0, trigger=None):
    try:
        inv.controls.read()
        inv.controls.OutPFSet_WinTms = time_window
        inv.controls.OutPFSet_RvrtTms = timeout_period
        inv.controls.OutPFSet_RmpTms = ramp_time
        inv.controls.OutPFSet = power_factor
        inv.controls.write()
        inv.controls.OutPFSet_Ena = enable
        # trigger sent just before the EUT has the enable command written
        if trigger is not None:
            trigger.on()
        inv.controls.write()
    except Exception, e:
        raise InverterError('Unable to set power factor limit: %s' % str(e))


def set_vrt_trip_high(inv, h_time=None, h_volt=None, h_n_points=0, h_curve_num=0,
                      time_window=0, timeout_period=0, ramp_time=0,
                      enable=0, trigger=None):
    # SunSpec defines the HVRT/LVRT settings in different sunspec models
    try:
        if h_curve_num > 0:
            inv.hvrtd.read()
            inv.hvrtd.RmpTms = ramp_time
            inv.hvrtd.RvrtTms = timeout_period
            inv.hvrtd.WinTms = time_window

            for i in xrange(1, h_n_points + 1): # Uses the SunSpec indexing rules (start at 1)
                time_point = 'Tms%d' % (i)
                volt_point = 'V%d' % (i)
                setattr(inv.hvrtd.l_curve[h_curve_num], time_point, h_time[i])
                setattr(inv.hvrtd.l_curve[h_curve_num], volt_point, h_volt[i])

            inv.hvrtd.write()

            inv.hvrtd.ActCrv = h_curve_num
            inv.hvrtd.ModEna = enable

            # trigger sent just before the EUT has the enable command written
            if trigger is not None:
                trigger.on()

            inv.hvrtd.write()

        else:
            raise InverterError('HVRT curve number invalid.')

    except Exception, e:
        raise InverterError('Unable to set HVRT: %s' % str(e))


def set_vrt_trip_low(inv, l_time=None, l_volt=None, l_n_points=0, l_curve_num=0,
                     time_window=0, timeout_period=0, ramp_time=0,
                     enable=0, trigger=None):
    try:
        if l_curve_num > 0:
            inv.lvrtd.read()
            inv.lvrtd.RmpTms = ramp_time
            inv.lvrtd.RvrtTms = timeout_period
            inv.lvrtd.WinTms = time_window

            for i in xrange(1, l_n_points + 1): # Uses the SunSpec indexing rules (start at 1)
                time_point = 'Tms%d' % (i)
                volt_point = 'V%d' % (i)
                setattr(inv.lvrtd.l_curve[l_curve_num], time_point, l_time[i])
                setattr(inv.lvrtd.l_curve[l_curve_num], volt_point, l_volt[i])

            inv.lvrtd.write()

            inv.lvrtd.ActCrv = l_curve_num
            inv.lvrtd.ModEna = enable

            # trigger sent just before the EUT has the enable command written
            if trigger is not None:
                trigger.on()

            inv.lvrtd.write()

        else:
            raise InverterError('LVRT curve number invalid.')

    except Exception, e:
        raise InverterError('Unable to set LVRT: %s' % str(e))


def set_vrt_stay_connected_high(inv, h_time=None, h_volt=None, h_n_points=0, h_curve_num=0,
                                time_window=0, timeout_period=0, ramp_time=0,
                                enable=0, trigger=None):

    # SunSpec defines the HVRT/LVRT must remain connected settings in different sunspec models
    try:
        if h_curve_num > 0:
            inv.hvrtc.read()
            inv.hvrtc.RmpTms = ramp_time
            inv.hvrtc.RvrtTms = timeout_period
            inv.hvrtc.WinTms = time_window

            for i in xrange(1, h_n_points + 1): # Uses the SunSpec indexing rules (start at 1)
                time_point = 'Tms%d' % (i)
                volt_point = 'V%d' % (i)
                setattr(inv.hvrtc.l_curve[h_curve_num], time_point, h_time[i])
                setattr(inv.hvrtc.l_curve[h_curve_num], volt_point, h_volt[i])

            inv.hvrtc.write()

            inv.hvrtc.ActCrv = h_curve_num
            inv.hvrtc.ModEna = enable

            # trigger sent just before the EUT has the enable command written
            if trigger is not None:
                trigger.on()

            inv.hvrtc.write()

        else:
            raise InverterError('HVRTC curve number invalid.')

    except Exception, e:
        raise InverterError('Unable to set HVRTC: %s' % str(e))


def set_vrt_stay_connected_low(inv, l_time=None, l_volt=None, l_n_points=0, l_curve_num=0,
                                time_window=0, timeout_period=0, ramp_time=0,
                                enable=0, trigger=None):

    try:
        if l_curve_num > 0:
            inv.lvrtc.read()
            inv.lvrtc.RmpTms = ramp_time
            inv.lvrtc.RvrtTms = timeout_period
            inv.lvrtc.WinTms = time_window

            for i in xrange(1, l_n_points + 1):  # Uses the SunSpec indexing rules (start at 1)
                time_point = 'Tms%d' % (i)
                volt_point = 'V%d' % (i)
                setattr(inv.lvrtc.l_curve[l_curve_num], time_point, l_time[i])
                setattr(inv.lvrtc.l_curve[l_curve_num], volt_point, l_volt[i])

            inv.lvrtc.write()

            inv.lvrtc.ActCrv = l_curve_num
            inv.lvrtc.ModEna = enable

            # trigger sent just before the EUT has the enable command written
            if trigger is not None:
                trigger.on()

            inv.lvrtc.write()

        else:
            raise InverterError('LVRTC curve number invalid.')

    except Exception, e:
        raise InverterError('Unable to set LVRTC: %s' % str(e))


def set_frt_trip_high(inv, h_time=None, h_freq=None, h_n_points=0, h_curve_num=0,
                      time_window=0, timeout_period=0, ramp_time=0,
                      enable=0, trigger=None):
    # SunSpec defines the HFRT/LFRT settings in different sunspec models
    try:
        if h_curve_num > 0:
            inv.hfrtd.read()
            inv.hfrtd.RmpTms = ramp_time
            inv.hfrtd.RvrtTms = timeout_period
            inv.hfrtd.WinTms = time_window

            for i in xrange(1, h_n_points + 1): # Uses the SunSpec indexing rules (start at 1)
                time_point = 'Tms%d' % (i)
                freq_point = 'F%d' % (i)
                setattr(inv.hfrtd.l_curve[h_curve_num], time_point, h_time[i])
                setattr(inv.hfrtd.l_curve[h_curve_num], freq_point, h_freq[i])

            inv.hfrtd.write()

            inv.hfrtd.ActCrv = h_curve_num
            inv.hfrtd.ModEna = enable

            # trigger sent just before the EUT has the enable command written
            if trigger is not None:
                trigger.on()

            inv.hfrtd.write()

        else:
            raise InverterError('HFRT curve number invalid.')

    except Exception, e:
        raise InverterError('Unable to set HFRT: %s' % str(e))


def set_frt_trip_low(inv, l_time=None, l_freq=None, l_n_points=0, l_curve_num=0,
                     time_window=0, timeout_period=0, ramp_time=0,
                     enable=0, trigger=None):
    try:
        if l_curve_num > 0:
            inv.lfrtd.read()
            inv.lfrtd.RmpTms = ramp_time
            inv.lfrtd.RvrtTms = timeout_period
            inv.lfrtd.WinTms = time_window

            for i in xrange(1, l_n_points + 1):  # Uses the SunSpec indexing rules (start at 1)
                time_point = 'Tms%d' % (i)
                freq_point = 'F%d' % (i)
                setattr(inv.lfrtd.l_curve[l_curve_num], time_point, l_time[i])
                setattr(inv.lfrtd.l_curve[l_curve_num], freq_point, l_freq[i])

            inv.lfrtd.write()

            inv.lfrtd.ActCrv = l_curve_num
            inv.lfrtd.ModEna = enable

            # trigger sent just before the EUT has the enable command written
            if trigger is not None:
                trigger.on()

            inv.lfrtd.write()

        else:
            raise InverterError('LFRT curve number invalid.')

    except Exception, e:
        raise InverterError('Unable to set LFRT: %s' % str(e))


def set_frt_stay_connected_high(inv, h_time=None, h_freq=None, h_n_points=0, h_curve_num=0,
                                time_window=0, timeout_period=0, ramp_time=0,
                                enable=0, trigger=None):

    # SunSpec defines the HFRT/LFRT must remain connected settings in different sunspec models
    try:
        if h_curve_num > 0:
            inv.hfrtc.read()
            inv.hfrtc.RmpTms = ramp_time
            inv.hfrtc.RvrtTms = timeout_period
            inv.hfrtc.WinTms = time_window

            for i in xrange(1, h_n_points + 1): # Uses the SunSpec indexing rules (start at 1)
                time_point = 'Tms%d' % (i)
                freq_point = 'F%d' % (i)
                setattr(inv.hfrtc.l_curve[h_curve_num], time_point, h_time[i])
                setattr(inv.hfrtc.l_curve[h_curve_num], freq_point, h_freq[i])

            inv.hfrtc.write()

            inv.hfrtc.ActCrv = h_curve_num
            inv.hfrtc.ModEna = enable

            # trigger sent just before the EUT has the enable command written
            if trigger is not None:
                trigger.on()

            inv.hfrtc.write()

        else:
            raise InverterError('HFRTC curve number invalid.')

    except Exception, e:
        raise InverterError('Unable to set HFRTC: %s' % str(e))


def set_frt_stay_connected_low(inv, l_time=None, l_freq=None, l_n_points=0, l_curve_num=0,
                               time_window=0, timeout_period=0, ramp_time=0,
                               enable=0, trigger=None):

    try:
        if l_curve_num > 0:
            inv.lfrtc.read()
            inv.lfrtc.RmpTms = ramp_time
            inv.lfrtc.RvrtTms = timeout_period
            inv.lfrtc.WinTms = time_window

            for i in xrange(1, l_n_points + 1): # Uses the SunSpec indexing rules (start at 1)
                time_point = 'Tms%d' % (i)
                freq_point = 'F%d' % (i)
                setattr(inv.lfrtc.l_curve[l_curve_num], time_point, l_time[i])
                setattr(inv.lfrtc.l_curve[l_curve_num], freq_point, l_freq[i])

            inv.lfrtc.write()

            inv.lfrtc.ActCrv = l_curve_num
            inv.lfrtc.ModEna = enable

            # trigger sent just before the EUT has the enable command written
            if trigger is not None:
                trigger.on()

            inv.lfrtc.write()

        else:
            raise InverterError('LFRTC curve number invalid.')

    except Exception, e:
        raise InverterError('Unable to set LFRTC: %s' % str(e))


def set_volt_var(inv, volt=None, var=None, n_points=0, time_window=0, timeout_period=0, ramp_time=0, curve_num=0,
                 deptRef=2, enable=0, trigger=None):
    try:
        if curve_num > 0:
            inv.volt_var.read()
            #inv.volt_var.curve[curve_num].RmpTms = ramp_time
            #inv.volt_var.curve[curve_num].RmpIncTmm = ramp_rate
            #inv.volt_var.RvrtTms = timeout_period
            #inv.volt_var.WinTms = time_window
            #inv.volt_var.curve[curve_num].DeptRef = deptRef

            for i in xrange(1,n_points + 1): # Uses the SunSpec indexing rules (start at 1)
                volt_point = 'V%d' % (i)
                var_point = 'VAr%d' % (i)
                setattr(inv.volt_var.curve[curve_num], volt_point, volt[i])
                setattr(inv.volt_var.curve[curve_num], var_point, var[i])

            inv.volt_var.write()

            inv.volt_var.ActCrv = curve_num
            inv.volt_var.ModEna = enable

            # trigger sent just before the EUT has the enable command written
            if trigger is not None:
                trigger.on()

            inv.volt_var.write()

        else:
            raise InverterError('Volt/var curve number invalid.')

    except Exception, e:
        raise InverterError('Unable to set volt/var curve: %s' % str(e))


def set_freq_watt(inv, fw_mode='FW21 (FW parameters)', freq=None, W=None, n_points=0, curve_num=0, timeout_period=0,
                  ramp_time=0, recovery_ramp_rate=0, time_window=0, WGra=65, HzStr=0.2, HzStop=0.1, HysEna=1,
                  HzStopWGra=10000., enable=0, trigger=None):

    if fw_mode == 'FW21 (FW parameters)':
        try:
            inv.freq_watt_param.read()
            inv.freq_watt_param.WGra = WGra
            inv.freq_watt_param.HzStr = HzStr
            if HysEna == 'Yes':
                inv.freq_watt_param.HzStop = HzStop
                inv.freq_watt_param.HysEna = 1
            else:
                inv.freq_watt_param.HysEna = 0
            if HzStopWGra == 0:
                inv.freq_watt_param.HzStopWGra = 10000  #This is for testing at Sandia with a specific manufacturer.
            else:
                inv.freq_watt_param.HzStopWGra = HzStopWGra
            inv.freq_watt_param.write()

            inv.freq_watt_param.ModEna = enable
            # trigger sent just before the EUT has the enable command written
            if trigger is not None:
                trigger.on()
            inv.freq_watt_param.write()

        except Exception, e:
            raise InverterError('Unable to set parameterized freq/watt. Check the parameters can be written: %s' % str(e))

    else:  #FW22
        try:
            if curve_num > 0:
                inv.freq_watt_crv.read()
                inv.freq_watt_crv.curve[curve_num].RmpTms = ramp_time
                #inv.freq_watt_crv.curve[curve_num].RmpIncTmm = ramp_rate
                #inv.freq_watt_crv.curve[curve_num].RmpDecTmm = ramp_rate
                inv.freq_watt_crv.RmpRsUp = recovery_ramp_rate
                inv.freq_watt_crv.RvrtTms = timeout_period
                inv.freq_watt_crv.WinTms = time_window

                for i in xrange(1,n_points + 1): # Uses the SunSpec indexing rules (start at 1)
                    freq_point = 'Hz%d' % (i)
                    W_point = 'W%d' % (i)
                    setattr(inv.freq_watt_crv.curve[curve_num], freq_point, freq[i])
                    setattr(inv.freq_watt_crv.curve[curve_num], W_point, W[i])

                inv.freq_watt_crv.write()

                inv.freq_watt_crv.ActCrv = curve_num
                inv.freq_watt_crv.ModEna = enable

                # trigger sent just before the EUT has the enable command written
                if trigger is not None:
                    trigger.on()

                inv.freq_watt_crv.write()

            else:
                raise InverterError('Volt/var curve number invalid. Curve number is %s' % curve_num)

        except Exception, e:
            raise InverterError('Unable to set freq/watt curve: %s' % str(e))

# returns: reactive power in vars
def get_var(inv, das=None):
    try:
        #only use the das (data acquisition system) if it is available
        if das:
            das.read()
            var = das.ac_vars
        # without the das use the EUT to report the power level
        else:
            inv.inverter.read()
            var = inv.inverter.VAr
            if var is None:
                raise InverterError('Inverter does not have VAr in the inverter model.')
            var = float(var)
        return var

    except Exception, e:
        raise InverterError('Unable to get var from das or EUT: %s' % str(e))

if __name__ == "__main__":
    pass




