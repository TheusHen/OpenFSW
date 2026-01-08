"""
Detumble Scenario
=================

Post-deployment detumbling using B-dot control.
"""

import numpy as np
from typing import Dict, Optional, List
from dataclasses import dataclass
from ..core.config import SimulationConfig
from ..core.simulator import Simulator
from ..dynamics.attitude import DetumbleController


@dataclass
class DetumbleScenarioConfig:
    """Configuration for detumble scenario."""
    max_duration_hours: float = 2.0
    initial_rate_deg_s: float = 10.0  # Maximum initial tumble rate
    target_rate_deg_s: float = 0.5    # Target rate for success
    bdot_gain: float = 1e6            # B-dot controller gain
    max_dipole_Am2: float = 0.2       # Maximum magnetorquer dipole


class DetumbleScenario:
    """
    Post-deployment detumbling scenario.
    
    Simulates:
    - Random initial tumbling
    - B-dot magnetic control
    - Rate convergence to target
    
    Success criteria:
    - Angular rate below target within time limit
    """
    
    def __init__(self, config: DetumbleScenarioConfig = None):
        """
        Initialize detumble scenario.
        
        Args:
            config: Scenario configuration
        """
        self.config = config or DetumbleScenarioConfig()
        
        # Create simulation config
        self.sim_config = SimulationConfig(
            duration_seconds=self.config.max_duration_hours * 3600,
            time_step_seconds=0.1,
        )
        
        self.simulator: Optional[Simulator] = None
        self.controller = DetumbleController(gain=self.config.bdot_gain)
        self.results: Dict = {}
        
        # Track rate history for analysis
        self.rate_history: List[float] = []
        self.time_history: List[float] = []
    
    def setup(self):
        """Setup scenario with tumbling initial conditions."""
        self.simulator = Simulator(self.sim_config)
        
        # Set random tumbling initial conditions
        self.simulator.set_detumble_initial_conditions(
            max_rate_deg_s=self.config.initial_rate_deg_s
        )
        
        # Reset controller
        self.controller.reset()
        self.rate_history.clear()
        self.time_history.clear()
        
        # Add B-dot controller
        self.simulator.add_step_callback(self._bdot_controller)
    
    def _bdot_controller(self, sim: Simulator, state):
        """B-dot detumble controller."""
        # Get magnetic field in body frame
        b_field = state.mag_field_body_uT * 1e-6  # Convert to T
        
        # Compute B-dot dipole command
        dt = sim.config.time_step_seconds
        dipole = self.controller.compute_dipole(b_field, dt)
        
        # Limit dipole
        dipole = np.clip(dipole, -self.config.max_dipole_Am2, 
                         self.config.max_dipole_Am2)
        
        # Command magnetorquers
        sim.command_magnetorquers(dipole)
        
        # Record rate for analysis
        omega_deg_s = np.degrees(np.linalg.norm(state.angular_velocity))
        self.rate_history.append(omega_deg_s)
        self.time_history.append(state.time_s)
    
    def run(self, progress_callback=None) -> Dict:
        """
        Run detumble scenario.
        
        Returns:
            Results dictionary with success/failure and metrics
        """
        if self.simulator is None:
            self.setup()
        
        print(f"Running Detumble Scenario: max {self.config.max_duration_hours} hours")
        print(f"  Initial rate: up to {self.config.initial_rate_deg_s} deg/s")
        print(f"  Target rate: {self.config.target_rate_deg_s} deg/s")
        
        # Run simulation with early termination check
        detumble_time = None
        
        while self.simulator.time.elapsed_seconds < self.sim_config.duration_seconds:
            state = self.simulator.step()
            
            omega_deg_s = np.degrees(np.linalg.norm(state.angular_velocity))
            
            # Check for successful detumble
            if omega_deg_s < self.config.target_rate_deg_s:
                if detumble_time is None:
                    detumble_time = state.time_s
                    print(f"  Target rate reached at t={detumble_time:.1f}s")
                    
                    # Continue for a bit to confirm stability
                    continue
            else:
                detumble_time = None
            
            # Progress update
            if progress_callback and self.simulator.step_count % 1000 == 0:
                progress = self.simulator.time.elapsed_seconds / self.sim_config.duration_seconds
                progress_callback(progress)
        
        # Analyze results
        self.results = self._analyze_results()
        
        return self.results
    
    def _analyze_results(self) -> Dict:
        """Analyze detumble performance."""
        if not self.rate_history:
            return {'success': False, 'reason': 'No data'}
        
        final_rate = self.rate_history[-1]
        initial_rate = self.rate_history[0]
        
        success = final_rate < self.config.target_rate_deg_s
        
        # Find time to reach target (if ever)
        time_to_target = None
        for i, rate in enumerate(self.rate_history):
            if rate < self.config.target_rate_deg_s:
                time_to_target = self.time_history[i]
                break
        
        # Calculate rate reduction rate
        if len(self.rate_history) > 1:
            # Use linear fit to estimate convergence rate
            times = np.array(self.time_history)
            rates = np.array(self.rate_history)
            
            # Exponential fit: rate = A * exp(-t/tau)
            # ln(rate) = ln(A) - t/tau
            log_rates = np.log(np.maximum(rates, 0.001))
            coeffs = np.polyfit(times, log_rates, 1)
            tau = -1.0 / coeffs[0] if abs(coeffs[0]) > 1e-10 else float('inf')
        else:
            tau = float('inf')
        
        return {
            'success': success,
            'initial_rate_deg_s': initial_rate,
            'final_rate_deg_s': final_rate,
            'rate_reduction_percent': (1 - final_rate/initial_rate) * 100 if initial_rate > 0 else 0,
            'time_to_target_s': time_to_target,
            'time_to_target_min': time_to_target / 60 if time_to_target else None,
            'time_constant_s': tau,
            'total_duration_s': self.time_history[-1] if self.time_history else 0,
        }
    
    def get_summary(self) -> str:
        """Get human-readable summary."""
        if not self.results:
            return "Scenario not yet run."
        
        status = "SUCCESS ✓" if self.results['success'] else "FAILED ✗"
        
        time_str = f"{self.results['time_to_target_min']:.1f} min" \
                   if self.results['time_to_target_min'] else "N/A"
        
        return f"""
Detumble Scenario Summary
=========================
Result: {status}

Initial rate: {self.results['initial_rate_deg_s']:.2f} deg/s
Final rate: {self.results['final_rate_deg_s']:.3f} deg/s
Rate reduction: {self.results['rate_reduction_percent']:.1f}%

Time to target: {time_str}
Time constant: {self.results['time_constant_s']:.1f} s
Total duration: {self.results['total_duration_s']/60:.1f} min
"""
    
    def plot_results(self):
        """Plot detumble results (requires matplotlib)."""
        try:
            import matplotlib.pyplot as plt
            
            fig, ax = plt.subplots(figsize=(10, 6))
            
            ax.semilogy(np.array(self.time_history)/60, self.rate_history)
            ax.axhline(y=self.config.target_rate_deg_s, color='r', 
                       linestyle='--', label=f'Target: {self.config.target_rate_deg_s} deg/s')
            
            ax.set_xlabel('Time (minutes)')
            ax.set_ylabel('Angular Rate (deg/s)')
            ax.set_title('B-dot Detumble Performance')
            ax.legend()
            ax.grid(True)
            
            plt.tight_layout()
            return fig
            
        except ImportError:
            print("matplotlib not available for plotting")
            return None
