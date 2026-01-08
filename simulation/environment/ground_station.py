"""
Ground Station Model
====================

Ground station visibility and communication windows.
"""

import numpy as np
from typing import Tuple, List, Optional
from dataclasses import dataclass
from datetime import datetime, timedelta


@dataclass
class GroundStationConfig:
    """Ground station configuration."""
    name: str = "OpenFSW-GS"
    latitude_deg: float = -23.55  # São Paulo, Brazil
    longitude_deg: float = -46.63
    altitude_m: float = 760.0
    min_elevation_deg: float = 10.0  # Minimum elevation for contact
    
    # Communication parameters
    antenna_gain_dBi: float = 12.0
    system_noise_temp_K: float = 300.0
    data_rate_bps: float = 9600.0


class GroundStation:
    """
    Ground station for communication link analysis.
    
    Features:
    - Visibility window calculation
    - Link budget analysis
    - Pass prediction
    """
    
    # Earth parameters
    RE = 6378.137  # km
    OMEGA_EARTH = 7.2921159e-5  # rad/s
    
    def __init__(self, config: GroundStationConfig = None):
        """
        Initialize ground station.
        
        Args:
            config: Station configuration
        """
        self.config = config or GroundStationConfig()
        
        # Calculate ECEF position
        self._calculate_ecef_position()
    
    def _calculate_ecef_position(self):
        """Calculate station position in ECEF."""
        lat = np.radians(self.config.latitude_deg)
        lon = np.radians(self.config.longitude_deg)
        h = self.config.altitude_m / 1000  # Convert to km
        
        # Simplified spherical Earth
        r = self.RE + h
        
        self.position_ecef = r * np.array([
            np.cos(lat) * np.cos(lon),
            np.cos(lat) * np.sin(lon),
            np.sin(lat)
        ])
    
    def position_eci(self, gmst_rad: float) -> np.ndarray:
        """
        Get station position in ECI frame.
        
        Args:
            gmst_rad: Greenwich Mean Sidereal Time [rad]
            
        Returns:
            Position in ECI [km]
        """
        # Rotate from ECEF to ECI
        cos_gmst = np.cos(gmst_rad)
        sin_gmst = np.sin(gmst_rad)
        
        R = np.array([
            [cos_gmst, -sin_gmst, 0],
            [sin_gmst, cos_gmst, 0],
            [0, 0, 1]
        ])
        
        return R @ self.position_ecef
    
    def elevation_azimuth(self,
                          sat_pos_eci: np.ndarray,
                          gmst_rad: float) -> Tuple[float, float]:
        """
        Calculate satellite elevation and azimuth from ground station.
        
        Args:
            sat_pos_eci: Satellite position in ECI [km]
            gmst_rad: GMST [rad]
            
        Returns:
            Tuple of (elevation_deg, azimuth_deg)
        """
        # Station position in ECI
        gs_pos = self.position_eci(gmst_rad)
        
        # Vector from station to satellite
        range_vec = sat_pos_eci - gs_pos
        range_mag = np.linalg.norm(range_vec)
        
        if range_mag < 1e-6:
            return 90.0, 0.0
        
        # Convert to local ENU (East-North-Up) frame
        lat = np.radians(self.config.latitude_deg)
        lon = np.radians(self.config.longitude_deg) + gmst_rad  # Adjusted for Earth rotation
        
        # Rotation matrix to ENU
        sin_lat, cos_lat = np.sin(lat), np.cos(lat)
        sin_lon, cos_lon = np.sin(lon), np.cos(lon)
        
        R_enu = np.array([
            [-sin_lon, cos_lon, 0],
            [-sin_lat*cos_lon, -sin_lat*sin_lon, cos_lat],
            [cos_lat*cos_lon, cos_lat*sin_lon, sin_lat]
        ])
        
        range_enu = R_enu @ range_vec
        
        # Elevation (angle above horizon)
        elevation = np.arcsin(range_enu[2] / range_mag)
        
        # Azimuth (angle from north, clockwise)
        azimuth = np.arctan2(range_enu[0], range_enu[1])
        if azimuth < 0:
            azimuth += 2 * np.pi
        
        return np.degrees(elevation), np.degrees(azimuth)
    
    def is_visible(self,
                   sat_pos_eci: np.ndarray,
                   gmst_rad: float) -> bool:
        """
        Check if satellite is visible from ground station.
        
        Args:
            sat_pos_eci: Satellite position in ECI [km]
            gmst_rad: GMST [rad]
            
        Returns:
            True if satellite is above minimum elevation
        """
        elevation, _ = self.elevation_azimuth(sat_pos_eci, gmst_rad)
        return elevation >= self.config.min_elevation_deg
    
    def slant_range(self,
                    sat_pos_eci: np.ndarray,
                    gmst_rad: float) -> float:
        """
        Calculate slant range to satellite.
        
        Args:
            sat_pos_eci: Satellite position in ECI [km]
            gmst_rad: GMST [rad]
            
        Returns:
            Slant range [km]
        """
        gs_pos = self.position_eci(gmst_rad)
        return np.linalg.norm(sat_pos_eci - gs_pos)
    
    def find_passes(self,
                    satellite_positions: np.ndarray,
                    times_seconds: np.ndarray,
                    gmst_values: np.ndarray) -> List[dict]:
        """
        Find all ground station passes in trajectory.
        
        Args:
            satellite_positions: Nx3 array of positions [km]
            times_seconds: N-element array of elapsed times [s]
            gmst_values: N-element array of GMST values [rad]
            
        Returns:
            List of pass dictionaries
        """
        passes = []
        in_pass = False
        pass_start = 0
        max_elevation = 0.0
        max_el_time = 0.0
        
        for i in range(len(satellite_positions)):
            visible = self.is_visible(satellite_positions[i], gmst_values[i])
            
            if visible and not in_pass:
                # Pass start
                in_pass = True
                pass_start = i
                max_elevation = 0.0
            
            if visible:
                el, az = self.elevation_azimuth(satellite_positions[i], gmst_values[i])
                if el > max_elevation:
                    max_elevation = el
                    max_el_time = times_seconds[i]
            
            if not visible and in_pass:
                # Pass end
                passes.append({
                    'start_time': times_seconds[pass_start],
                    'end_time': times_seconds[i-1],
                    'duration': times_seconds[i-1] - times_seconds[pass_start],
                    'max_elevation': max_elevation,
                    'max_elevation_time': max_el_time,
                })
                in_pass = False
        
        # Handle pass that ends at trajectory end
        if in_pass:
            passes.append({
                'start_time': times_seconds[pass_start],
                'end_time': times_seconds[-1],
                'duration': times_seconds[-1] - times_seconds[pass_start],
                'max_elevation': max_elevation,
                'max_elevation_time': max_el_time,
            })
        
        return passes
    
    def link_margin_dB(self,
                       slant_range_km: float,
                       sat_tx_power_dBm: float = 30.0,
                       sat_antenna_gain_dBi: float = 0.0,
                       frequency_mhz: float = 437.0,
                       required_snr_dB: float = 10.0) -> float:
        """
        Calculate link margin for downlink.
        
        Args:
            slant_range_km: Range to satellite [km]
            sat_tx_power_dBm: Satellite transmit power [dBm]
            sat_antenna_gain_dBi: Satellite antenna gain [dBi]
            frequency_mhz: Carrier frequency [MHz]
            required_snr_dB: Required SNR [dB]
            
        Returns:
            Link margin [dB]
        """
        # Free space path loss
        fspl = 20 * np.log10(slant_range_km * 1000) + \
               20 * np.log10(frequency_mhz * 1e6) - 147.55
        
        # Received power
        rx_power = sat_tx_power_dBm + sat_antenna_gain_dBi + \
                   self.config.antenna_gain_dBi - fspl
        
        # Noise power (dBm)
        bandwidth_hz = self.config.data_rate_bps * 2  # Simplified
        k = 1.38e-23  # Boltzmann constant
        noise_power = 10 * np.log10(k * self.config.system_noise_temp_K * \
                                     bandwidth_hz * 1000)
        
        # SNR
        snr = rx_power - noise_power
        
        # Link margin
        margin = snr - required_snr_dB
        
        return margin
