"""
Sun Sensor Model
================

Multi-head sun sensor for attitude determination.
"""

import numpy as np
from typing import Optional, List, Tuple
from dataclasses import dataclass


@dataclass
class SunSensorConfig:
    """Sun sensor configuration."""
    # Accuracy
    accuracy_deg: float = 1.0  # Measurement accuracy [deg]
    resolution_deg: float = 0.1  # Resolution
    
    # Field of view
    fov_half_angle_deg: float = 60.0  # Half-angle of FOV
    
    # Mounting
    normal_body: np.ndarray = None  # Sensor normal in body frame
    
    # Operational
    sample_rate_hz: float = 5.0
    albedo_sensitivity: float = 0.1  # Sensitivity to Earth albedo (0-1)
    
    def __post_init__(self):
        if self.normal_body is None:
            self.normal_body = np.array([0, 0, 1])  # Default: +Z face


class SunSensor:
    """
    Single-axis or two-axis sun sensor.
    
    Models:
    - Field of view constraints
    - Measurement noise
    - Earth albedo interference
    - Eclipse detection
    """
    
    def __init__(self, config: SunSensorConfig = None):
        """
        Initialize sun sensor.
        
        Args:
            config: Sensor configuration
        """
        self.config = config or SunSensorConfig()
        
        # State
        self.sun_visible = False
        self.last_direction = np.zeros(3)
        self.is_valid = True
        self.sample_count = 0
    
    def measure(self,
                sun_direction_body: np.ndarray,
                in_eclipse: bool = False,
                add_noise: bool = True) -> Tuple[np.ndarray, bool]:
        """
        Generate sun sensor measurement.
        
        Args:
            sun_direction_body: Sun direction unit vector in body frame
            in_eclipse: Whether spacecraft is in Earth's shadow
            add_noise: Whether to add measurement noise
            
        Returns:
            Tuple of (measured_direction, sun_visible)
        """
        if not self.is_valid:
            return np.zeros(3), False
        
        # Check if sun is in field of view
        sun_dir = sun_direction_body / np.linalg.norm(sun_direction_body)
        
        # Angle between sun and sensor normal
        cos_angle = np.dot(sun_dir, self.config.normal_body)
        angle_deg = np.degrees(np.arccos(np.clip(cos_angle, -1, 1)))
        
        # Eclipse or outside FOV
        if in_eclipse or angle_deg > self.config.fov_half_angle_deg:
            self.sun_visible = False
            self.last_direction = np.zeros(3)
            return np.zeros(3), False
        
        self.sun_visible = True
        
        # Add measurement noise
        if add_noise:
            # Angular noise
            noise_rad = np.radians(np.random.normal(0, self.config.accuracy_deg))
            
            # Create perpendicular perturbation
            perp1 = np.cross(sun_dir, self.config.normal_body)
            if np.linalg.norm(perp1) < 1e-6:
                perp1 = np.cross(sun_dir, np.array([1, 0, 0]))
            perp1 /= np.linalg.norm(perp1)
            perp2 = np.cross(sun_dir, perp1)
            
            # Random direction in perpendicular plane
            phi = np.random.uniform(0, 2*np.pi)
            perturbation = noise_rad * (np.cos(phi) * perp1 + np.sin(phi) * perp2)
            
            measured = sun_dir + perturbation
            measured /= np.linalg.norm(measured)
        else:
            measured = sun_dir.copy()
        
        # Quantization
        measured = np.round(measured / np.radians(self.config.resolution_deg)) * np.radians(self.config.resolution_deg)
        
        # Re-normalize
        measured /= np.linalg.norm(measured)
        
        self.last_direction = measured
        self.sample_count += 1
        
        return measured, True
    
    def inject_fault(self, fault_type: str):
        """Inject sensor fault."""
        if fault_type == 'stuck':
            self.measure = lambda sun, eclipse=False, noise=True: (self.last_direction, self.sun_visible)
        elif fault_type == 'false_sun':
            # Reports sun when there is none
            self.sun_visible = True
            self.last_direction = np.array([0.707, 0.707, 0])
        elif fault_type == 'offline':
            self.is_valid = False
    
    def reset(self):
        """Reset sensor state."""
        self.sun_visible = False
        self.last_direction = np.zeros(3)
        self.sample_count = 0
        self.is_valid = True


class SunSensorArray:
    """
    Array of sun sensors for full-sphere coverage.
    
    Typically mounted on different faces of the CubeSat.
    """
    
    # Standard 6-face mounting (±X, ±Y, ±Z)
    STANDARD_NORMALS = [
        np.array([1, 0, 0]),   # +X
        np.array([-1, 0, 0]),  # -X
        np.array([0, 1, 0]),   # +Y
        np.array([0, -1, 0]),  # -Y
        np.array([0, 0, 1]),   # +Z
        np.array([0, 0, -1]),  # -Z
    ]
    
    def __init__(self, num_sensors: int = 6, configs: List[SunSensorConfig] = None):
        """
        Initialize sun sensor array.
        
        Args:
            num_sensors: Number of sensors (default 6 for full coverage)
            configs: List of configurations (one per sensor)
        """
        self.sensors = []
        
        for i in range(num_sensors):
            if configs and i < len(configs):
                config = configs[i]
            else:
                config = SunSensorConfig()
                if i < len(self.STANDARD_NORMALS):
                    config.normal_body = self.STANDARD_NORMALS[i]
            
            self.sensors.append(SunSensor(config))
    
    def measure(self,
                sun_direction_body: np.ndarray,
                in_eclipse: bool = False,
                add_noise: bool = True) -> Tuple[np.ndarray, bool, List[int]]:
        """
        Get composite sun direction from all sensors.
        
        Args:
            sun_direction_body: True sun direction in body frame
            in_eclipse: Eclipse flag
            add_noise: Add noise to measurements
            
        Returns:
            Tuple of (best_direction, sun_visible, visible_sensor_indices)
        """
        visible_sensors = []
        directions = []
        
        for i, sensor in enumerate(self.sensors):
            direction, visible = sensor.measure(sun_direction_body, in_eclipse, add_noise)
            if visible:
                visible_sensors.append(i)
                directions.append(direction)
        
        if len(visible_sensors) == 0:
            return np.zeros(3), False, []
        
        # Use best measurement (closest to sensor normal)
        # In practice, would use weighted average or voting
        best_direction = np.mean(directions, axis=0)
        best_direction /= np.linalg.norm(best_direction)
        
        return best_direction, True, visible_sensors
    
    def reset(self):
        """Reset all sensors."""
        for sensor in self.sensors:
            sensor.reset()
