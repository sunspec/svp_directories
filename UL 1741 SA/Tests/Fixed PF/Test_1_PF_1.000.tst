<scriptConfig name="Test_1_PF_1.000" script="Fixed_PF">
  <params>
    <param name="invt.posttest_delay" type="int">0</param>
    <param name="inv3.pf_acc" type="float">0.01</param>
    <param name="invt.power_factor_range" type="float">0.06</param>
    <param name="inv3.power_factor" type="float">1.0</param>
    <param name="invt.verification_delay" type="int">1</param>
    <param name="inv3.MSA_Vac" type="float">1.0</param>
    <param name="inv3.pf_settling_time" type="float">1.0</param>
    <param name="inv3.MSA_Vdc" type="float">1.0</param>
    <param name="invt.pretest_delay" type="int">2</param>
    <param name="comm.slave_id" type="int">5</param>
    <param name="invt.setpoint_failure_count" type="int">20</param>
    <param name="inv3.p_low" type="float">20.0</param>
    <param name="inv3.p_high" type="float">100.0</param>
    <param name="inv3.v_low" type="float">200.0</param>
    <param name="inv3.dc_nom" type="float">460.0</param>
    <param name="inv3.v_high" type="float">600.0</param>
    <param name="comm.baudrate" type="int">9600</param>
    <param name="comm.ifc_name" type="string">COM3</param>
    <param name="datatrig.dsm_method" type="string">Disabled - Data from EUT</param>
    <param name="datatrig.trigger_method" type="string">Disabled - Data from EUT</param>
    <param name="pvsim.mode" type="string">Manual</param>
    <param name="comm.parity" type="string">N</param>
    <param name="comm.ifc_type" type="string">RTU</param>
    <param name="invt.disable" type="string">Yes</param>
  </params>
</scriptConfig>
