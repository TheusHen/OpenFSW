# Validation pipeline (tests + simulations + artifacts)

OpenFSW provides a single entrypoint to run the full validation flow and generate artifacts.

## One-command run

From the repository root:

- Full pipeline:

  `python3 tools/run_all.py --profile smoke`

- Skip firmware build (Python-only):

  `python3 tools/run_all.py --skip-firmware --profile smoke`

Profiles:
- `smoke`: fast, still generates complete artifacts
- `standard`: moderate runtime
- `full`: longer/heavier

Detumble note:
- Magnetic detumble (B-dot) is intentionally run on a realistic time horizon (tens of minutes). Even in `smoke`, detumble runs long enough to be physically meaningful.

## Outputs

Artifacts are written into:

- `build/reports/<timestamp>/`
- `build/reports/latest/` (copy of the most recent run)

### Logs

`build/reports/latest/logs/`

Includes:
- `firmware_configure.log`, `firmware_build.log`
- `ctest.log`
- `pytest.log`
- `simulation_*.log`
- `ground_example.log`

### Data exports

`build/reports/latest/data/`

Includes:
- `*_timeseries.csv` — time series exports for scenarios (time, altitude, |ω|, eclipse, GS visibility)
- `*_results.json` — scenario summary metrics
- `simulation_summary.json`
- `pytest-junit.xml`

### Images

`build/reports/latest/images/`

Includes:
- `*_timeseries.png` — altitude/|ω|/eclipse/GS visibility vs time
- `detumble_rate.png` — semilog plot of detumble rate history

## Notes

- Firmware is bare-metal ARM; `ctest` is used for orchestration and (currently) runs host-side Python tests as a CTest test.
- Simulation plots use a headless Matplotlib backend (Agg), so no GUI is required.

## Example: detumble result

The runner writes a scenario summary into `build/reports/latest/data/detumble_results.json`.

Typical successful run characteristics are:
- large rate reduction ($>90\%$)
- time-to-target on the order of $\sim 30$–$90$ minutes (depends on initial rate, gain, dipole limit, and orbit/magnetic field)
