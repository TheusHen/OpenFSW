"""
Sun Model
=========

Sun position and solar radiation for space simulation.
"""

import numpy as np
from datetime import datetime
from typing import Tuple


class SunModel:
    """
    Sun position model for attitude determination.
    
    Provides:
    - Sun position in ECI frame
    - Sun direction in body frame
    - Solar constant and radiation pressure
    """
    
    # Astronomical unit in km
    AU_KM = 149597870.7
    
    # Solar constant at 1 AU [W/m²]
    SOLAR_CONSTANT = 1361.0
    
    # Speed of light [m/s]
    C = 299792458.0
    
    def __init__(self):
        """Initialize sun model."""
        pass
    
    def position_eci(self, julian_date: float) -> np.ndarray:
        """
        Calculate sun position in ECI frame.
        
        Uses low-precision solar position algorithm.
        
        Args:
            julian_date: Julian date
            
        Returns:
            Sun position in ECI [km]
        """
        # Julian centuries since J2000
        T = (julian_date - 2451545.0) / 36525.0
        
        # Mean longitude of the Sun (deg)
        L0 = 280.46646 + 36000.76983 * T + 0.0003032 * T**2
        L0 = L0 % 360
        
        # Mean anomaly of the Sun (deg)
        M = 357.52911 + 35999.05029 * T - 0.0001537 * T**2
        M_rad = np.radians(M % 360)
        
        # Eccentricity of Earth's orbit
        e = 0.016708634 - 0.000042037 * T - 0.0000001267 * T**2
        
        # Sun's equation of center (deg)
        C = ((1.914602 - 0.004817 * T - 0.000014 * T**2) * np.sin(M_rad) +
             (0.019993 - 0.000101 * T) * np.sin(2 * M_rad) +
             0.000289 * np.sin(3 * M_rad))
        
        # Sun's true longitude (deg)
        true_lon = L0 + C
        true_lon_rad = np.radians(true_lon)
        
        # Sun's true anomaly (deg)
        true_anom = M + C
        true_anom_rad = np.radians(true_anom)
        
        # Distance to sun (AU)
        R = 1.000001018 * (1 - e**2) / (1 + e * np.cos(true_anom_rad))
        
        # Obliquity of the ecliptic (deg)
        epsilon = 23.439291 - 0.0130042 * T
        epsilon_rad = np.radians(epsilon)
        
        # Sun position in ECI (equatorial coordinates)
        x = R * np.cos(true_lon_rad) * self.AU_KM
        y = R * np.sin(true_lon_rad) * np.cos(epsilon_rad) * self.AU_KM
        z = R * np.sin(true_lon_rad) * np.sin(epsilon_rad) * self.AU_KM
        
        return np.array([x, y, z])
    
    def direction_eci(self, julian_date: float) -> np.ndarray:
        """
        Get sun direction unit vector in ECI.
        
        Args:
            julian_date: Julian date
            
        Returns:
            Unit vector towards sun
        """
        pos = self.position_eci(julian_date)
        return pos / np.linalg.norm(pos)
    
    def direction_body(self, 
                       julian_date: float,
                       quaternion: np.ndarray) -> np.ndarray:
        """
        Get sun direction in body frame.
        
        Args:
            julian_date: Julian date
            quaternion: Attitude quaternion [w, x, y, z]
            
        Returns:
            Unit vector towards sun in body frame
        """
        sun_eci = self.direction_eci(julian_date)
        
        # Transform to body frame
        R_bi = self._quaternion_to_matrix_inverse(quaternion)
        sun_body = R_bi @ sun_eci
        
        return sun_body
    
    def solar_flux(self, distance_km: float = AU_KM) -> float:
        """
        Calculate solar flux at given distance.
        
        Args:
            distance_km: Distance from sun [km]
            
        Returns:
            Solar flux [W/m²]
        """
        return self.SOLAR_CONSTANT * (self.AU_KM / distance_km)**2
    
    def radiation_pressure(self, 
                           distance_km: float = AU_KM,
                           reflectivity: float = 0.3) -> float:
        """
        Calculate solar radiation pressure.
        
        Args:
            distance_km: Distance from sun [km]
            reflectivity: Surface reflectivity (0-1)
            
        Returns:
            Radiation pressure [Pa]
        """
        flux = self.solar_flux(distance_km)
        # P = (1 + ρ) * F / c
        return (1 + reflectivity) * flux / self.C
    
    def solar_panel_power(self,
                          sun_direction_body: np.ndarray,
                          panel_normal_body: np.ndarray,
                          panel_area_m2: float,
                          efficiency: float = 0.28,
                          in_eclipse: bool = False) -> float:
        """
        Calculate solar panel power output.
        
        Args:
            sun_direction_body: Sun direction in body frame
            panel_normal_body: Panel normal in body frame
            panel_area_m2: Panel area [m²]
            efficiency: Solar cell efficiency (0-1)
            in_eclipse: Eclipse flag
            
        Returns:
            Power output [W]
        """
        if in_eclipse:
            return 0.0
        
        # Cosine of incidence angle
        cos_incidence = np.dot(sun_direction_body, panel_normal_body)
        
        if cos_incidence <= 0:
            return 0.0
        
        return self.SOLAR_CONSTANT * panel_area_m2 * efficiency * cos_incidence
    
    @staticmethod
    def _quaternion_to_matrix_inverse(q: np.ndarray) -> np.ndarray:
        """Convert quaternion to rotation matrix (inertial to body)."""
        w, x, y, z = q
        
        R = np.array([
            [1-2*(y*y+z*z), 2*(x*y-w*z), 2*(x*z+w*y)],
            [2*(x*y+w*z), 1-2*(x*x+z*z), 2*(y*z-w*x)],
            [2*(x*z-w*y), 2*(y*z+w*x), 1-2*(x*x+y*y)]
        ])
        
        return R.T
