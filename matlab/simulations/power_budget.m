%% Power budget simulation with eclipse and battery SOC

constants = earth_constants();
params = mission_params();

period_s = 2 * pi * sqrt(params.orbit.semi_major_axis_km^3 / constants.mu_km3_s2);
num_orbits = 2.0;

dt = 1.0;
time_s = (0:dt:num_orbits*period_s)';

sun_dir = [1; 0; 0];

soc = zeros(size(time_s));
illumination = zeros(size(time_s));
net_power_W = zeros(size(time_s));
payload_power_W = zeros(size(time_s));

soc(1) = params.power.initial_soc;
battery_capacity_Wh = params.power.battery_capacity_Wh;

for k = 1:length(time_s)
    t = time_s(k);
    theta = 2 * pi * t / period_s;
    r_eci = params.orbit.semi_major_axis_km * [cos(theta); sin(theta); 0];

    illumination(k) = eclipse_fraction(r_eci, sun_dir, constants.re_km);

    power_gen = params.power.panel_area_m2 * constants.solar_flux * params.power.solar_efficiency * illumination(k);

    payload_power_W(k) = params.power.payload_load_W * params.power.payload_duty_cycle;
    power_load = payload_power_W(k) + params.power.bus_load_W;

    net_power_W(k) = power_gen - power_load;

    if k > 1
        dE_Wh = net_power_W(k) * dt / 3600;
        soc(k) = min(max(soc(k-1) + dE_Wh / battery_capacity_Wh, 0), 1.0);
    end
end

output.time_s = time_s;
output.illumination = illumination;
output.net_power_W = net_power_W;
output.payload_power_W = payload_power_W;
output.soc = soc;
output.params = params;
output.constants = constants;

stamp = datestr(now,'yyyymmdd_HHMMSS');
output_path = fullfile('matlab','data','output',['power_budget_' stamp '.mat']);
if ~exist(fileparts(output_path),'dir')
    mkdir(fileparts(output_path));
end
save(output_path, '-struct', 'output');

fprintf('Power budget simulation complete. Saved to %s\n', output_path);

%% Local functions
function fraction = eclipse_fraction(r_eci, sun_dir, re_km)
    sun_dir = sun_dir / max(norm(sun_dir), 1e-12);
    proj = dot(r_eci, sun_dir) * sun_dir;
    perp = r_eci - proj;
    perp_dist = norm(perp);

    if dot(r_eci, sun_dir) > 0
        fraction = 1.0;
        return;
    end

    if perp_dist < re_km
        fraction = 0.0;
    else
        fraction = 1.0;
    end
end
