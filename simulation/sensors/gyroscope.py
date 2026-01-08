"""
Gyroscope Sensor Model
======================

Three-axis rate gyroscope with bias instability and noise.
"""

import numpy as np
from typing import Optional
from dataclasses import dataclass


@dataclass
class GyroscopeConfig:
    """Gyroscope configuration parameters."""
    # Noise parameters
    arw_deg_s_sqrt_hz: float = 0.003  # Angle Random Walk [deg/s/√Hz]
    bias_instability_deg_s: float = 0.01  # Bias instability [deg/s]
    
    # Initial bias
    bias_deg_s: np.ndarray = None  # Bias [deg/s]
    
    # Scale factor errors
    scale_factor_error_ppm: float = 1000  # Scale factor error [ppm]
    
    # Operational parameters
    sample_rate_hz: float = 100.0
    range_deg_s: float = 300.0  # Full scale range
    resolution_deg_s: float = 0.001  # Resolution
    
    def __post_init__(self):
        if self.bias_deg_s is None:
            # Random initial bias
            self.bias_deg_s = np.random.uniform(-0.1, 0.1, 3)


class Gyroscope:
    """
    Three-axis MEMS gyroscope sensor model.
    
    Models:
    - Angle Random Walk (ARW)
    - Bias instability (random walk)
    - Scale factor errors
    - Quantization
    - Saturation
    """
    
    def __init__(self, config: GyroscopeConfig = None):
        """
        Initialize gyroscope.
        
        Args:
            config: Sensor configuration
        """
        self.config = config or GyroscopeConfig()
        
        # Current bias (evolves with bias instability)
        self.current_bias = self.config.bias_deg_s.copy()
        
        # Scale factors with error
        sf_error = self.config.scale_factor_error_ppm * 1e-6
        self.scale_factors = 1 + np.random.uniform(-sf_error, sf_error, 3)
        
        # State
        self.last_reading = np.zeros(3)
        self.is_valid = True
        self.sample_count = 0
    
    def measure(self,
                omega_true: np.ndarray,
                dt: float = None,
                add_noise: bool = True) -> np.ndarray:
        """
        Generate gyroscope measurement.
        
        Args:
            omega_true: True angular velocity in body frame [rad/s]
            dt: Time since last sample (for bias drift)
            add_noise: Whether to add noise
            
        Returns:
            Measured angular velocity [rad/s]
        """
        if not self.is_valid:
            return np.full(3, np.nan)
        
        # Convert to deg/s for internal processing
        omega_deg = np.degrees(omega_true)
        
        # Apply scale factors
        omega = self.scale_factors * omega_deg
        
        # Add bias
        omega = omega + self.current_bias
        
        if add_noise:
            # ARW noise (white noise on rate)
            # σ_rate = ARW × √(sample_rate)
            noise_std = self.config.arw_deg_s_sqrt_hz * np.sqrt(self.config.sample_rate_hz)
            noise = np.random.normal(0, noise_std, 3)
            omega = omega + noise
            
            # Bias random walk (if dt provided)
            if dt is not None:
                # Bias drift
                bias_noise_std = self.config.bias_instability_deg_s * np.sqrt(dt)
                self.current_bias += np.random.normal(0, bias_noise_std, 3)
        
        # Quantization
        omega = np.round(omega / self.config.resolution_deg_s) * self.config.resolution_deg_s
        
        # Saturation
        omega = np.clip(omega, -self.config.range_deg_s, self.config.range_deg_s)
        
        # Convert back to rad/s
        omega_rad = np.radians(omega)
        
        self.last_reading = omega_rad
        self.sample_count += 1
        
        return omega_rad
    
    def estimate_bias(self,
                      measurements: np.ndarray,
                      reference: np.ndarray = None) -> np.ndarray:
        """
        Estimate bias from static measurements.
        
        Args:
            measurements: Nx3 array of measurements during zero-rate condition
            reference: True rate (default zeros)
            
        Returns:
            Estimated bias [rad/s]
        """
        if reference is None:
            reference = np.zeros(3)
        
        bias_est = np.mean(measurements, axis=0) - reference
        return bias_est
    
    def set_bias(self, bias: np.ndarray):
        """Manually set sensor bias [deg/s]."""
        self.current_bias = bias.copy()
    
    def inject_fault(self, fault_type: str):
        """
        Inject sensor fault.
        
        Args:
            fault_type: 'stuck', 'noisy', 'drift', 'offline'
        """
        if fault_type == 'stuck':
            self.measure = lambda omega, dt=None, add_noise=True: self.last_reading
        elif fault_type == 'noisy':
            self.config.arw_deg_s_sqrt_hz *= 10
        elif fault_type == 'drift':
            self.config.bias_instability_deg_s *= 100
        elif fault_type == 'offline':
            self.is_valid = False
    
    def reset(self):
        """Reset sensor state."""
        self.current_bias = self.config.bias_deg_s.copy()
        self.last_reading = np.zeros(3)
        self.sample_count = 0
        self.is_valid = True


class RateIntegratingGyro:
    """
    Rate-integrating gyroscope for attitude estimation.
    
    Integrates rate measurements to estimate attitude change.
    Susceptible to drift over time.
    """
    
    def __init__(self, gyro: Gyroscope):
        """
        Initialize with base gyroscope.
        
        Args:
            gyro: Gyroscope sensor model
        """
        self.gyro = gyro
        self.integrated_angle = np.zeros(3)  # Euler angles [rad]
    
    def update(self, omega_true: np.ndarray, dt: float) -> np.ndarray:
        """
        Update integrated angle.
        
        Args:
            omega_true: True angular velocity [rad/s]
            dt: Time step [s]
            
        Returns:
            Integrated Euler angles [rad]
        """
        omega_meas = self.gyro.measure(omega_true, dt)
        self.integrated_angle += omega_meas * dt
        return self.integrated_angle
    
    def reset(self, initial_angle: np.ndarray = None):
        """Reset integrated angle."""
        self.integrated_angle = initial_angle if initial_angle is not None else np.zeros(3)
        self.gyro.reset()
