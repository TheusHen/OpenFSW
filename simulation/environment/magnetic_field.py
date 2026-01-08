"""
Magnetic Field Model
====================

Earth's magnetic field models for attitude simulation.
"""

import numpy as np
from typing import Tuple
from datetime import datetime


class IGRF:
    """
    Simplified IGRF (International Geomagnetic Reference Field) model.
    
    Uses dipole approximation with secular variation.
    For accurate simulations, use pyIGRF or similar libraries.
    """
    
    # Dipole coefficients (IGRF-13, 2020)
    G10 = -29404.8  # nT
    G11 = -1450.9   # nT
    H11 = 4652.5    # nT
    
    # Secular variation (nT/year)
    DG10 = 5.7
    DG11 = 7.4
    DH11 = -25.9
    
    # Reference epoch
    EPOCH = 2020.0
    
    # Earth parameters
    RE = 6371.2  # km - mean Earth radius for IGRF
    
    def __init__(self, date: datetime = None):
        """
        Initialize IGRF model.
        
        Args:
            date: Date for secular variation (default: current)
        """
        if date is None:
            date = datetime.now()
        
        # Calculate decimal year
        year = date.year + (date.timetuple().tm_yday - 1) / 365.0
        
        # Apply secular variation
        dt = year - self.EPOCH
        self.g10 = self.G10 + self.DG10 * dt
        self.g11 = self.G11 + self.DG11 * dt
        self.h11 = self.H11 + self.DH11 * dt
    
    def field_eci(self, position_km: np.ndarray, gmst_rad: float) -> np.ndarray:
        """
        Calculate magnetic field in ECI frame.
        
        Args:
            position_km: Position in ECI [km]
            gmst_rad: Greenwich Mean Sidereal Time [rad]
            
        Returns:
            Magnetic field in ECI [T]
        """
        # Convert ECI to ECEF (simplified rotation about Z)
        cos_gmst = np.cos(gmst_rad)
        sin_gmst = np.sin(gmst_rad)
        
        R_ecef_eci = np.array([
            [cos_gmst, sin_gmst, 0],
            [-sin_gmst, cos_gmst, 0],
            [0, 0, 1]
        ])
        
        position_ecef = R_ecef_eci @ position_km
        
        # Get field in ECEF
        b_ecef = self.field_ecef(position_ecef)
        
        # Convert back to ECI
        b_eci = R_ecef_eci.T @ b_ecef
        
        return b_eci
    
    def field_ecef(self, position_km: np.ndarray) -> np.ndarray:
        """
        Calculate magnetic field in ECEF frame.
        
        Uses tilted dipole model.
        
        Args:
            position_km: Position in ECEF [km]
            
        Returns:
            Magnetic field in ECEF [T]
        """
        # Convert to geocentric coordinates
        r = np.linalg.norm(position_km)
        
        if r < 1e-6:
            return np.zeros(3)
        
        # Geocentric latitude and longitude
        x, y, z = position_km
        lat = np.arcsin(z / r)
        lon = np.arctan2(y, x)
        
        # Dipole parameters
        # Dipole moment direction (from g10, g11, h11)
        m0 = np.sqrt(self.g10**2 + self.g11**2 + self.h11**2)
        
        # Dipole tilt
        theta_m = np.arccos(-self.g10 / m0)
        phi_m = np.arctan2(self.h11, self.g11)
        
        # Compute dipole field
        # B = (μ₀/4π) * (m/r³) * [3(m·r̂)r̂ - m]
        
        # Dipole moment direction
        m_hat = np.array([
            np.sin(theta_m) * np.cos(phi_m),
            np.sin(theta_m) * np.sin(phi_m),
            np.cos(theta_m)
        ])
        
        # Position unit vector
        r_hat = position_km / r
        
        # Field strength scale
        B0 = m0 * 1e-9 * (self.RE / r)**3  # Convert nT to T and scale
        
        # Dipole field
        m_dot_r = np.dot(m_hat, r_hat)
        B = B0 * (3 * m_dot_r * r_hat - m_hat)
        
        return B
    
    def field_ned(self, lat_deg: float, lon_deg: float, alt_km: float) -> np.ndarray:
        """
        Calculate field in local NED frame.
        
        Args:
            lat_deg: Geodetic latitude [deg]
            lon_deg: Longitude [deg]
            alt_km: Altitude [km]
            
        Returns:
            (B_north, B_east, B_down) in Tesla
        """
        # Convert to geocentric position
        lat = np.radians(lat_deg)
        lon = np.radians(lon_deg)
        r = self.RE + alt_km
        
        position = r * np.array([
            np.cos(lat) * np.cos(lon),
            np.cos(lat) * np.sin(lon),
            np.sin(lat)
        ])
        
        # Get ECEF field
        B_ecef = self.field_ecef(position)
        
        # Transform to NED
        sin_lat, cos_lat = np.sin(lat), np.cos(lat)
        sin_lon, cos_lon = np.sin(lon), np.cos(lon)
        
        R_ned_ecef = np.array([
            [-sin_lat*cos_lon, -sin_lat*sin_lon, cos_lat],
            [-sin_lon, cos_lon, 0],
            [-cos_lat*cos_lon, -cos_lat*sin_lon, -sin_lat]
        ])
        
        B_ned = R_ned_ecef @ B_ecef
        
        return B_ned


class MagneticFieldModel:
    """
    Wrapper for magnetic field calculations.
    
    Provides body-frame magnetic field for attitude control.
    """
    
    def __init__(self, date: datetime = None):
        """
        Initialize magnetic field model.
        
        Args:
            date: Reference date
        """
        self.igrf = IGRF(date)
    
    def get_field_body(self,
                       position_eci: np.ndarray,
                       quaternion: np.ndarray,
                       gmst_rad: float) -> np.ndarray:
        """
        Get magnetic field in body frame.
        
        Args:
            position_eci: Position in ECI [km]
            quaternion: Attitude quaternion [w, x, y, z]
            gmst_rad: GMST [rad]
            
        Returns:
            Magnetic field in body frame [T]
        """
        # Get field in ECI
        B_eci = self.igrf.field_eci(position_eci, gmst_rad)
        
        # Transform to body frame
        R_bi = self._quaternion_to_matrix_inverse(quaternion)
        B_body = R_bi @ B_eci
        
        return B_body
    
    def get_field_body_uT(self,
                          position_eci: np.ndarray,
                          quaternion: np.ndarray,
                          gmst_rad: float) -> np.ndarray:
        """Get magnetic field in body frame [µT]."""
        return self.get_field_body(position_eci, quaternion, gmst_rad) * 1e6
    
    @staticmethod
    def _quaternion_to_matrix_inverse(q: np.ndarray) -> np.ndarray:
        """Convert quaternion to rotation matrix (inertial to body)."""
        w, x, y, z = q
        
        R = np.array([
            [1-2*(y*y+z*z), 2*(x*y-w*z), 2*(x*z+w*y)],
            [2*(x*y+w*z), 1-2*(x*x+z*z), 2*(y*z-w*x)],
            [2*(x*z-w*y), 2*(y*z+w*x), 1-2*(x*x+y*y)]
        ])
        
        return R.T  # Transpose for inertial to body
