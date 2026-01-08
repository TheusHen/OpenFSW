#!/usr/bin/env python3
"""Run *complete* OpenFSW validations.

This script executes:
- Firmware cross-build (ARM) + CTest (if any)
- Python unit tests (pytest)
- Simulation examples + scenarios
- Ground example

It writes full logs + data + images into build/reports/.

Usage:
  python3 tools/run_all.py
  python3 tools/run_all.py --out build/reports
"""

from __future__ import annotations

import argparse
import contextlib
import csv
import io
import json
import os
import shutil
import subprocess
import sys
from dataclasses import asdict, is_dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterable, Optional

# Force headless plotting
import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np


REPO_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_OUT_ROOT = REPO_ROOT / "build" / "reports"


def _utc_stamp() -> str:
    return datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%SZ")


def _run_cmd(
    cmd: list[str],
    *,
    cwd: Path,
    log_path: Path,
    env: Optional[dict[str, str]] = None,
) -> int:
    log_path.parent.mkdir(parents=True, exist_ok=True)
    with log_path.open("w", encoding="utf-8") as f:
        f.write(f"$ {' '.join(cmd)}\n")
        f.write(f"cwd={cwd}\n\n")
        f.flush()
        proc = subprocess.Popen(
            cmd,
            cwd=str(cwd),
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            env=env,
        )
        assert proc.stdout is not None
        for line in proc.stdout:
            f.write(line)
        return proc.wait()


def _git_info() -> dict[str, Any]:
    def _git(args: list[str]) -> str:
        try:
            out = subprocess.check_output(["git", *args], cwd=str(REPO_ROOT), text=True).strip()
            return out
        except Exception:
            return ""

    return {
        "commit": _git(["rev-parse", "HEAD"]),
        "branch": _git(["rev-parse", "--abbrev-ref", "HEAD"]),
        "status_porcelain": _git(["status", "--porcelain"]),
    }


def _write_json(path: Path, obj: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)

    def _default(o: Any):
        # Numpy types
        if isinstance(o, np.ndarray):
            return o.tolist()
        if isinstance(o, np.generic):
            return o.item()
        # Dataclasses
        if is_dataclass(o):
            return asdict(o)
        return str(o)

    path.write_text(json.dumps(obj, indent=2, sort_keys=True, default=_default) + "\n", encoding="utf-8")


def _history_to_rows(history: Iterable[Any]) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for s in history:
        # SimulationState dataclass or similar
        rows.append(
            {
                "time_s": float(getattr(s, "time_s")),
                "altitude_km": float(getattr(s, "altitude_km")),
                "omega_x_rad_s": float(getattr(s, "angular_velocity")[0]),
                "omega_y_rad_s": float(getattr(s, "angular_velocity")[1]),
                "omega_z_rad_s": float(getattr(s, "angular_velocity")[2]),
                "omega_mag_deg_s": float(np.degrees(np.linalg.norm(getattr(s, "angular_velocity")))),
                "in_eclipse": bool(getattr(s, "in_eclipse")),
                "gs_visible": bool(getattr(s, "gs_visible")),
                "gs_elevation_deg": float(getattr(s, "gs_elevation_deg")),
            }
        )
    return rows


def _write_csv(path: Path, rows: list[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    if not rows:
        path.write_text("", encoding="utf-8")
        return
    with path.open("w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=list(rows[0].keys()))
        writer.writeheader()
        writer.writerows(rows)


def _plot_timeseries(rows: list[dict[str, Any]], out_png: Path, title: str) -> None:
    out_png.parent.mkdir(parents=True, exist_ok=True)
    if not rows:
        return

    t_min = np.array([r["time_s"] for r in rows]) / 60.0
    alt = np.array([r["altitude_km"] for r in rows])
    omega = np.array([r["omega_mag_deg_s"] for r in rows])
    eclipse = np.array([1.0 if r["in_eclipse"] else 0.0 for r in rows])
    gs_vis = np.array([1.0 if r["gs_visible"] else 0.0 for r in rows])

    fig, axs = plt.subplots(4, 1, figsize=(12, 10), sharex=True)
    fig.suptitle(title)

    axs[0].plot(t_min, alt)
    axs[0].set_ylabel("Altitude (km)")
    axs[0].grid(True)

    axs[1].plot(t_min, omega)
    axs[1].set_ylabel("|ω| (deg/s)")
    axs[1].grid(True)

    axs[2].step(t_min, eclipse, where="post")
    axs[2].set_ylabel("Eclipse")
    axs[2].set_yticks([0, 1])
    axs[2].grid(True)

    axs[3].step(t_min, gs_vis, where="post")
    axs[3].set_ylabel("GS Visible")
    axs[3].set_yticks([0, 1])
    axs[3].set_xlabel("Time (min)")
    axs[3].grid(True)

    fig.tight_layout(rect=(0, 0, 1, 0.96))
    fig.savefig(out_png, dpi=160)
    plt.close(fig)


def _run_simulation_bundle(out_dir: Path, *, profile: str) -> dict[str, Any]:
    # Import here so repo root is on sys.path
    sys.path.insert(0, str(REPO_ROOT))

    from simulation.core.config import SimulationConfig
    from simulation.core.simulator import Simulator
    from simulation.scenarios.detumble import DetumbleScenario, DetumbleScenarioConfig
    from simulation.scenarios.eclipse import EclipseScenario, EclipseScenarioConfig
    from simulation.scenarios.ground_pass import GroundPassScenario, GroundPassScenarioConfig
    from simulation.scenarios.nominal import NominalScenario, NominalScenarioConfig
    from simulation.scenarios.safe_mode import SafeModeScenario, SafeModeScenarioConfig

    results: dict[str, Any] = {}

    # Deterministic runs for reports/CI
    np.random.seed(0)

    def _capture(name: str, fn):
        buf = io.StringIO()
        with contextlib.redirect_stdout(buf), contextlib.redirect_stderr(buf):
            out = fn()
        (out_dir / "logs").mkdir(parents=True, exist_ok=True)
        (out_dir / "logs" / f"simulation_{name}.log").write_text(buf.getvalue(), encoding="utf-8")
        return out

    # Quick sim
    def quick():
        if profile == "full":
            duration_s, dt_s = 600, 0.1
        else:
            duration_s, dt_s = 300, 0.2

        config = SimulationConfig(duration_seconds=duration_s, time_step_seconds=dt_s)
        sim = Simulator(config)
        sim.set_initial_attitude(
            quaternion=np.array([1, 0, 0, 0]),
            angular_velocity_deg_s=np.array([0.5, -0.3, 0.2]),
        )
        history = sim.run()
        return {"config": {"duration_seconds": config.duration_seconds, "time_step_seconds": config.time_step_seconds}, "history": history}

    quick_out = _capture("quick", quick)
    quick_history = quick_out["history"]
    quick_rows = _history_to_rows(quick_history)
    _write_csv(out_dir / "data" / "quick_timeseries.csv", quick_rows)
    _plot_timeseries(quick_rows, out_dir / "images" / "quick_timeseries.png", "Quick Simulation")
    results["quick"] = {"samples": len(quick_rows), **quick_out["config"]}

    if profile == "full":
        detumble_cfg = DetumbleScenarioConfig(max_duration_hours=2.0, initial_rate_deg_s=10.0, target_rate_deg_s=0.5)
        eclipse_cfg = EclipseScenarioConfig(duration_orbits=2.0)
        ground_cfg = GroundPassScenarioConfig(duration_orbits=3.0)
        nominal_cfg = NominalScenarioConfig(duration_orbits=1.0)
        safe_cfg = SafeModeScenarioConfig(duration_orbits=3.0)
        dt_overrides = {
            "eclipse": 0.5,
            "ground_pass": 1.0,
            "nominal": 0.1,
            "safe_mode": 0.1,
        }
    elif profile == "standard":
        # Standard profile: runs everything with moderate cost.
        detumble_cfg = DetumbleScenarioConfig(max_duration_hours=1.5, initial_rate_deg_s=10.0, target_rate_deg_s=0.5)
        eclipse_cfg = EclipseScenarioConfig(duration_orbits=0.5)
        ground_cfg = GroundPassScenarioConfig(duration_orbits=0.5)
        nominal_cfg = NominalScenarioConfig(duration_orbits=0.2)
        safe_cfg = SafeModeScenarioConfig(duration_orbits=0.5)
        dt_overrides = {
            "eclipse": 2.0,
            "ground_pass": 5.0,
            "nominal": 1.0,
            "safe_mode": 1.0,
        }
    else:
        # Smoke profile: fast, still generates complete artifacts (logs/CSV/PNG) for every scenario.
        # IMPORTANT: Detumble physics are slow (typically tens of minutes). Keep duration realistic.
        detumble_cfg = DetumbleScenarioConfig(max_duration_hours=1.5, initial_rate_deg_s=10.0, target_rate_deg_s=0.5)
        eclipse_cfg = EclipseScenarioConfig(duration_orbits=0.2)
        ground_cfg = GroundPassScenarioConfig(duration_orbits=0.2)
        nominal_cfg = NominalScenarioConfig(duration_orbits=0.1)
        safe_cfg = SafeModeScenarioConfig(duration_orbits=0.2)
        dt_overrides = {
            "eclipse": 10.0,
            "ground_pass": 10.0,
            "nominal": 5.0,
            "safe_mode": 5.0,
        }

    scenarios = {
        "detumble": DetumbleScenario(detumble_cfg),
        "eclipse": EclipseScenario(eclipse_cfg),
        "ground_pass": GroundPassScenario(ground_cfg),
        "nominal": NominalScenario(nominal_cfg),
        "safe_mode": SafeModeScenario(safe_cfg),
    }

    for name, scenario in scenarios.items():
        # Override dt before setup() creates the Simulator.
        if name in dt_overrides and getattr(scenario, "sim_config", None) is not None:
            scenario.sim_config.time_step_seconds = float(dt_overrides[name])

        def _run():
            return scenario.run()

        res = _capture(name, _run)
        results[name] = res
        _write_json(out_dir / "data" / f"{name}_results.json", res)

        history = getattr(scenario, "history", None)
        if history:
            rows = _history_to_rows(history)
            _write_csv(out_dir / "data" / f"{name}_timeseries.csv", rows)
            _plot_timeseries(rows, out_dir / "images" / f"{name}_timeseries.png", f"Scenario: {name}")

        # Detumble has extra rate history plot
        if name == "detumble" and getattr(scenario, "rate_history", None):
            t_min = np.array(getattr(scenario, "time_history", [])) / 60.0
            rate = np.array(getattr(scenario, "rate_history", []))
            fig, ax = plt.subplots(figsize=(12, 6))
            ax.semilogy(t_min, np.maximum(rate, 1e-6))
            ax.set_xlabel("Time (min)")
            ax.set_ylabel("Angular rate (deg/s)")
            ax.set_title("Detumble rate history")
            ax.grid(True, which="both")
            fig.tight_layout()
            (out_dir / "images").mkdir(parents=True, exist_ok=True)
            fig.savefig(out_dir / "images" / "detumble_rate.png", dpi=160)
            plt.close(fig)

    return results


def main() -> int:
    parser = argparse.ArgumentParser(description="Run complete tests + simulations and write artifacts into build/")
    parser.add_argument("--out", default=str(DEFAULT_OUT_ROOT), help="Output root (default: build/reports)")
    parser.add_argument("--skip-firmware", action="store_true", help="Skip ARM firmware build")
    parser.add_argument("--skip-pytests", action="store_true", help="Skip pytest")
    parser.add_argument("--skip-sim", action="store_true", help="Skip simulations")
    parser.add_argument("--skip-ground", action="store_true", help="Skip ground example")
    parser.add_argument(
        "--profile",
        choices=["smoke", "standard", "full"],
        default="smoke",
        help="Simulation workload profile (default: smoke)",
    )
    args = parser.parse_args()

    out_root = Path(args.out)
    stamp = _utc_stamp()
    run_dir = out_root / stamp
    latest_dir = out_root / "latest"

    run_dir.mkdir(parents=True, exist_ok=True)
    (run_dir / "logs").mkdir(exist_ok=True)
    (run_dir / "data").mkdir(exist_ok=True)
    (run_dir / "images").mkdir(exist_ok=True)

    meta = {
        "timestamp_utc": stamp,
        "python": sys.version,
        "repo": str(REPO_ROOT),
        "git": _git_info(),
    }
    _write_json(run_dir / "meta.json", meta)

    summary: dict[str, Any] = {"meta": meta, "steps": {}}

    # Firmware build
    if not args.skip_firmware:
        code = _run_cmd(
            [
                "cmake",
                "-S",
                ".",
                "-B",
                "build-arm",
                "-DCMAKE_TOOLCHAIN_FILE=cmake/arm-none-eabi.cmake",
                "-G",
                "Unix Makefiles",
            ],
            cwd=REPO_ROOT,
            log_path=run_dir / "logs" / "firmware_configure.log",
        )
        code2 = _run_cmd(
            ["cmake", "--build", "build-arm", "-j"],
            cwd=REPO_ROOT,
            log_path=run_dir / "logs" / "firmware_build.log",
        )
        code3 = _run_cmd(
            ["ctest", "--test-dir", "build-arm", "--output-on-failure"],
            cwd=REPO_ROOT,
            log_path=run_dir / "logs" / "ctest.log",
        )
        summary["steps"]["firmware"] = {"configure": code, "build": code2, "ctest": code3}

    # Pytests
    if not args.skip_pytests:
        code = _run_cmd(
            [
                sys.executable,
                "-m",
                "pytest",
                "-q",
                "--disable-warnings",
                "--maxfail=1",
                f"--junitxml={str(run_dir / 'data' / 'pytest-junit.xml')}",
                "tests",
            ],
            cwd=REPO_ROOT,
            log_path=run_dir / "logs" / "pytest.log",
            env={**os.environ, "PYTHONPATH": str(REPO_ROOT)},
        )
        summary["steps"]["pytest"] = {"exit_code": code}

    # Simulations
    if not args.skip_sim:
        try:
            sim_results = _run_simulation_bundle(run_dir, profile=args.profile)
            _write_json(run_dir / "data" / "simulation_summary.json", sim_results)
            summary["steps"]["simulations"] = {"ok": True, "scenarios": list(sim_results.keys())}
        except KeyboardInterrupt:
            (run_dir / "logs" / "simulation_runner_error.log").write_text("KeyboardInterrupt\n", encoding="utf-8")
            summary["steps"]["simulations"] = {"ok": False, "error": "KeyboardInterrupt"}
        except Exception as e:
            (run_dir / "logs" / "simulation_runner_error.log").write_text(str(e) + "\n", encoding="utf-8")
            summary["steps"]["simulations"] = {"ok": False, "error": str(e)}

    # Ground example (subprocess to keep output identical to user-facing demo)
    if not args.skip_ground:
        code = _run_cmd(
            [sys.executable, "-m", "ground.examples.ground_example"],
            cwd=REPO_ROOT,
            log_path=run_dir / "logs" / "ground_example.log",
            env={**os.environ, "PYTHONPATH": str(REPO_ROOT)},
        )
        summary["steps"]["ground"] = {"exit_code": code}

    _write_json(run_dir / "summary.json", summary)

    # Human-readable summary
    lines = [
        f"OpenFSW Validation Report ({stamp})",
        f"Output: {run_dir}",
        "",
        "Steps:",
    ]
    for k, v in summary["steps"].items():
        lines.append(f"- {k}: {v}")
    (run_dir / "summary.txt").write_text("\n".join(lines) + "\n", encoding="utf-8")

    # Refresh latest/
    if latest_dir.exists():
        shutil.rmtree(latest_dir)
    shutil.copytree(run_dir, latest_dir)

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
