#!/usr/bin/env python3
"""
OpenFSW Simulation Example
==========================

Example script demonstrating the simulation framework.
"""

import numpy as np
import time

# Add parent directory to path for imports
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

from simulation.core.config import SimulationConfig, OrbitalParameters
from simulation.core.simulator import Simulator
from simulation.scenarios import DetumbleScenario, NominalScenario


def run_quick_simulation():
    """Run a quick 10-minute simulation."""
    print("=" * 60)
    print("OpenFSW-LEO-3U Quick Simulation")
    print("=" * 60)
    
    # Create configuration
    config = SimulationConfig(
        duration_seconds=600,  # 10 minutes
        time_step_seconds=0.1,
    )
    
    # Create simulator
    sim = Simulator(config)
    
    # Set initial conditions
    sim.set_initial_attitude(
        quaternion=np.array([1, 0, 0, 0]),  # Identity
        angular_velocity_deg_s=np.array([0.5, -0.3, 0.2])  # Slow tumble
    )
    
    print(f"\nSimulation Configuration:")
    print(f"  Duration: {config.duration_seconds} s")
    print(f"  Time step: {config.time_step_seconds} s")
    print(f"  Orbital altitude: {config.orbital.altitude_km} km")
    print(f"  Inclination: {config.orbital.inclination_deg}°")
    
    print("\nRunning simulation...")
    start_time = time.time()
    
    # Run with progress callback
    def progress(p):
        if p > 0:
            print(f"  Progress: {p*100:.0f}%", end='\r')
    
    history = sim.run(progress_callback=progress)
    
    elapsed = time.time() - start_time
    print(f"\nSimulation complete in {elapsed:.2f}s")
    print(f"  Simulated {len(history)} steps")
    print(f"  Real-time factor: {config.duration_seconds / elapsed:.1f}x")
    
    # Print final state
    final = history[-1]
    print(f"\nFinal State:")
    print(f"  Time: {final.time_s:.1f} s")
    print(f"  Altitude: {final.altitude_km:.1f} km")
    print(f"  Angular velocity: {np.linalg.norm(final.angular_velocity)*180/np.pi:.3f} deg/s")
    print(f"  In eclipse: {final.in_eclipse}")
    print(f"  GS visible: {final.gs_visible}")


def run_detumble_scenario():
    """Run detumble scenario."""
    print("\n" + "=" * 60)
    print("Detumble Scenario")
    print("=" * 60)
    
    from simulation.scenarios.detumble import DetumbleScenario, DetumbleScenarioConfig
    
    # Create scenario with shorter duration for demo
    config = DetumbleScenarioConfig(
        max_duration_hours=0.5,  # 30 minutes
        initial_rate_deg_s=5.0,
        target_rate_deg_s=0.5,
    )
    
    scenario = DetumbleScenario(config)
    results = scenario.run()
    
    print(scenario.get_summary())


def run_eclipse_analysis():
    """Run eclipse analysis."""
    print("\n" + "=" * 60)
    print("Eclipse Analysis")
    print("=" * 60)
    
    from simulation.scenarios.eclipse import EclipseScenario, EclipseScenarioConfig
    
    config = EclipseScenarioConfig(duration_orbits=1.0)
    scenario = EclipseScenario(config)
    results = scenario.run()
    
    print(scenario.get_summary())


def demonstrate_sensors():
    """Demonstrate sensor models."""
    print("\n" + "=" * 60)
    print("Sensor Model Demonstration")
    print("=" * 60)
    
    from simulation.sensors.magnetometer import Magnetometer, MagnetometerConfig
    from simulation.sensors.gyroscope import Gyroscope, GyroscopeConfig
    from simulation.sensors.sun_sensor import SunSensorArray, SunSensorArrayConfig
    
    # Create sensors
    mag = Magnetometer(MagnetometerConfig())
    gyro = Gyroscope(GyroscopeConfig())
    sun_sensor = SunSensorArray(SunSensorArrayConfig())
    
    # True values
    true_mag_field = np.array([20000, -10000, 45000])  # nT
    true_omega = np.array([0.01, -0.02, 0.015])  # rad/s
    true_sun_dir = np.array([0.5, 0.5, 0.707])
    
    print("\nMagnetometer:")
    for i in range(5):
        measured = mag.measure(true_mag_field)
        print(f"  Sample {i+1}: [{measured[0]:.1f}, {measured[1]:.1f}, {measured[2]:.1f}] nT")
    
    print("\nGyroscope:")
    for i in range(5):
        measured = gyro.measure(true_omega, dt=0.1)
        print(f"  Sample {i+1}: [{measured[0]*1000:.2f}, {measured[1]*1000:.2f}, {measured[2]*1000:.2f}] mrad/s")
    
    print("\nSun Sensor Array:")
    for i in range(5):
        result = sun_sensor.measure(true_sun_dir)
        if result['valid']:
            dir = result['direction']
            print(f"  Sample {i+1}: [{dir[0]:.3f}, {dir[1]:.3f}, {dir[2]:.3f}]")


def demonstrate_link_budget():
    """Demonstrate link budget calculation."""
    print("\n" + "=" * 60)
    print("Link Budget Analysis")
    print("=" * 60)
    
    from simulation.models.link_budget import LinkBudget
    
    link = LinkBudget()
    
    # Analyze at different distances
    distances = [500, 1000, 2000, 3000]
    
    print("\nUHF Link Budget (437 MHz, 1W TX, 9600 bps):")
    print("-" * 50)
    print(f"{'Distance':>10} {'Elevation':>10} {'Rx Power':>12} {'Margin':>10} {'Status':>10}")
    print("-" * 50)
    
    for dist in distances:
        # Calculate elevation (approximate)
        elev = np.degrees(np.arcsin(500 / dist)) if dist > 500 else 90
        elev = min(elev, 90)
        
        result = link.calculate_link(dist, elev)
        status = "✓ OK" if result['link_closed'] else "✗ FAIL"
        
        print(f"{dist:>10} km {elev:>9.1f}° {result['rx_power_dBm']:>10.1f} dBm "
              f"{result['margin_dB']:>9.1f} dB {status:>10}")
    
    # Calculate max range
    max_range = link.calculate_max_range(min_margin_dB=3.0)
    print(f"\nMaximum range with 3 dB margin: {max_range:.0f} km")


if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description="OpenFSW Simulation Examples")
    parser.add_argument('--all', action='store_true', help='Run all examples')
    parser.add_argument('--quick', action='store_true', help='Run quick simulation')
    parser.add_argument('--detumble', action='store_true', help='Run detumble scenario')
    parser.add_argument('--eclipse', action='store_true', help='Run eclipse analysis')
    parser.add_argument('--sensors', action='store_true', help='Demonstrate sensors')
    parser.add_argument('--link', action='store_true', help='Link budget analysis')
    
    args = parser.parse_args()
    
    # Default to quick if no args
    if not any(vars(args).values()):
        args.quick = True
    
    if args.all or args.quick:
        run_quick_simulation()
    
    if args.all or args.detumble:
        run_detumble_scenario()
    
    if args.all or args.eclipse:
        run_eclipse_analysis()
    
    if args.all or args.sensors:
        demonstrate_sensors()
    
    if args.all or args.link:
        demonstrate_link_budget()
    
    print("\n" + "=" * 60)
    print("Examples complete!")
    print("=" * 60)
