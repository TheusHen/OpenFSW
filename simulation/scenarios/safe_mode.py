"""
Safe Mode Scenario
==================

Emergency safe mode operations testing.
"""

import numpy as np
from typing import Dict, Optional
from dataclasses import dataclass
from ..core.config import SimulationConfig
from ..core.simulator import Simulator


@dataclass
class SafeModeScenarioConfig:
    """Configuration for safe mode scenario."""
    duration_orbits: float = 3.0
    trigger_fault: str = 'attitude_loss'  # 'attitude_loss', 'power_low', 'comms_loss'
    fault_time_s: float = 300.0  # When to inject fault
    recovery_expected: bool = True


class SafeModeScenario:
    """
    Safe mode operations scenario.
    
    Tests:
    - Fault detection and mode transition
    - Sun acquisition for power
    - Reduced operations
    - Recovery procedures
    """
    
    def __init__(self, config: SafeModeScenarioConfig = None):
        """
        Initialize safe mode scenario.
        
        Args:
            config: Scenario configuration
        """
        self.config = config or SafeModeScenarioConfig()
        
        orbital_period = 95 * 60
        self.sim_config = SimulationConfig(
            duration_seconds=orbital_period * self.config.duration_orbits,
            time_step_seconds=0.1,
        )
        
        self.simulator: Optional[Simulator] = None
        self.results: Dict = {}
        self.history = []
        self.fault_injected = False
        self.in_safe_mode = False
    
    def setup(self):
        """Setup scenario."""
        self.simulator = Simulator(self.sim_config)
        self.fault_injected = False
        self.in_safe_mode = False
        
        self.simulator.add_step_callback(self._safe_mode_logic)
    
    def _safe_mode_logic(self, sim: Simulator, state):
        """Safe mode detection and control logic."""
        # Inject fault at specified time
        if not self.fault_injected and state.time_s >= self.config.fault_time_s:
            self._inject_fault(sim)
            self.fault_injected = True
        
        # Detect conditions requiring safe mode
        if not self.in_safe_mode:
            if self._check_safe_mode_trigger(sim, state):
                self._enter_safe_mode(sim)
                self.in_safe_mode = True
        else:
            # Safe mode control: simple sun acquisition
            self._safe_mode_control(sim, state)
    
    def _inject_fault(self, sim: Simulator):
        """Inject fault based on configuration."""
        if self.config.trigger_fault == 'attitude_loss':
            # Add large disturbance torque
            sim.spacecraft.disturbance_torque = np.array([1e-4, 1e-4, 1e-4])
        elif self.config.trigger_fault == 'power_low':
            # Simulated by disabling actuators
            sim.magnetorquers.reset()
    
    def _check_safe_mode_trigger(self, sim: Simulator, state) -> bool:
        """Check if safe mode should be triggered."""
        # High angular rates
        omega_deg_s = np.degrees(np.linalg.norm(state.angular_velocity))
        if omega_deg_s > 5.0:  # Threshold
            return True
        
        return False
    
    def _enter_safe_mode(self, sim: Simulator):
        """Execute safe mode entry."""
        print(f"  SAFE MODE ENTERED at t={sim.time.elapsed_seconds:.1f}s")
        
        # Clear disturbance
        sim.spacecraft.disturbance_torque = np.zeros(3)
    
    def _safe_mode_control(self, sim: Simulator, state):
        """Safe mode attitude control - simple rate damping."""
        # B-dot style control
        b_field = state.mag_field_body_uT * 1e-6
        b_norm = np.linalg.norm(b_field)
        
        if b_norm > 1e-9:
            omega = sim.spacecraft.attitude_state.angular_velocity
            # B-dot approximation: dB/dt ≈ -ω×B (body frame), so m = -k*dB/dt = k*(ω×B)
            # Use |B|^2 scaling to avoid dependency on field magnitude.
            dipole = 1e5 * np.cross(omega, b_field) / (b_norm ** 2)
            dipole = np.clip(dipole, -0.2, 0.2)
            sim.command_magnetorquers(dipole)
    
    def run(self, progress_callback=None) -> Dict:
        """Run safe mode scenario."""
        if self.simulator is None:
            self.setup()
        
        print(f"Running Safe Mode Scenario")
        print(f"  Fault type: {self.config.trigger_fault}")
        print(f"  Fault injection at: {self.config.fault_time_s}s")
        
        history = self.simulator.run(progress_callback=progress_callback)
        self.history = history
        self.results = self._analyze_results(history)
        
        return self.results
    
    def _analyze_results(self, history) -> Dict:
        """Analyze safe mode scenario results."""
        if not history:
            return {'success': False}
        
        # Find safe mode entry time
        safe_mode_time = None
        for state in history:
            omega_deg_s = np.degrees(np.linalg.norm(state.angular_velocity))
            if omega_deg_s > 5.0 and safe_mode_time is None:
                safe_mode_time = state.time_s
                break
        
        # Check final rates
        final_rate = np.degrees(np.linalg.norm(history[-1].angular_velocity))
        
        return {
            'success': final_rate < 1.0,
            'safe_mode_triggered': self.in_safe_mode,
            'safe_mode_time_s': safe_mode_time,
            'final_rate_deg_s': final_rate,
            'fault_type': self.config.trigger_fault,
        }
    
    def get_summary(self) -> str:
        """Get summary."""
        if not self.results:
            return "Scenario not yet run."
        
        status = "SUCCESS ✓" if self.results['success'] else "FAILED ✗"
        
        return f"""
Safe Mode Scenario Summary
==========================
Result: {status}

Fault injected: {self.config.trigger_fault}
Safe mode triggered: {self.results['safe_mode_triggered']}
Safe mode time: {self.results['safe_mode_time_s']}s
Final rate: {self.results['final_rate_deg_s']:.3f} deg/s
"""
