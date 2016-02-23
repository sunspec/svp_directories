<scriptConfig name="VV12_3" script="VV">
  <params>
    <param name="vv.settings.timeout_period" type="int">0</param>
    <param name="vv.settings.time_window" type="int">0</param>
    <param name="invt.posttest_delay" type="int">0</param>
    <param name="vv.settings.curve_num" type="int">1</param>
    <param name="invt.pretest_delay" type="int">3</param>
    <param name="vv.settings.n_points" type="int">4</param>
    <param name="comm.slave_id" type="int">5</param>
    <param name="vv.settings.ramp_time" type="int">10</param>
    <param name="invt.var_range" type="float">15.0</param>
    <param name="invt.verification_delay" type="int">35</param>
    <param name="invt.setpoint_failure_count" type="int">120</param>
    <param name="invt.setpoint_period" type="int">300</param>
    <param name="comm.baudrate" type="int">9600</param>
    <param index_count="4" index_start="1" name="vv.curve.var" type="float">50.0 0.0 0.0 -50.0 </param>
    <param index_count="4" index_start="1" name="vv.curve.volt" type="float">97.0 99.0 101.0 103.0 </param>
    <param name="comm.ifc_name" type="string">COM3</param>
    <param name="gridsim.auto_config" type="string">Disabled</param>
    <param name="pvsim.mode" type="string">Manual</param>
    <param name="gridsim.mode" type="string">Manual</param>
    <param name="das.mode" type="string">Manual</param>
    <param name="comm.parity" type="string">N</param>
    <param name="invt.disable" type="string">No</param>
    <param name="comm.ifc_type" type="string">RTU</param>
    <param name="profile.profile_name" type="string">VV Profile</param>
    <param name="vv.settings.vv_mode" type="string">VV12 (var priority)</param>
  </params>
</scriptConfig>
