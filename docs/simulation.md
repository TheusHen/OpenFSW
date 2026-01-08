# Simulation framework

OpenFSW includes a Python simulation framework in `simulation/`.

## High-level architecture

- `simulation/core/` — simulator loop, spacecraft state, time management, configuration
- `simulation/dynamics/` — orbital + attitude dynamics and integrators
- `simulation/environment/` — sun/eclipse, magnetic field, atmosphere (optional), ground station geometry
- `simulation/sensors/` — magnetometer, gyro, sun sensors
- `simulation/actuators/` — magnetorquers (reaction wheel stub available)
- `simulation/scenarios/` — scenario runners (detumble, nominal, eclipse, ground pass, safe mode)
- `simulation/models/` — support models (link budget, power/thermal stubs)

## Units and conventions

- Position: kilometers (km)
- Velocity: km/s
- Attitude: quaternion `[w, x, y, z]` (scalar-first)
- Angular velocity: rad/s (internally); scenario outputs often report deg/s
- Magnetic field:
  - Environment uses SI Tesla internally where noted
  - `SimulationState.mag_field_body_uT` is stored in microtesla (µT)

## Outputs

The simulator logs a `SimulationState` at a configurable rate. The validation runner exports:

- CSV: `*_timeseries.csv`
- Plots: `*_timeseries.png`

Columns include:
- `time_s`, `altitude_km`
- `omega_*_rad_s`, `omega_mag_deg_s`
- `in_eclipse`, `gs_visible`, `gs_elevation_deg`

## Scenarios

- Detumble: magnetic B-dot control (magnetorquers)
- Nominal: nominal operations with a simple controller
- Eclipse: eclipse transitions/events
- Ground pass: GS visibility and pass tracking
- Safe mode: fault injection + safe-mode controller

## Limitations (current)

- The simulation is intended for development and architectural validation, not high-fidelity flight qualification.
- Environmental models are simplified.
- Controller tuning is scenario-dependent.

## Detumble time scale

Detumble is a slow process in realistic magnetic control: expect convergence on the order of tens of minutes, not seconds.
