"""
Thermal Model
=============

Simplified thermal model for 3U CubeSat.
"""

import numpy as np
from dataclasses import dataclass
from typing import Dict, List


@dataclass
class ThermalNodeConfig:
    """Configuration for a thermal node."""
    name: str
    mass_kg: float
    specific_heat_J_kgK: float = 900.0  # Aluminum
    initial_temp_K: float = 293.0
    absorptivity: float = 0.9
    emissivity: float = 0.9
    area_m2: float = 0.01


@dataclass
class ThermalLimits:
    """Temperature limits for components."""
    battery_min_K: float = 273.0      # 0°C
    battery_max_K: float = 318.0      # 45°C
    electronics_min_K: float = 233.0  # -40°C
    electronics_max_K: float = 358.0  # 85°C


class ThermalModel:
    """
    Simplified lumped-parameter thermal model.
    
    Uses single-node model with radiative and conductive heat transfer.
    """
    
    # Physical constants
    STEFAN_BOLTZMANN = 5.67e-8  # W/(m^2*K^4)
    SOLAR_FLUX = 1361.0  # W/m^2 at 1 AU
    ALBEDO_FLUX = 400.0  # W/m^2 (Earth reflected)
    IR_FLUX = 240.0  # W/m^2 (Earth IR)
    
    def __init__(self, limits: ThermalLimits = None):
        """
        Initialize thermal model.
        
        Args:
            limits: Temperature limits
        """
        self.limits = limits or ThermalLimits()
        
        # Single-node bulk model
        self.temperature_K = 293.0  # Initial temp
        
        # Spacecraft thermal properties
        self.thermal_mass = 4.0 * 900.0  # 4kg * specific heat (J/K)
        self.surface_area = 0.1 * 0.1 * 2 + 0.1 * 0.34 * 4  # m^2
        
        # Surface properties
        self.absorptivity = 0.9
        self.emissivity = 0.9
        
        # Internal dissipation
        self.internal_power = 3.0  # Watts
        
        # History for analysis
        self.temp_history: List[float] = []
        self.time_history: List[float] = []
    
    def update(self, dt: float, solar_illuminated: bool, 
               in_eclipse: bool, altitude_km: float = 500) -> Dict:
        """
        Update thermal state.
        
        Args:
            dt: Time step in seconds
            solar_illuminated: Whether sun is visible
            in_eclipse: Whether in eclipse
            altitude_km: Orbital altitude for view factors
            
        Returns:
            Thermal status dictionary
        """
        # Calculate view factors
        # Simplified: assume half surface sees Earth
        earth_view_factor = 0.5 * (6371.0 / (6371.0 + altitude_km)) ** 2
        
        # Heat inputs
        Q_solar = 0.0
        if not in_eclipse and solar_illuminated:
            # Assume 1/6 surface illuminated (one face)
            Q_solar = self.absorptivity * self.SOLAR_FLUX * self.surface_area / 6
        
        Q_albedo = 0.0
        if not in_eclipse:
            Q_albedo = self.absorptivity * self.ALBEDO_FLUX * \
                       self.surface_area * earth_view_factor
        
        Q_earth_ir = self.absorptivity * self.IR_FLUX * \
                     self.surface_area * earth_view_factor
        
        Q_internal = self.internal_power
        
        # Radiative heat loss to space
        T_space = 3.0  # K (cosmic background)
        Q_radiated = self.emissivity * self.STEFAN_BOLTZMANN * \
                     self.surface_area * (self.temperature_K ** 4 - T_space ** 4)
        
        # Net heat flow
        Q_net = Q_solar + Q_albedo + Q_earth_ir + Q_internal - Q_radiated
        
        # Temperature change
        dT = Q_net * dt / self.thermal_mass
        self.temperature_K += dT
        
        # Record history
        if self.time_history:
            current_time = self.time_history[-1] + dt
        else:
            current_time = dt
        
        self.temp_history.append(self.temperature_K)
        self.time_history.append(current_time)
        
        return {
            'temperature_K': self.temperature_K,
            'temperature_C': self.temperature_K - 273.15,
            'Q_solar_W': Q_solar,
            'Q_albedo_W': Q_albedo,
            'Q_earth_ir_W': Q_earth_ir,
            'Q_internal_W': Q_internal,
            'Q_radiated_W': Q_radiated,
            'Q_net_W': Q_net,
            'in_limits': self.check_limits(),
        }
    
    def set_internal_power(self, power_W: float):
        """Set internal power dissipation."""
        self.internal_power = power_W
    
    def check_limits(self) -> Dict[str, bool]:
        """Check if temperature is within limits."""
        return {
            'battery_ok': (self.limits.battery_min_K <= self.temperature_K <= 
                          self.limits.battery_max_K),
            'electronics_ok': (self.limits.electronics_min_K <= self.temperature_K <= 
                              self.limits.electronics_max_K),
        }
    
    def get_statistics(self) -> Dict:
        """Get thermal statistics."""
        if not self.temp_history:
            return {}
        
        temps = np.array(self.temp_history)
        
        return {
            'current_temp_K': self.temperature_K,
            'current_temp_C': self.temperature_K - 273.15,
            'min_temp_K': np.min(temps),
            'max_temp_K': np.max(temps),
            'mean_temp_K': np.mean(temps),
            'min_temp_C': np.min(temps) - 273.15,
            'max_temp_C': np.max(temps) - 273.15,
            'mean_temp_C': np.mean(temps) - 273.15,
        }
