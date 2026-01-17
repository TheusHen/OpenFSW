%% Orbit propagation with J2 + drag + SRP
% Generates full orbit state history and saves to matlab/data/output.

constants = earth_constants();
params = mission_params();

% Initial state from orbital elements
[r0_km, v0_km_s] = coe2rv(params.orbit, constants.mu_km3_s2);

% Simulation span
period_s = 2 * pi * sqrt(params.orbit.semi_major_axis_km^3 / constants.mu_km3_s2);
num_orbits = 2.0;
span_s = [0, num_orbits * period_s];

state0 = [r0_km; v0_km_s];

opts = odeset('RelTol',1e-10,'AbsTol',1e-12);
[t_s, state] = ode45(@(t, x) orbital_ode(t, x, constants, params), span_s, state0, opts);

% Derived outputs
r_km = state(:,1:3);
v_km_s = state(:,4:6);
alt_km = vecnorm(r_km,2,2) - constants.re_km;

output.t_s = t_s;
output.state = state;
output.alt_km = alt_km;
output.r_km = r_km;
output.v_km_s = v_km_s;
output.params = params;
output.constants = constants;

stamp = datestr(now,'yyyymmdd_HHMMSS');
output_path = fullfile('matlab','data','output',['orbit_propagation_' stamp '.mat']);
if ~exist(fileparts(output_path),'dir')
    mkdir(fileparts(output_path));
end
save(output_path, '-struct', 'output');

fprintf('Orbit propagation complete. Saved to %s\n', output_path);

%% Local functions
function dx = orbital_ode(~, x, constants, params)
    r = x(1:3);
    v = x(4:6);
    rmag = norm(r);

    % Two-body
    a = -constants.mu_km3_s2 * r / rmag^3;

    % J2 perturbation
    z2 = r(3)^2;
    r2 = rmag^2;
    factor = 1.5 * constants.j2 * constants.mu_km3_s2 * constants.re_km^2 / rmag^5;
    a_j2 = factor * [r(1) * (5 * z2 / r2 - 1); r(2) * (5 * z2 / r2 - 1); r(3) * (5 * z2 / r2 - 3)];
    a = a + a_j2;

    % Drag
    altitude_km = rmag - constants.re_km;
    rho = atmosphere_density(altitude_km);
    if rho > 0
        r_m = r * 1000;
        v_m_s = v * 1000;
        omega = [0; 0; constants.omega_earth];
        v_atm = cross(omega, r_m);
        v_rel = v_m_s - v_atm;
        v_rel_mag = norm(v_rel);
        a_drag_m_s2 = -0.5 * rho * params.drag_cd * params.drag_area_m2 / params.mass_kg * v_rel_mag * v_rel;
        a = a + a_drag_m_s2 / 1000;
    end

    % SRP
    sun_dir = [1; 0; 0];
    pressure = constants.solar_pressure;
    a_srp_m_s2 = -pressure * params.srp_cr * params.srp_area_m2 / params.mass_kg * sun_dir;
    a = a + a_srp_m_s2 / 1000;

    dx = [v; a];
end

function rho = atmosphere_density(altitude_km)
    % Simple layered density model [kg/m^3]
    layers = [
        0 25 1.225 7.249;
        25 100 3.899e-2 6.349;
        100 200 5.297e-7 27.0;
        200 350 2.418e-10 53.628;
        350 500 9.518e-12 53.298;
        500 750 3.725e-13 76.828;
        750 1000 1.585e-14 99.0;
        1000 2000 3.019e-15 268.0];

    if altitude_km < 0
        rho = layers(1,3);
        return;
    end
    if altitude_km > 2000
        rho = 1e-18;
        return;
    end

    rho = 1e-18;
    for i = 1:size(layers,1)
        if altitude_km >= layers(i,1) && altitude_km < layers(i,2)
            h_base = layers(i,1);
            rho_base = layers(i,3);
            H = layers(i,4);
            rho = rho_base * exp(-(altitude_km - h_base) / H);
            return;
        end
    end
end

function [r_km, v_km_s] = coe2rv(orbit, mu)
    a = orbit.semi_major_axis_km;
    e = orbit.eccentricity;
    i = deg2rad(orbit.inclination_deg);
    raan = deg2rad(orbit.raan_deg);
    argp = deg2rad(orbit.arg_perigee_deg);
    nu = deg2rad(orbit.true_anomaly_deg);

    p = a * (1 - e^2);
    r_pqw = (p / (1 + e * cos(nu))) * [cos(nu); sin(nu); 0];
    v_pqw = sqrt(mu / p) * [-sin(nu); e + cos(nu); 0];

    R3_raan = [cos(raan) -sin(raan) 0; sin(raan) cos(raan) 0; 0 0 1];
    R1_i = [1 0 0; 0 cos(i) -sin(i); 0 sin(i) cos(i)];
    R3_argp = [cos(argp) -sin(argp) 0; sin(argp) cos(argp) 0; 0 0 1];
    Q = R3_raan * R1_i * R3_argp;

    r_km = Q * r_pqw;
    v_km_s = Q * v_pqw;
end
