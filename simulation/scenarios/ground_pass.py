"""
Ground Pass Scenario
====================

Ground station communication pass testing.
"""

import numpy as np
from typing import Dict, Optional, List
from dataclasses import dataclass
from ..core.config import SimulationConfig, GroundStationParameters
from ..core.simulator import Simulator
from ..environment.ground_station import GroundStation, GroundStationConfig


@dataclass
class GroundPassScenarioConfig:
    """Configuration for ground pass scenario."""
    duration_orbits: float = 3.0
    ground_station_lat: float = -23.55  # São Paulo
    ground_station_lon: float = -46.63
    min_elevation_deg: float = 10.0


class GroundPassScenario:
    """
    Ground station pass scenario.
    
    Tests:
    - Pass prediction
    - Link budget analysis
    - Data transfer estimation
    """
    
    def __init__(self, config: GroundPassScenarioConfig = None):
        """Initialize ground pass scenario."""
        self.config = config or GroundPassScenarioConfig()
        
        orbital_period = 95 * 60
        self.sim_config = SimulationConfig(
            duration_seconds=orbital_period * self.config.duration_orbits,
            time_step_seconds=1.0,
        )
        
        # Custom ground station
        gs_config = GroundStationConfig(
            latitude_deg=self.config.ground_station_lat,
            longitude_deg=self.config.ground_station_lon,
            min_elevation_deg=self.config.min_elevation_deg,
        )
        
        self.simulator: Optional[Simulator] = None
        self.ground_station = GroundStation(gs_config)
        self.results: Dict = {}
        self.passes: List[Dict] = []
    
    def setup(self):
        """Setup scenario."""
        self.simulator = Simulator(self.sim_config)
        self.simulator.ground_station = self.ground_station
        self.passes.clear()
        
        self._in_pass = False
        self._pass_start = 0.0
        self._max_elevation = 0.0
        
        self.simulator.add_step_callback(self._pass_monitor)
    
    def _pass_monitor(self, sim: Simulator, state):
        """Monitor ground station passes."""
        if state.gs_visible and not self._in_pass:
            # Pass start
            self._in_pass = True
            self._pass_start = state.time_s
            self._max_elevation = state.gs_elevation_deg
            print(f"  Pass start at t={state.time_s:.1f}s")
        
        elif state.gs_visible:
            # During pass
            if state.gs_elevation_deg > self._max_elevation:
                self._max_elevation = state.gs_elevation_deg
        
        elif not state.gs_visible and self._in_pass:
            # Pass end
            self._in_pass = False
            duration = state.time_s - self._pass_start
            
            self.passes.append({
                'start_time_s': self._pass_start,
                'end_time_s': state.time_s,
                'duration_min': duration / 60,
                'max_elevation_deg': self._max_elevation,
            })
            
            print(f"  Pass end: duration={duration/60:.1f}min, max_el={self._max_elevation:.1f}°")
    
    def run(self, progress_callback=None) -> Dict:
        """Run ground pass scenario."""
        if self.simulator is None:
            self.setup()
        
        print(f"Running Ground Pass Scenario: {self.config.duration_orbits} orbits")
        print(f"  Ground station: {self.config.ground_station_lat}°, {self.config.ground_station_lon}°")
        
        history = self.simulator.run(progress_callback=progress_callback)
        self.results = self._analyze_results(history)
        
        return self.results
    
    def _analyze_results(self, history) -> Dict:
        """Analyze ground pass results."""
        if not history:
            return {}
        
        contact_samples = sum(1 for s in history if s.gs_visible)
        total_samples = len(history)
        
        return {
            'num_passes': len(self.passes),
            'contact_fraction': contact_samples / total_samples if total_samples > 0 else 0,
            'total_contact_min': sum(p['duration_min'] for p in self.passes),
            'mean_pass_duration_min': np.mean([p['duration_min'] for p in self.passes]) if self.passes else 0,
            'max_elevation_deg': max([p['max_elevation_deg'] for p in self.passes]) if self.passes else 0,
            'passes': self.passes,
        }
    
    def get_summary(self) -> str:
        """Get summary."""
        if not self.results:
            return "Scenario not yet run."
        
        return f"""
Ground Pass Scenario Summary
============================
Ground Station: {self.config.ground_station_lat}°N, {self.config.ground_station_lon}°E

Pass Statistics:
  Number of passes: {self.results['num_passes']}
  Contact fraction: {self.results['contact_fraction']*100:.1f}%
  Total contact time: {self.results['total_contact_min']:.1f} min
  Mean pass duration: {self.results['mean_pass_duration_min']:.1f} min
  Max elevation: {self.results['max_elevation_deg']:.1f}°
"""
