"""
Magnetometer Sensor Model
=========================

Three-axis magnetometer with realistic noise and bias.
"""

import numpy as np
from typing import Optional
from dataclasses import dataclass


@dataclass
class MagnetometerConfig:
    """Magnetometer configuration parameters."""
    # Noise parameters
    noise_std_uT: float = 0.5  # Standard deviation [µT]
    bias_uT: np.ndarray = None  # Bias vector [µT]
    
    # Scale factors and alignment
    scale_factor: np.ndarray = None  # Per-axis scale factors
    misalignment_deg: float = 0.5  # Maximum misalignment [deg]
    
    # Operational parameters
    sample_rate_hz: float = 10.0
    range_uT: float = 100.0  # Full scale range
    resolution_uT: float = 0.01  # ADC resolution
    
    def __post_init__(self):
        if self.bias_uT is None:
            self.bias_uT = np.zeros(3)
        if self.scale_factor is None:
            self.scale_factor = np.ones(3)


class Magnetometer:
    """
    Three-axis magnetometer sensor model.
    
    Models:
    - Gaussian measurement noise
    - Bias (constant and temperature-dependent)
    - Scale factor errors
    - Axis misalignment
    - Quantization
    """
    
    def __init__(self, config: MagnetometerConfig = None):
        """
        Initialize magnetometer.
        
        Args:
            config: Sensor configuration
        """
        self.config = config or MagnetometerConfig()
        
        # Generate random misalignment matrix
        self._generate_misalignment()
        
        # State
        self.last_reading = np.zeros(3)
        self.is_valid = True
        self.sample_count = 0
    
    def _generate_misalignment(self):
        """Generate small axis misalignment matrix."""
        # Random small angles
        max_angle = np.radians(self.config.misalignment_deg)
        angles = np.random.uniform(-max_angle, max_angle, 3)
        
        # Build rotation matrix (small angle approximation)
        self.misalignment = np.array([
            [1, -angles[2], angles[1]],
            [angles[2], 1, -angles[0]],
            [-angles[1], angles[0], 1]
        ])
    
    def measure(self, 
                b_true: np.ndarray,
                add_noise: bool = True) -> np.ndarray:
        """
        Generate magnetometer measurement.
        
        Args:
            b_true: True magnetic field in body frame [µT]
            add_noise: Whether to add noise (False for perfect sensor)
            
        Returns:
            Measured magnetic field [µT]
        """
        if not self.is_valid:
            return np.full(3, np.nan)
        
        # Apply scale factors
        b = self.config.scale_factor * b_true
        
        # Apply misalignment
        b = self.misalignment @ b
        
        # Add bias
        b = b + self.config.bias_uT
        
        if add_noise:
            # Add Gaussian noise
            noise = np.random.normal(0, self.config.noise_std_uT, 3)
            b = b + noise
        
        # Quantization
        b = np.round(b / self.config.resolution_uT) * self.config.resolution_uT
        
        # Saturation (limit to range)
        b = np.clip(b, -self.config.range_uT, self.config.range_uT)
        
        self.last_reading = b
        self.sample_count += 1
        
        return b
    
    def calibrate(self, 
                  measurements: np.ndarray,
                  references: np.ndarray) -> tuple:
        """
        Estimate calibration parameters from measurement-reference pairs.
        
        Uses simple least-squares ellipsoid fitting.
        
        Args:
            measurements: Nx3 array of measured values
            references: Nx3 array of reference (true) values
            
        Returns:
            Tuple of (bias, scale_factors)
        """
        # Simple bias estimation (assuming scale = 1)
        bias = np.mean(measurements - references, axis=0)
        
        # Simple scale estimation
        corrected = measurements - bias
        scale = np.std(references, axis=0) / np.std(corrected, axis=0)
        
        return bias, scale
    
    def inject_fault(self, fault_type: str):
        """
        Inject sensor fault for testing.
        
        Args:
            fault_type: 'stuck', 'noisy', 'bias', 'offline'
        """
        if fault_type == 'stuck':
            # Sensor reads constant value
            self.measure = lambda b, add_noise=True: self.last_reading
        elif fault_type == 'noisy':
            # Increased noise
            self.config.noise_std_uT *= 10
        elif fault_type == 'bias':
            # Large bias
            self.config.bias_uT += np.array([10.0, 10.0, 10.0])
        elif fault_type == 'offline':
            self.is_valid = False
    
    def reset(self):
        """Reset sensor to initial state."""
        self.last_reading = np.zeros(3)
        self.sample_count = 0
        self.is_valid = True
