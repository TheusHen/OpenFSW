"""
Eclipse Model
=============

Earth shadow modeling for LEO satellites.
"""

import numpy as np
from typing import Tuple
from enum import Enum


class EclipseType(Enum):
    """Eclipse type enumeration."""
    SUNLIT = 0
    PENUMBRA = 1
    UMBRA = 2


class EclipseModel:
    """
    Eclipse calculation for Earth shadow.
    
    Supports:
    - Cylindrical shadow model (simple)
    - Conical shadow model (accurate)
    - Penumbra calculation
    """
    
    # Earth radius [km]
    RE = 6378.137
    
    # Sun radius [km]
    RS = 696000.0
    
    # AU in km
    AU = 149597870.7
    
    def __init__(self, model: str = 'conical'):
        """
        Initialize eclipse model.
        
        Args:
            model: 'cylindrical' or 'conical'
        """
        self.model = model
    
    def check_eclipse(self,
                      sat_pos_eci: np.ndarray,
                      sun_pos_eci: np.ndarray) -> Tuple[EclipseType, float]:
        """
        Check if satellite is in eclipse.
        
        Args:
            sat_pos_eci: Satellite position in ECI [km]
            sun_pos_eci: Sun position in ECI [km]
            
        Returns:
            Tuple of (eclipse_type, illumination_fraction)
        """
        if self.model == 'cylindrical':
            return self._cylindrical_eclipse(sat_pos_eci, sun_pos_eci)
        else:
            return self._conical_eclipse(sat_pos_eci, sun_pos_eci)
    
    def _cylindrical_eclipse(self,
                             sat_pos: np.ndarray,
                             sun_pos: np.ndarray) -> Tuple[EclipseType, float]:
        """
        Simple cylindrical shadow model.
        
        Assumes Earth casts a cylinder-shaped shadow.
        """
        # Sun direction
        sun_dir = sun_pos / np.linalg.norm(sun_pos)
        
        # Project satellite position onto sun direction
        proj = np.dot(sat_pos, sun_dir) * sun_dir
        
        # Perpendicular distance from sun-Earth line
        perp = sat_pos - proj
        perp_dist = np.linalg.norm(perp)
        
        # Check if on shadow side (away from sun)
        if np.dot(sat_pos, sun_dir) > 0:
            # Sunlit side
            return EclipseType.SUNLIT, 1.0
        
        # Check if within shadow cylinder
        if perp_dist < self.RE:
            return EclipseType.UMBRA, 0.0
        else:
            return EclipseType.SUNLIT, 1.0
    
    def _conical_eclipse(self,
                         sat_pos: np.ndarray,
                         sun_pos: np.ndarray) -> Tuple[EclipseType, float]:
        """
        Conical shadow model with penumbra.
        
        More accurate model accounting for sun's finite size.
        """
        # Position magnitudes
        r_sat = np.linalg.norm(sat_pos)
        r_sun = np.linalg.norm(sun_pos)
        
        # Umbra and penumbra cone parameters
        # Half-angle of umbra cone
        alpha_umbra = np.arcsin((self.RS - self.RE) / r_sun)
        # Half-angle of penumbra cone
        alpha_penumbra = np.arcsin((self.RS + self.RE) / r_sun)
        
        # Umbra cone apex distance from Earth center
        x_umbra = self.RE / np.sin(alpha_umbra)
        
        # Sun direction (unit vector)
        sun_dir = sun_pos / r_sun
        
        # Satellite position in shadow frame
        # x: along Earth-Sun line (positive toward sun)
        # y: perpendicular
        x_sat = -np.dot(sat_pos, sun_dir)  # Negative = toward sun
        
        # If satellite is on sunward side of Earth, it's sunlit
        if x_sat < 0:
            return EclipseType.SUNLIT, 1.0
        
        # Perpendicular distance from shadow axis
        proj = np.dot(sat_pos, sun_dir) * sun_dir
        y_sat = np.linalg.norm(sat_pos - proj)
        
        # Check against umbra cone
        umbra_radius = self.RE - x_sat * np.tan(alpha_umbra)
        if y_sat < umbra_radius and umbra_radius > 0:
            return EclipseType.UMBRA, 0.0
        
        # Check against penumbra cone
        penumbra_radius = self.RE + x_sat * np.tan(alpha_penumbra)
        if y_sat < penumbra_radius:
            # In penumbra - calculate illumination fraction
            # Linear interpolation between umbra and penumbra
            if umbra_radius > 0:
                fraction = (y_sat - umbra_radius) / (penumbra_radius - umbra_radius)
            else:
                fraction = y_sat / penumbra_radius
            return EclipseType.PENUMBRA, min(1.0, fraction)
        
        return EclipseType.SUNLIT, 1.0
    
    def in_eclipse(self,
                   sat_pos_eci: np.ndarray,
                   sun_pos_eci: np.ndarray) -> bool:
        """
        Simple boolean eclipse check.
        
        Returns True if in umbra or penumbra.
        """
        eclipse_type, _ = self.check_eclipse(sat_pos_eci, sun_pos_eci)
        return eclipse_type != EclipseType.SUNLIT
    
    def eclipse_fraction(self,
                         sat_pos_eci: np.ndarray,
                         sun_pos_eci: np.ndarray) -> float:
        """
        Get fraction of sun visible (0 = full eclipse, 1 = full sun).
        """
        _, fraction = self.check_eclipse(sat_pos_eci, sun_pos_eci)
        return fraction
    
    def eclipse_entry_exit(self,
                           orbit_positions: np.ndarray,
                           sun_positions: np.ndarray) -> list:
        """
        Find eclipse entry and exit points in an orbit.
        
        Args:
            orbit_positions: Nx3 array of satellite positions [km]
            sun_positions: Nx3 array of sun positions [km]
            
        Returns:
            List of (entry_index, exit_index) tuples
        """
        eclipses = []
        in_eclipse = False
        entry_idx = 0
        
        for i in range(len(orbit_positions)):
            currently_eclipsed = self.in_eclipse(orbit_positions[i], sun_positions[i])
            
            if currently_eclipsed and not in_eclipse:
                # Eclipse entry
                entry_idx = i
                in_eclipse = True
            elif not currently_eclipsed and in_eclipse:
                # Eclipse exit
                eclipses.append((entry_idx, i))
                in_eclipse = False
        
        # Handle case where orbit ends in eclipse
        if in_eclipse:
            eclipses.append((entry_idx, len(orbit_positions) - 1))
        
        return eclipses
