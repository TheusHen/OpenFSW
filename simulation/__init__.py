"""
OpenFSW-LEO-3U Simulation Framework
====================================

Python-based simulation framework for CubeSat flight software development.

Mission Parameters:
- Platform: 3U CubeSat (10x10x34 cm, ~4kg)
- Orbit: LEO 500km, 97° SSO, ~95min period
- Life: 6-12 months

Components:
- Orbital dynamics (J2 perturbation)
- Attitude dynamics (quaternion-based)
- Sensor models (magnetometer, sun sensor, gyroscope)
- Actuator models (magnetorquers, reaction wheels)
- Environment models (magnetic field, sun position, eclipse)
- Ground station passes
"""

__version__ = "1.0.0"
__mission__ = "OpenFSW-LEO-3U"

from simulation.core.simulator import Simulator
from simulation.core.spacecraft import Spacecraft
from simulation.core.time_manager import SimulationTime

__all__ = [
    'Simulator',
    'Spacecraft', 
    'SimulationTime',
]
