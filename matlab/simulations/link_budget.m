%% Link budget analysis vs elevation

params = mission_params();

c = 299792458;
frequency_hz = params.link.frequency_MHz * 1e6;
lambda = c / frequency_hz;

% Slant range sweep (km)
range_km = linspace(500, 3000, 50);
elevation_deg = linspace(5, 90, 50);

margin_dB = zeros(length(range_km), length(elevation_deg));

for i = 1:length(range_km)
    for j = 1:length(elevation_deg)
        dist_m = range_km(i) * 1000;
        fspl = 20 * log10(4 * pi * dist_m / lambda);

        if elevation_deg(j) < 10
            atm_loss = 2.0;
        elseif elevation_deg(j) < 30
            atm_loss = 0.5;
        else
            atm_loss = 0.2;
        end

        pol_loss = 3.0;
        eirp_dBm = params.link.tx_power_dBm + params.link.tx_gain_dBi - 2.0;
        rx_power_dBm = eirp_dBm - fspl - atm_loss - pol_loss + params.link.rx_gain_dBi - 2.0;

        bandwidth = params.link.data_rate_bps;
        noise_power_dBm = 10 * log10(1.38e-23 * 290 * bandwidth) + 30 + 1.5;
        snr_dB = rx_power_dBm - noise_power_dBm;
        ebno_dB = snr_dB + 10 * log10(bandwidth / params.link.data_rate_bps);
        margin_dB(i,j) = ebno_dB - params.link.required_ebno_dB;
    end
end

output.range_km = range_km;
output.elevation_deg = elevation_deg;
output.margin_dB = margin_dB;
output.params = params;

stamp = datestr(now,'yyyymmdd_HHMMSS');
output_path = fullfile('matlab','data','output',['link_budget_' stamp '.mat']);
if ~exist(fileparts(output_path),'dir')
    mkdir(fileparts(output_path));
end
save(output_path, '-struct', 'output');

fprintf('Link budget analysis complete. Saved to %s\n', output_path);
