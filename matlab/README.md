# MATLAB Mission Analysis Suite

This folder contains MATLAB-first mission analysis scripts intended to mirror and extend the Python simulation stack with higher-fidelity workflows. Each script writes `.mat` outputs into `matlab/data/output/` so you can load the results directly in MATLAB/Simulink or post-process them with your own tooling.

## Contents

- `simulations/orbit_propagation.m` — 2-body + J2 + drag + SRP orbit propagation using `ode45`.
- `simulations/attitude_detumble.m` — Rigid body attitude dynamics with B-dot detumble law and gravity-gradient torque.
- `simulations/power_budget.m` — Orbit eclipse analysis and battery state-of-charge model.
- `simulations/link_budget.m` — Pass-by-pass link margin model vs elevation.
- `simulations/run_all.m` — Runs every simulation and stores data outputs.

## How to run

From MATLAB:

```matlab
addpath(genpath('matlab'));
run('matlab/simulations/run_all.m');
```

Each script will create a timestamped `.mat` file in `matlab/data/output/`.

## Data files

Shared constants and mission configuration live in:

- `matlab/data/earth_constants.m`
- `matlab/data/mission_params.m`

Generated data files are stored in `matlab/data/output/`.
