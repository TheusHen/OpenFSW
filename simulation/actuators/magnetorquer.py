"""
Magnetorquer Model
==================

Magnetic torque rods for attitude control.
"""

import numpy as np
from typing import Optional, List, Tuple
from dataclasses import dataclass


@dataclass
class MagnetorquerConfig:
    """Magnetorquer configuration."""
    # Performance
    max_dipole_Am2: float = 0.2  # Maximum magnetic dipole [Am²]
    residual_dipole_Am2: float = 0.001  # Residual when off [Am²]
    
    # Dynamics
    rise_time_ms: float = 50.0  # Time constant for PWM response
    power_W: float = 0.5  # Power consumption at max dipole
    
    # Axis
    axis_body: np.ndarray = None  # Torquer axis in body frame
    
    # Efficiency
    efficiency: float = 0.95  # Magnetic efficiency
    
    def __post_init__(self):
        if self.axis_body is None:
            self.axis_body = np.array([1, 0, 0])  # Default: X-axis


class Magnetorquer:
    """
    Single-axis magnetorquer (torque rod).
    
    Generates magnetic dipole moment for attitude control
    when interacting with Earth's magnetic field.
    """
    
    def __init__(self, config: MagnetorquerConfig = None):
        """
        Initialize magnetorquer.
        
        Args:
            config: Actuator configuration
        """
        self.config = config or MagnetorquerConfig()
        
        # State
        self.commanded_dipole = 0.0  # Commanded dipole [Am²]
        self.actual_dipole = 0.0  # Actual dipole (with dynamics)
        self.is_enabled = True
        self.power_consumption = 0.0
    
    def command(self, dipole: float) -> float:
        """
        Command dipole moment.
        
        Args:
            dipole: Commanded dipole [Am²]
            
        Returns:
            Actual commanded value (after limits)
        """
        if not self.is_enabled:
            self.commanded_dipole = 0.0
            return 0.0
        
        # Apply limits
        self.commanded_dipole = np.clip(
            dipole, 
            -self.config.max_dipole_Am2,
            self.config.max_dipole_Am2
        )
        
        return self.commanded_dipole
    
    def update(self, dt: float) -> float:
        """
        Update actual dipole with dynamics.
        
        Args:
            dt: Time step [s]
            
        Returns:
            Actual dipole [Am²]
        """
        if not self.is_enabled:
            self.actual_dipole = self.config.residual_dipole_Am2
            self.power_consumption = 0.0
            return self.actual_dipole
        
        # First-order lag dynamics
        tau = self.config.rise_time_ms / 1000.0  # Convert to seconds
        alpha = 1 - np.exp(-dt / tau) if tau > 0 else 1.0
        
        target = self.commanded_dipole * self.config.efficiency
        self.actual_dipole = self.actual_dipole + alpha * (target - self.actual_dipole)
        
        # Add residual
        self.actual_dipole += np.sign(self.actual_dipole) * self.config.residual_dipole_Am2
        
        # Power consumption (proportional to dipole squared)
        dipole_ratio = abs(self.actual_dipole) / self.config.max_dipole_Am2
        self.power_consumption = self.config.power_W * dipole_ratio
        
        return self.actual_dipole
    
    def get_dipole_vector(self) -> np.ndarray:
        """
        Get dipole vector in body frame.
        
        Returns:
            Dipole vector [Am²]
        """
        return self.actual_dipole * self.config.axis_body
    
    def get_torque(self, b_field: np.ndarray) -> np.ndarray:
        """
        Calculate torque from magnetic field interaction.
        
        τ = m × B
        
        Args:
            b_field: Magnetic field in body frame [T]
            
        Returns:
            Torque vector [Nm]
        """
        dipole_vec = self.get_dipole_vector()
        return np.cross(dipole_vec, b_field)
    
    def inject_fault(self, fault_type: str):
        """Inject actuator fault."""
        if fault_type == 'stuck_on':
            self.actual_dipole = self.config.max_dipole_Am2
            self.command = lambda d: self.config.max_dipole_Am2
            self.update = lambda dt: self.config.max_dipole_Am2
        elif fault_type == 'stuck_off':
            self.is_enabled = False
        elif fault_type == 'degraded':
            self.config.max_dipole_Am2 *= 0.5
            self.config.efficiency *= 0.5
    
    def reset(self):
        """Reset actuator state."""
        self.commanded_dipole = 0.0
        self.actual_dipole = 0.0
        self.is_enabled = True
        self.power_consumption = 0.0


class MagnetorquerSet:
    """
    Three-axis magnetorquer set.
    
    Standard configuration with one torquer per body axis.
    """
    
    def __init__(self, configs: List[MagnetorquerConfig] = None):
        """
        Initialize three-axis magnetorquer set.
        
        Args:
            configs: List of 3 configurations (X, Y, Z axes)
        """
        if configs is None:
            configs = [
                MagnetorquerConfig(axis_body=np.array([1, 0, 0])),
                MagnetorquerConfig(axis_body=np.array([0, 1, 0])),
                MagnetorquerConfig(axis_body=np.array([0, 0, 1])),
            ]
        
        self.torquers = [Magnetorquer(cfg) for cfg in configs]
    
    def command(self, dipole_vec: np.ndarray) -> np.ndarray:
        """
        Command dipole vector.
        
        Args:
            dipole_vec: Commanded dipole [Am²] for each axis
            
        Returns:
            Actual commanded values
        """
        return np.array([
            self.torquers[i].command(dipole_vec[i]) 
            for i in range(3)
        ])
    
    def update(self, dt: float) -> np.ndarray:
        """
        Update all torquers.
        
        Args:
            dt: Time step [s]
            
        Returns:
            Actual dipole vector [Am²]
        """
        return np.array([t.update(dt) for t in self.torquers])
    
    def get_dipole_vector(self) -> np.ndarray:
        """Get combined dipole vector."""
        return sum(t.get_dipole_vector() for t in self.torquers)
    
    def get_torque(self, b_field: np.ndarray) -> np.ndarray:
        """
        Calculate total torque from all torquers.
        
        Args:
            b_field: Magnetic field in body frame [T]
            
        Returns:
            Total torque [Nm]
        """
        dipole_vec = self.get_dipole_vector()
        return np.cross(dipole_vec, b_field)
    
    def get_total_power(self) -> float:
        """Get total power consumption [W]."""
        return sum(t.power_consumption for t in self.torquers)
    
    def reset(self):
        """Reset all torquers."""
        for t in self.torquers:
            t.reset()
