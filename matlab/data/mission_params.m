
function params = mission_params()
%MISSION_PARAMS  Baseline mission parameters for OpenFSW 3U.

% Physical properties
params.mass_kg = 4.0;
params.inertia = diag([0.008, 0.008, 0.002]);
params.drag_cd = 2.2;
params.drag_area_m2 = 0.034;  % 0.10 x 0.34 m
params.srp_cr = 1.3;
params.srp_area_m2 = 0.01;    % 0.10 x 0.10 m

% Orbit parameters (ECI, classical elements)
params.orbit.semi_major_axis_km = 6878.0;
params.orbit.eccentricity = 0.001;
params.orbit.inclination_deg = 97.0;
params.orbit.raan_deg = 0.0;
params.orbit.arg_perigee_deg = 0.0;
params.orbit.true_anomaly_deg = 0.0;

% Power system (improved)
params.power.solar_efficiency = 0.28;
params.power.panel_area_m2 = 0.04;
params.power.battery_capacity_Wh = 40.0;
params.power.initial_soc = 0.7;
params.power.payload_load_W = 2.0;
params.power.payload_duty_cycle = 0.25;
params.power.bus_load_W = 3.0;

% Detumble control (new)
params.detumble.max_dipole_Am2 = 0.2;
params.detumble.k_bdot = 1.0e5;
params.detumble.b_field_floor_T = 1.0e-9;

% Link budget
params.link.tx_power_dBm = 30.0;
params.link.tx_gain_dBi = 2.0;
params.link.rx_gain_dBi = 12.0;
params.link.frequency_MHz = 437.0;
params.link.data_rate_bps = 9600.0;
params.link.required_ebno_dB = 10.0;

end
