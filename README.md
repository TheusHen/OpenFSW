# OpenFSW

OpenFSW is an open-source Flight Software (FSW) + Ground + Simulation stack for a realistic 3U LEO CubeSat-style mission.

This repository contains:
- A bare-metal ARM/FreeRTOS firmware build (flight-side scaffolding + comms TM/TC)
- A Python simulation framework (orbit + attitude + environment + sensors + actuators)
- A Python ground-segment toolkit (telemetry decode/processing + telecommand generation/scheduling)

## Creators

- Matheus Henrique (aka: TheusHen) — developer
- Iago Toledo — astrophysics student

## Repository layout

- `flight/` — flight software (C)
- `ground/` — ground segment (Python)
- `simulation/` — simulation framework + scenarios (Python)
- `linker/` — linker scripts for bare-metal builds
- `third_party/` — vendor dependencies (e.g., FreeRTOS kernel)
- `tools/` — automation scripts (run-all pipeline)
- `docs/` — design notes, protocols, standards, safety

## Quick start

### 1) Run the complete validation pipeline (recommended)

This runs:
- ARM firmware configure/build + `ctest`
- Python unit tests (`pytest`)
- Simulations + scenario runs
- Ground example

It writes full logs + exported data (CSV/JSON/JUnit XML) + PNG plots into `build/reports/`.

Run:

`python3 tools/run_all.py --profile smoke`

Profiles:
- `smoke` (default): fast, still generates complete artifacts
- `standard`: moderate runtime
- `full`: heavier/longer runs

Detumble note: convergence is intentionally evaluated over tens of minutes (not a 3-minute window).

Artifacts:
- `build/reports/latest/` (most recent)
- `build/reports/<timestamp>/` (archived run)

### 2) Firmware build (ARM bare-metal)

Configure + build (cross compile):

`cmake -S . -B build-arm -DCMAKE_TOOLCHAIN_FILE=cmake/arm-none-eabi.cmake -G "Unix Makefiles"`

`cmake --build build-arm -j`

Run tests registered with CTest:

`ctest --test-dir build-arm --output-on-failure`

Note: this is a bare-metal build; host execution is not performed.

### 3) Run simulations only

`PYTHONPATH=. python3 -m simulation.examples.run_simulation`

Or use the pipeline runner to generate plots/data:

`python3 tools/run_all.py --skip-firmware --profile smoke`

## Current validation snapshot (generated artifacts)

After running `tools/run_all.py`, inspect:
- Logs: `build/reports/latest/logs/`
- Data exports: `build/reports/latest/data/`
- Plots: `build/reports/latest/images/`

Example detumble metrics are emitted into `build/reports/latest/data/detumble_results.json`.

## Documentation

See `docs/` for deeper notes and the documentation index in `docs/README.md`.

## Powered by

<img width="1200" height="462" alt="FreeRTOS" src="https://github.com/user-attachments/assets/d0d671ad-61b6-403a-82ed-470d9fe997ff" />
