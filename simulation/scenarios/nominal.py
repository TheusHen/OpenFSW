"""
Nominal Operations Scenario
===========================

Standard mission operations with sun-pointing attitude.
"""

import numpy as np
from typing import Dict, Optional
from dataclasses import dataclass
from ..core.config import SimulationConfig, OrbitalParameters
from ..core.simulator import Simulator


@dataclass
class NominalScenarioConfig:
    """Configuration for nominal scenario."""
    duration_orbits: float = 1.0
    initial_attitude: str = 'nadir'  # 'nadir', 'sun_pointing', 'inertial'
    enable_adcs: bool = True
    pointing_accuracy_deg: float = 5.0


class NominalScenario:
    """
    Nominal mission operations scenario.
    
    Tests:
    - Normal sun-pointing operations
    - Eclipse transitions
    - Ground station passes
    - Housekeeping telemetry
    """
    
    def __init__(self, config: NominalScenarioConfig = None):
        """
        Initialize nominal scenario.
        
        Args:
            config: Scenario configuration
        """
        self.config = config or NominalScenarioConfig()
        
        # Create simulation config
        orbital_period = 95 * 60  # ~95 minutes for 500km
        self.sim_config = SimulationConfig(
            duration_seconds=orbital_period * self.config.duration_orbits,
            time_step_seconds=0.1,
        )
        
        self.simulator: Optional[Simulator] = None
        self.results: Dict = {}
        self.history = []
    
    def setup(self):
        """Setup scenario."""
        self.simulator = Simulator(self.sim_config)
        
        # Set initial attitude based on config
        if self.config.initial_attitude == 'nadir':
            # Nadir pointing: Z-axis towards Earth
            self.simulator.set_initial_attitude(
                quaternion=np.array([1, 0, 0, 0]),
                angular_velocity_deg_s=np.array([0, 0, 0])
            )
        elif self.config.initial_attitude == 'sun_pointing':
            # Sun pointing: will be computed at runtime
            pass
        
        # Add ADCS controller if enabled
        if self.config.enable_adcs:
            self.simulator.add_step_callback(self._adcs_controller)
    
    def _adcs_controller(self, sim: Simulator, state):
        """Simple proportional attitude controller."""
        # Target: reduce angular velocity
        omega = sim.spacecraft.attitude_state.angular_velocity
        
        # Proportional control (B-dot like)
        gain = 0.01
        torque_cmd = -gain * omega
        
        # Convert to magnetorquer dipole (simplified)
        b_field = state.mag_field_body_uT * 1e-6  # Convert to T
        b_norm = np.linalg.norm(b_field)
        
        if b_norm > 1e-9:
            # Cross product to get required dipole
            dipole = np.cross(torque_cmd, b_field) / (b_norm ** 2)
            sim.command_magnetorquers(dipole)
    
    def run(self, progress_callback=None) -> Dict:
        """
        Run nominal scenario.
        
        Returns:
            Results dictionary
        """
        if self.simulator is None:
            self.setup()
        
        print(f"Running Nominal Scenario: {self.config.duration_orbits} orbits")
        
        history = self.simulator.run(progress_callback=progress_callback)
        self.history = history
        
        # Analyze results
        self.results = self._analyze_results(history)
        
        return self.results
    
    def _analyze_results(self, history) -> Dict:
        """Analyze scenario results."""
        if not history:
            return {}
        
        # Calculate statistics
        altitudes = [s.altitude_km for s in history]
        eclipse_fraction = sum(1 for s in history if s.in_eclipse) / len(history)
        gs_fraction = sum(1 for s in history if s.gs_visible) / len(history)
        
        # Angular velocity magnitude over time
        omega_mags = [np.linalg.norm(s.angular_velocity) for s in history]
        
        return {
            'duration_s': history[-1].time_s,
            'num_samples': len(history),
            'altitude_min_km': min(altitudes),
            'altitude_max_km': max(altitudes),
            'altitude_mean_km': np.mean(altitudes),
            'eclipse_fraction': eclipse_fraction,
            'gs_contact_fraction': gs_fraction,
            'final_omega_deg_s': np.degrees(omega_mags[-1]),
            'max_omega_deg_s': np.degrees(max(omega_mags)),
            'min_omega_deg_s': np.degrees(min(omega_mags)),
        }
    
    def get_summary(self) -> str:
        """Get human-readable summary."""
        if not self.results:
            return "Scenario not yet run."
        
        return f"""
Nominal Scenario Summary
========================
Duration: {self.results['duration_s']:.1f} s ({self.results['duration_s']/60:.1f} min)
Samples: {self.results['num_samples']}

Orbit:
  Altitude: {self.results['altitude_min_km']:.1f} - {self.results['altitude_max_km']:.1f} km
  Mean altitude: {self.results['altitude_mean_km']:.1f} km

Environment:
  Eclipse fraction: {self.results['eclipse_fraction']*100:.1f}%
  GS contact fraction: {self.results['gs_contact_fraction']*100:.1f}%

Attitude:
  Final rate: {self.results['final_omega_deg_s']:.3f} deg/s
  Max rate: {self.results['max_omega_deg_s']:.3f} deg/s
"""
