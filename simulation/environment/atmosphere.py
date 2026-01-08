"""
Atmosphere Model
================

Atmospheric density model for drag calculations.
"""

import numpy as np
from typing import Tuple
from dataclasses import dataclass


@dataclass
class AtmosphereLayer:
    """Atmospheric layer parameters."""
    h_base_km: float  # Base altitude [km]
    h_top_km: float   # Top altitude [km]
    rho_base: float   # Base density [kg/m³]
    H: float          # Scale height [km]


class AtmosphereModel:
    """
    Atmospheric density model for LEO.
    
    Uses US Standard Atmosphere 1976 with extensions for higher altitudes.
    """
    
    # Layer definitions (simplified US Standard Atmosphere 1976)
    LAYERS = [
        AtmosphereLayer(0, 25, 1.225, 7.249),
        AtmosphereLayer(25, 100, 3.899e-2, 6.349),
        AtmosphereLayer(100, 200, 5.297e-7, 27.0),
        AtmosphereLayer(200, 350, 2.418e-10, 53.628),
        AtmosphereLayer(350, 500, 9.518e-12, 53.298),
        AtmosphereLayer(500, 750, 3.725e-13, 76.828),
        AtmosphereLayer(750, 1000, 1.585e-14, 99.0),
        AtmosphereLayer(1000, 2000, 3.019e-15, 268.0),
    ]
    
    def __init__(self, 
                 solar_flux_f107: float = 150.0,
                 geomagnetic_index_ap: float = 15.0):
        """
        Initialize atmosphere model.
        
        Args:
            solar_flux_f107: Solar 10.7 cm radio flux [sfu]
            geomagnetic_index_ap: Geomagnetic activity index
        """
        self.f107 = solar_flux_f107
        self.ap = geomagnetic_index_ap
    
    def density(self, altitude_km: float) -> float:
        """
        Calculate atmospheric density.
        
        Args:
            altitude_km: Altitude above Earth surface [km]
            
        Returns:
            Atmospheric density [kg/m³]
        """
        if altitude_km < 0:
            return self.LAYERS[0].rho_base
        
        if altitude_km > 2000:
            # Above 2000 km, essentially vacuum
            return 1e-18
        
        # Find appropriate layer
        for layer in self.LAYERS:
            if layer.h_base_km <= altitude_km < layer.h_top_km:
                # Exponential atmosphere
                dh = altitude_km - layer.h_base_km
                rho = layer.rho_base * np.exp(-dh / layer.H)
                
                # Apply solar activity correction
                rho *= self._solar_correction(altitude_km)
                
                return rho
        
        # Should not reach here
        return 1e-18
    
    def _solar_correction(self, altitude_km: float) -> float:
        """
        Apply solar activity correction to density.
        
        Higher solar activity = higher density at high altitudes.
        """
        if altitude_km < 200:
            return 1.0
        
        # Simplified correction based on F10.7
        # F10.7 = 70-300 sfu range
        f107_ref = 150.0  # Reference value
        
        # Correction factor (can be 0.5 to 2.0)
        correction = 1.0 + (self.f107 - f107_ref) / f107_ref * 0.5
        
        # Effect increases with altitude
        alt_factor = (altitude_km - 200) / 300
        alt_factor = min(alt_factor, 1.0)
        
        return 1.0 + (correction - 1.0) * alt_factor
    
    def set_solar_conditions(self, f107: float, ap: float):
        """Update solar activity parameters."""
        self.f107 = f107
        self.ap = ap
    
    def density_gradient(self, altitude_km: float) -> float:
        """
        Calculate density gradient (d(rho)/dh).
        
        Args:
            altitude_km: Altitude [km]
            
        Returns:
            Density gradient [kg/m³/km]
        """
        h = 1.0  # Numerical differentiation step [km]
        rho_up = self.density(altitude_km + h)
        rho_down = self.density(altitude_km - h)
        
        return (rho_up - rho_down) / (2 * h)
    
    def scale_height(self, altitude_km: float) -> float:
        """
        Get local scale height.
        
        Args:
            altitude_km: Altitude [km]
            
        Returns:
            Scale height [km]
        """
        for layer in self.LAYERS:
            if layer.h_base_km <= altitude_km < layer.h_top_km:
                return layer.H
        
        return 100.0  # Default for very high altitude
