# MATLAB Data Outputs

This folder contains baseline configuration files (`earth_constants.m`, `mission_params.m`) and a writable `output/` directory where simulations store generated `.mat` files.

## Output files

Each simulation writes a timestamped `.mat` with a consistent structure:

- `orbit_propagation_*.mat` → `t_s`, `state`, `alt_km`, `r_km`, `v_km_s`
- `attitude_detumble_*.mat` → `time_s`, `q`, `omega_rad_s`
- `power_budget_*.mat` → `time_s`, `illumination`, `net_power_W`, `soc`
- `link_budget_*.mat` → `range_km`, `elevation_deg`, `margin_dB`

## Usage

```matlab
load('matlab/data/output/orbit_propagation_YYYYMMDD_HHMMSS.mat')
plot(t_s/60, alt_km)
```
