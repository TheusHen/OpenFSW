"""
Reaction Wheel Model
====================

Reaction wheels for fine attitude control.
"""

import numpy as np
from typing import Optional, List, Tuple
from dataclasses import dataclass


@dataclass
class ReactionWheelConfig:
    """Reaction wheel configuration."""
    # Performance limits
    max_torque_Nm: float = 0.001  # Maximum torque [Nm]
    max_momentum_Nms: float = 0.01  # Maximum momentum storage [Nms]
    max_speed_rpm: float = 6000  # Maximum wheel speed [rpm]
    
    # Dynamics
    inertia_kg_m2: float = 1e-5  # Wheel inertia [kg·m²]
    friction_Nm: float = 1e-5  # Friction torque [Nm]
    motor_time_constant_ms: float = 20.0  # Motor response time
    
    # Axis
    axis_body: np.ndarray = None  # Wheel spin axis in body frame
    
    # Power
    power_per_torque_W_Nm: float = 100.0  # Power efficiency
    idle_power_W: float = 0.05  # Power when spinning at low torque
    
    def __post_init__(self):
        if self.axis_body is None:
            self.axis_body = np.array([1, 0, 0])


class ReactionWheel:
    """
    Single reaction wheel actuator.
    
    Features:
    - Torque and momentum limits
    - Motor dynamics
    - Friction model
    - Saturation detection
    """
    
    def __init__(self, config: ReactionWheelConfig = None):
        """
        Initialize reaction wheel.
        
        Args:
            config: Wheel configuration
        """
        self.config = config or ReactionWheelConfig()
        
        # State
        self.wheel_speed_rad_s = 0.0  # Current wheel speed
        self.commanded_torque = 0.0  # Commanded torque
        self.actual_torque = 0.0  # Actual torque
        self.momentum = 0.0  # Angular momentum storage
        
        self.is_enabled = True
        self.is_saturated = False
        self.power_consumption = 0.0
    
    @property
    def wheel_speed_rpm(self) -> float:
        """Get wheel speed in RPM."""
        return self.wheel_speed_rad_s * 60 / (2 * np.pi)
    
    def command(self, torque: float) -> float:
        """
        Command wheel torque.
        
        Args:
            torque: Commanded torque [Nm]
            
        Returns:
            Actual commanded torque (after limits)
        """
        if not self.is_enabled:
            self.commanded_torque = 0.0
            return 0.0
        
        # Apply torque limit
        self.commanded_torque = np.clip(
            torque,
            -self.config.max_torque_Nm,
            self.config.max_torque_Nm
        )
        
        return self.commanded_torque
    
    def update(self, dt: float) -> float:
        """
        Update wheel state.
        
        Args:
            dt: Time step [s]
            
        Returns:
            Actual reaction torque on spacecraft [Nm]
        """
        if not self.is_enabled:
            self.actual_torque = 0.0
            self.power_consumption = 0.0
            return 0.0
        
        # Motor dynamics (first-order lag)
        tau = self.config.motor_time_constant_ms / 1000.0
        alpha = 1 - np.exp(-dt / tau) if tau > 0 else 1.0
        
        target_torque = self.commanded_torque
        
        # Check momentum saturation
        predicted_momentum = self.momentum + target_torque * dt
        if abs(predicted_momentum) > self.config.max_momentum_Nms:
            # Limit torque to stay within momentum bounds
            self.is_saturated = True
            sign = np.sign(predicted_momentum)
            target_torque = (sign * self.config.max_momentum_Nms - self.momentum) / dt
            target_torque = np.clip(target_torque, -self.config.max_torque_Nm, 
                                     self.config.max_torque_Nm)
        else:
            self.is_saturated = False
        
        # Apply motor dynamics
        self.actual_torque = self.actual_torque + alpha * (target_torque - self.actual_torque)
        
        # Apply friction (opposes wheel motion)
        friction = -np.sign(self.wheel_speed_rad_s) * self.config.friction_Nm
        net_wheel_torque = self.actual_torque + friction
        
        # Update wheel speed and momentum
        wheel_accel = net_wheel_torque / self.config.inertia_kg_m2
        self.wheel_speed_rad_s += wheel_accel * dt
        
        # Speed limit
        max_speed = self.config.max_speed_rpm * 2 * np.pi / 60
        if abs(self.wheel_speed_rad_s) > max_speed:
            self.wheel_speed_rad_s = np.sign(self.wheel_speed_rad_s) * max_speed
            self.is_saturated = True
        
        # Update momentum
        self.momentum = self.config.inertia_kg_m2 * self.wheel_speed_rad_s
        
        # Power consumption
        self.power_consumption = (
            self.config.idle_power_W + 
            abs(self.actual_torque) * self.config.power_per_torque_W_Nm
        )
        
        # Reaction torque on spacecraft (Newton's 3rd law)
        return -self.actual_torque
    
    def get_torque_vector(self) -> np.ndarray:
        """Get torque vector in body frame."""
        return -self.actual_torque * self.config.axis_body
    
    def get_momentum_vector(self) -> np.ndarray:
        """Get momentum vector in body frame."""
        return self.momentum * self.config.axis_body
    
    def desaturate(self, target_momentum: float, rate: float) -> float:
        """
        Command for wheel desaturation.
        
        Args:
            target_momentum: Target momentum [Nms]
            rate: Desaturation rate [Nms/s]
            
        Returns:
            Desaturation torque command
        """
        error = target_momentum - self.momentum
        return np.clip(error * 10, -rate, rate)
    
    def inject_fault(self, fault_type: str):
        """Inject actuator fault."""
        if fault_type == 'stuck':
            self.command = lambda t: 0.0
            self.update = lambda dt: 0.0
        elif fault_type == 'offline':
            self.is_enabled = False
        elif fault_type == 'high_friction':
            self.config.friction_Nm *= 10
    
    def reset(self):
        """Reset wheel state."""
        self.wheel_speed_rad_s = 0.0
        self.commanded_torque = 0.0
        self.actual_torque = 0.0
        self.momentum = 0.0
        self.is_enabled = True
        self.is_saturated = False
        self.power_consumption = 0.0


class ReactionWheelArray:
    """
    Reaction wheel array configuration.
    
    Supports:
    - Three-axis orthogonal configuration
    - Pyramid configuration (4 wheels)
    - Arbitrary configurations
    """
    
    # Standard 3-axis configuration
    THREE_AXIS = [
        np.array([1, 0, 0]),
        np.array([0, 1, 0]),
        np.array([0, 0, 1]),
    ]
    
    # Pyramid configuration (4 wheels at 45° from Z)
    PYRAMID = [
        np.array([0.866, 0, 0.5]),      # X-skewed
        np.array([0, 0.866, 0.5]),      # Y-skewed
        np.array([-0.866, 0, 0.5]),     # -X-skewed
        np.array([0, -0.866, 0.5]),     # -Y-skewed
    ]
    
    def __init__(self, 
                 config: str = 'three_axis',
                 wheel_configs: List[ReactionWheelConfig] = None):
        """
        Initialize wheel array.
        
        Args:
            config: 'three_axis' or 'pyramid'
            wheel_configs: List of wheel configurations
        """
        if config == 'three_axis':
            axes = self.THREE_AXIS
        elif config == 'pyramid':
            axes = self.PYRAMID
        else:
            axes = self.THREE_AXIS
        
        self.wheels = []
        for i, axis in enumerate(axes):
            if wheel_configs and i < len(wheel_configs):
                cfg = wheel_configs[i]
                cfg.axis_body = axis / np.linalg.norm(axis)
            else:
                cfg = ReactionWheelConfig(axis_body=axis / np.linalg.norm(axis))
            self.wheels.append(ReactionWheel(cfg))
        
        # Compute torque distribution matrix
        self._compute_distribution_matrix()
    
    def _compute_distribution_matrix(self):
        """Compute torque distribution matrix for wheel array."""
        # Wheel axes matrix (3 x n_wheels)
        A = np.column_stack([w.config.axis_body for w in self.wheels])
        
        # Pseudo-inverse for torque distribution
        self.distribution_matrix = np.linalg.pinv(A)
    
    def command_torque(self, torque_vec: np.ndarray) -> np.ndarray:
        """
        Command body-frame torque vector.
        
        Distributes torque across wheels.
        
        Args:
            torque_vec: Desired body torque [Nm]
            
        Returns:
            Wheel torque commands
        """
        # Distribute torque to wheels
        wheel_torques = self.distribution_matrix @ torque_vec
        
        # Command each wheel
        for i, wheel in enumerate(self.wheels):
            wheel.command(wheel_torques[i])
        
        return wheel_torques
    
    def update(self, dt: float) -> np.ndarray:
        """
        Update all wheels.
        
        Args:
            dt: Time step [s]
            
        Returns:
            Total reaction torque on spacecraft [Nm]
        """
        total_torque = np.zeros(3)
        for wheel in self.wheels:
            wheel.update(dt)
            total_torque += wheel.get_torque_vector()
        
        return total_torque
    
    def get_total_momentum(self) -> np.ndarray:
        """Get total momentum vector in body frame."""
        return sum(w.get_momentum_vector() for w in self.wheels)
    
    def get_total_power(self) -> float:
        """Get total power consumption."""
        return sum(w.power_consumption for w in self.wheels)
    
    def is_any_saturated(self) -> bool:
        """Check if any wheel is saturated."""
        return any(w.is_saturated for w in self.wheels)
    
    def reset(self):
        """Reset all wheels."""
        for w in self.wheels:
            w.reset()
