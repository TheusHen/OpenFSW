"""
GPS Receiver Model
==================

Simplified GPS receiver for position and velocity.
"""

import numpy as np
from typing import Optional, Tuple
from dataclasses import dataclass


@dataclass
class GPSConfig:
    """GPS receiver configuration."""
    # Accuracy (1-sigma)
    position_accuracy_m: float = 10.0  # Position accuracy [m]
    velocity_accuracy_m_s: float = 0.1  # Velocity accuracy [m/s]
    time_accuracy_us: float = 100.0  # Time accuracy [µs]
    
    # Operational
    sample_rate_hz: float = 1.0  # Position update rate
    acquisition_time_s: float = 60.0  # Cold start acquisition time
    
    # Visibility
    min_satellites: int = 4  # Minimum satellites for fix
    max_altitude_km: float = 1000.0  # Maximum operational altitude


class GPSReceiver:
    """
    GPS receiver model for LEO satellites.
    
    Models:
    - Position and velocity errors
    - Signal acquisition
    - Outages (ionosphere, multipath equivalent)
    - Altitude limits
    """
    
    def __init__(self, config: GPSConfig = None):
        """
        Initialize GPS receiver.
        
        Args:
            config: Receiver configuration
        """
        self.config = config or GPSConfig()
        
        # State
        self.has_fix = False
        self.time_since_fix = 0.0
        self.satellites_visible = 8
        self.last_position = np.zeros(3)
        self.last_velocity = np.zeros(3)
        self.is_valid = True
        self.sample_count = 0
    
    def update(self,
               true_position_km: np.ndarray,
               true_velocity_km_s: np.ndarray,
               dt: float,
               add_noise: bool = True) -> Tuple[np.ndarray, np.ndarray, bool]:
        """
        Update GPS measurement.
        
        Args:
            true_position_km: True position in ECEF or ECI [km]
            true_velocity_km_s: True velocity [km/s]
            dt: Time step [s]
            add_noise: Add measurement noise
            
        Returns:
            Tuple of (position_km, velocity_km_s, has_fix)
        """
        if not self.is_valid:
            return np.full(3, np.nan), np.full(3, np.nan), False
        
        # Check altitude constraint
        altitude_km = np.linalg.norm(true_position_km) - 6378.0
        if altitude_km > self.config.max_altitude_km:
            self.has_fix = False
            return np.zeros(3), np.zeros(3), False
        
        # Simulate satellite visibility (simplified)
        # In reality would depend on orbit and GPS constellation
        self.satellites_visible = np.random.poisson(8)
        
        if self.satellites_visible < self.config.min_satellites:
            self.has_fix = False
            self.time_since_fix = 0.0
            return np.zeros(3), np.zeros(3), False
        
        # Acquisition time
        if not self.has_fix:
            self.time_since_fix += dt
            if self.time_since_fix < self.config.acquisition_time_s:
                return np.zeros(3), np.zeros(3), False
            self.has_fix = True
        
        # Add measurement noise
        if add_noise:
            # Position error (convert m to km)
            pos_error = np.random.normal(0, self.config.position_accuracy_m * 1e-3, 3)
            vel_error = np.random.normal(0, self.config.velocity_accuracy_m_s * 1e-3, 3)
            
            position = true_position_km + pos_error
            velocity = true_velocity_km_s + vel_error
        else:
            position = true_position_km.copy()
            velocity = true_velocity_km_s.copy()
        
        self.last_position = position
        self.last_velocity = velocity
        self.sample_count += 1
        
        return position, velocity, True
    
    def get_pdop(self) -> float:
        """
        Get Position Dilution of Precision (simplified).
        
        Returns:
            PDOP value (lower is better, typical 1-3)
        """
        if not self.has_fix:
            return 99.9
        
        # Simplified: inversely related to visible satellites
        return max(1.0, 10.0 / self.satellites_visible)
    
    def inject_fault(self, fault_type: str):
        """Inject receiver fault."""
        if fault_type == 'no_fix':
            self.has_fix = False
            self.time_since_fix = 0.0
        elif fault_type == 'offline':
            self.is_valid = False
        elif fault_type == 'degraded':
            self.config.position_accuracy_m *= 10
            self.config.velocity_accuracy_m_s *= 10
    
    def reset(self):
        """Reset receiver state."""
        self.has_fix = False
        self.time_since_fix = 0.0
        self.satellites_visible = 8
        self.last_position = np.zeros(3)
        self.last_velocity = np.zeros(3)
        self.sample_count = 0
        self.is_valid = True
