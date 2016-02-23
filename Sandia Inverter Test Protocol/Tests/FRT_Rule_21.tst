<scriptConfig name="FRT_Rule_21" script="FRT">
  <params>
    <param name="frt.settings.time_window" type="int">0</param>
    <param name="frt.settings.timeout_period" type="int">0</param>
    <param name="frt.settings.ramp_time" type="int">0</param>
    <param name="invt.time_msa" type="float">0.1</param>
    <param name="frt.settings.lc_curve_num" type="int">1</param>
    <param name="frt.settings.hc_curve_num" type="int">1</param>
    <param name="frt.settings.l_curve_num" type="int">1</param>
    <param name="frt.settings.h_curve_num" type="int">1</param>
    <param name="invt.test_point_offset" type="float">1.0</param>
    <param name="comm.slave_id" type="int">1</param>
    <param name="frt.settings.hc_n_points" type="int">4</param>
    <param name="frt.settings.lc_n_points" type="int">4</param>
    <param name="frt.settings.l_n_points" type="int">4</param>
    <param name="frt.settings.h_n_points" type="int">4</param>
    <param name="invt.frt_period" type="int">5</param>
    <param name="invt.verification_delay" type="int">5</param>
    <param name="invt.posttest_delay" type="int">10</param>
    <param name="invt.pretest_delay" type="int">10</param>
    <param name="invt.failure_count" type="int">60</param>
    <param name="comm.baudrate" type="int">9600</param>
    <param index_count="4" index_start="1" name="frt.hc_curve.hc_time" type="float">0.0 0.0 0.0 0.0 </param>
    <param index_count="4" index_start="1" name="frt.h_curve.h_time" type="float">0.0 0.0 0.0 0.0 </param>
    <param index_count="4" index_start="1" name="frt.lc_curve.lc_time" type="float">0.0 0.0 0.0 0.0 </param>
    <param index_count="4" index_start="1" name="frt.l_curve.l_time" type="float">0.0 0.0 0.0 0.0 </param>
    <param index_count="4" index_start="1" name="frt.hc_curve.hc_freq" type="float">100.0 100.0 100.0 100.0 </param>
    <param index_count="4" index_start="1" name="frt.lc_curve.lc_freq" type="float">100.0 100.0 100.0 100.0 </param>
    <param index_count="4" index_start="1" name="frt.h_curve.h_freq" type="float">100.0 100.0 100.0 100.0 </param>
    <param index_count="4" index_start="1" name="frt.l_curve.l_freq" type="float">100.0 100.0 100.0 100.0 </param>
    <param name="comm.ifc_name" type="string">COM3</param>
    <param name="gridsim.auto_config" type="string">Disabled</param>
    <param name="datatrig.dsm_method" type="string">Disabled - Data from EUT</param>
    <param name="pvsim.mode" type="string">Manual</param>
    <param name="gridsim.mode" type="string">Manual</param>
    <param name="comm.parity" type="string">N</param>
    <param name="invt.disable" type="string">No</param>
    <param name="comm.ifc_type" type="string">RTU</param>
    <param name="frt.settings.ride_through" type="string">Yes</param>
  </params>
</scriptConfig>
