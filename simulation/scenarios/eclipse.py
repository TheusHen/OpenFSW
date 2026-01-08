"""
Eclipse Scenario
================

Eclipse transition testing.
"""

import numpy as np
from typing import Dict, Optional, List
from dataclasses import dataclass
from ..core.config import SimulationConfig
from ..core.simulator import Simulator


@dataclass
class EclipseScenarioConfig:
    """Configuration for eclipse scenario."""
    duration_orbits: float = 2.0
    track_power: bool = True


class EclipseScenario:
    """
    Eclipse transition scenario.
    
    Tests:
    - Eclipse entry/exit detection
    - Power management during eclipse
    - Thermal effects
    - Attitude maintenance without sun reference
    """
    
    def __init__(self, config: EclipseScenarioConfig = None):
        """Initialize eclipse scenario."""
        self.config = config or EclipseScenarioConfig()
        
        orbital_period = 95 * 60
        self.sim_config = SimulationConfig(
            duration_seconds=orbital_period * self.config.duration_orbits,
            time_step_seconds=0.5,  # Longer step for longer scenario
        )
        
        self.simulator: Optional[Simulator] = None
        self.results: Dict = {}
        self.eclipse_events: List[Dict] = []
        self.history: List = []
    
    def setup(self):
        """Setup scenario."""
        self.simulator = Simulator(self.sim_config)
        self.eclipse_events.clear()
        self._last_eclipse_state = False
        
        self.simulator.add_step_callback(self._eclipse_monitor)
    
    def _eclipse_monitor(self, sim: Simulator, state):
        """Monitor eclipse transitions."""
        if state.in_eclipse != self._last_eclipse_state:
            event_type = 'entry' if state.in_eclipse else 'exit'
            self.eclipse_events.append({
                'type': event_type,
                'time_s': state.time_s,
                'altitude_km': state.altitude_km,
            })
            print(f"  Eclipse {event_type} at t={state.time_s:.1f}s")
        
        self._last_eclipse_state = state.in_eclipse
    
    def run(self, progress_callback=None) -> Dict:
        """Run eclipse scenario."""
        if self.simulator is None:
            self.setup()
        
        print(f"Running Eclipse Scenario: {self.config.duration_orbits} orbits")
        
        history = self.simulator.run(progress_callback=progress_callback)
        self.history = history
        self.results = self._analyze_results(history)
        
        return self.results
    
    def _analyze_results(self, history) -> Dict:
        """Analyze eclipse scenario."""
        if not history:
            return {}
        
        # Calculate eclipse statistics
        eclipse_samples = sum(1 for s in history if s.in_eclipse)
        total_samples = len(history)
        
        # Calculate eclipse durations
        eclipse_durations = []
        if len(self.eclipse_events) >= 2:
            for i in range(0, len(self.eclipse_events) - 1, 2):
                if i + 1 < len(self.eclipse_events):
                    entry = self.eclipse_events[i]
                    exit_event = self.eclipse_events[i + 1]
                    if entry['type'] == 'entry' and exit_event['type'] == 'exit':
                        duration = exit_event['time_s'] - entry['time_s']
                        eclipse_durations.append(duration)
        
        return {
            'num_eclipses': len(eclipse_durations),
            'eclipse_fraction': eclipse_samples / total_samples if total_samples > 0 else 0,
            'eclipse_durations_min': [d/60 for d in eclipse_durations],
            'mean_eclipse_duration_min': np.mean(eclipse_durations)/60 if eclipse_durations else 0,
            'total_duration_s': history[-1].time_s,
            'eclipse_events': self.eclipse_events,
        }
    
    def get_summary(self) -> str:
        """Get summary."""
        if not self.results:
            return "Scenario not yet run."
        
        return f"""
Eclipse Scenario Summary
========================
Duration: {self.results['total_duration_s']/60:.1f} min

Eclipse Statistics:
  Number of eclipses: {self.results['num_eclipses']}
  Eclipse fraction: {self.results['eclipse_fraction']*100:.1f}%
  Mean eclipse duration: {self.results['mean_eclipse_duration_min']:.1f} min

Events: {len(self.results['eclipse_events'])}
"""
