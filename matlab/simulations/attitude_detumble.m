%% Attitude detumble simulation (B-dot + gravity gradient)

constants = earth_constants();
params = mission_params();

% Initial conditions
q0 = [1; 0; 0; 0];
omega0 = deg2rad([5; -3; 2]);

% Orbit reference (circular)
alt_km = params.orbit.semi_major_axis_km - constants.re_km;
orbital_radius_km = constants.re_km + alt_km;
orbital_rate = sqrt(constants.mu_km3_s2 / orbital_radius_km^3); % rad/s

% Simulation settings
sim_time_s = 3600;
dt = 0.05;
steps = floor(sim_time_s / dt);

q = zeros(4, steps);
omega = zeros(3, steps);
time = zeros(steps, 1);

q(:,1) = q0;
omega(:,1) = omega0;

% B-dot gain and actuator limits
k_bdot = params.detumble.k_bdot; % A*m^2 / (T/s)
max_dipole = params.detumble.max_dipole_Am2;
b_field_floor = params.detumble.b_field_floor_T;

for k = 1:(steps-1)
    t = (k-1) * dt;
    time(k) = t;

    % Simple circular orbit position
    theta = orbital_rate * t;
    r_eci_km = orbital_radius_km * [cos(theta); sin(theta); 0];

    % Magnetic field (dipole) in ECI
    b_eci = earth_dipole_field(r_eci_km * 1000);

    % Rotate to body frame
    R_bi = quat_to_dcm(q(:,k))';
    b_body = R_bi * b_eci;

    % B-dot law: m = -k * dB/dt ≈ -k * (omega x B)
    b_norm = norm(b_body);
    if b_norm < b_field_floor
        b_body = b_body / max(b_norm, 1e-12) * b_field_floor;
    end
    bdot = cross(omega(:,k), b_body);
    m_cmd = -k_bdot * bdot;
    m_cmd = max(min(m_cmd, max_dipole), -max_dipole);

    % Torque from magnetorquers
    tau_mag = cross(m_cmd, b_body);

    % Gravity gradient torque
    tau_gg = gravity_gradient_torque(params.inertia, r_eci_km, q(:,k), constants.mu_km3_s2);

    tau_total = tau_mag + tau_gg;

    % Propagate attitude
    [q(:,k+1), omega(:,k+1)] = rk4_attitude_step(q(:,k), omega(:,k), tau_total, params.inertia, dt);

    if any(~isfinite(q(:,k+1))) || any(~isfinite(omega(:,k+1)))
        warning('NaN detected at t=%.2f s. Stopping integration.', t);
        q(:,k+1:end) = repmat(q(:,k), 1, steps - k);
        omega(:,k+1:end) = repmat(omega(:,k), 1, steps - k);
        break;
    end
end

time(end) = sim_time_s;

output.time_s = time;
output.q = q;
output.omega_rad_s = omega;
output.params = params;
output.constants = constants;

stamp = datestr(now,'yyyymmdd_HHMMSS');
output_path = fullfile('matlab','data','output',['attitude_detumble_' stamp '.mat']);
if ~exist(fileparts(output_path),'dir')
    mkdir(fileparts(output_path));
end
save(output_path, '-struct', 'output');

fprintf('Attitude detumble complete. Saved to %s\n', output_path);

%% Local functions
function [q_next, omega_next] = rk4_attitude_step(q, omega, torque, inertia, dt)
    k1 = attitude_derivatives(q, omega, torque, inertia);
    k2 = attitude_derivatives(q + 0.5 * dt * k1(1:4), omega + 0.5 * dt * k1(5:7), torque, inertia);
    k3 = attitude_derivatives(q + 0.5 * dt * k2(1:4), omega + 0.5 * dt * k2(5:7), torque, inertia);
    k4 = attitude_derivatives(q + dt * k3(1:4), omega + dt * k3(5:7), torque, inertia);

    q_next = q + (dt/6) * (k1(1:4) + 2*k2(1:4) + 2*k3(1:4) + k4(1:4));
    omega_next = omega + (dt/6) * (k1(5:7) + 2*k2(5:7) + 2*k3(5:7) + k4(5:7));

    q_next = q_next / max(norm(q_next), 1e-12);
end

function dx = attitude_derivatives(q, omega, torque, inertia)
    Omega = 0.5 * [
        0 -omega(1) -omega(2) -omega(3);
        omega(1) 0 omega(3) -omega(2);
        omega(2) -omega(3) 0 omega(1);
        omega(3) omega(2) -omega(1) 0];
    qdot = Omega * q;

    H = inertia * omega;
    omega_dot = inertia \ (torque - cross(omega, H));
    dx = [qdot; omega_dot];
end

function dcm = quat_to_dcm(q)
    w = q(1); x = q(2); y = q(3); z = q(4);
    dcm = [
        1-2*(y*y+z*z) 2*(x*y-w*z) 2*(x*z+w*y);
        2*(x*y+w*z) 1-2*(x*x+z*z) 2*(y*z-w*x);
        2*(x*z-w*y) 2*(y*z+w*x) 1-2*(x*x+y*y)];
end

function tau = gravity_gradient_torque(inertia, r_eci_km, q, mu)
    r_km = norm(r_eci_km);
    r_m = r_km * 1000;
    nadir_eci = -r_eci_km / r_km;
    R = quat_to_dcm(q);
    nadir_body = R' * nadir_eci;
    factor = 3 * mu * 1e9 / r_m^3; % convert km^3 to m^3
    tau = factor * cross(nadir_body, inertia * nadir_body);
end

function b = earth_dipole_field(r_m)
    mu0 = 4 * pi * 1e-7;
    M = 7.94e22; % Earth's dipole moment [A*m^2]
    r = norm(r_m);
    if r < 1
        b = [0; 0; 0];
        return;
    end
    m_vec = [0; 0; M];
    b = (mu0 / (4*pi)) * (3 * r_m * dot(m_vec, r_m) / r^5 - m_vec / r^3);
end
