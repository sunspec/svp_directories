<scriptConfig name="PF_mid_ind" script="SA12_power_factor">
  <params>
    <param name="ratings.pf_min_cap" type="float">-0.85</param>
    <param name="ratings.pf_min_ind" type="float">0.85</param>
    <param name="ratings.pf_settling_time" type="int">1</param>
    <param name="profile.irr_start" type="float">1000.0</param>
    <param name="ratings.p_rated" type="int">3000</param>
    <param name="das.mode" type="string">DAS Simulation</param>
    <param name="gridsim.auto_config" type="string">Disabled</param>
    <param name="pvsim.mode" type="string">Manual</param>
    <param name="der.mode" type="string">Manual</param>
    <param name="gridsim.mode" type="string">Manual</param>
    <param name="profile.profile_name" type="string">None</param>
    <param name="ratings.pf_target" type="string">PF_mid_ind</param>
    <param name="das.sim.data_file" type="string">data.csv</param>
  </params>
</scriptConfig>
