"""
Spacecraft Model
================

Complete 3U CubeSat physical model.
"""

import numpy as np
from dataclasses import dataclass
from typing import Dict


@dataclass
class SpacecraftPhysicalConfig:
    """Physical configuration of 3U CubeSat."""
    
    # Dimensions (m)
    length_x: float = 0.1      # 10cm
    length_y: float = 0.1      # 10cm
    length_z: float = 0.34     # 34cm (3U)
    
    # Mass properties
    mass_kg: float = 4.0
    
    # Moments of inertia (kg*m^2)
    Ixx: float = 0.0046
    Iyy: float = 0.0046
    Izz: float = 0.0017
    
    # Products of inertia (usually small)
    Ixy: float = 0.0
    Ixz: float = 0.0
    Iyz: float = 0.0
    
    # Center of mass offset from geometric center (m)
    cm_offset_x: float = 0.0
    cm_offset_y: float = 0.0
    cm_offset_z: float = 0.0


class SpacecraftModel:
    """
    Complete 3U CubeSat physical model.
    
    Includes:
    - Mass and inertia properties
    - Surface areas for drag and solar pressure
    - Magnetic properties for residual dipole
    """
    
    def __init__(self, config: SpacecraftPhysicalConfig = None):
        """
        Initialize spacecraft model.
        
        Args:
            config: Physical configuration
        """
        self.config = config or SpacecraftPhysicalConfig()
        
        # Compute inertia tensor
        self._inertia_tensor = np.array([
            [self.config.Ixx, -self.config.Ixy, -self.config.Ixz],
            [-self.config.Ixy, self.config.Iyy, -self.config.Iyz],
            [-self.config.Ixz, -self.config.Iyz, self.config.Izz]
        ])
        
        self._inertia_inv = np.linalg.inv(self._inertia_tensor)
        
        # Surface areas for each face (m^2)
        self._surface_areas = {
            '+X': self.config.length_y * self.config.length_z,
            '-X': self.config.length_y * self.config.length_z,
            '+Y': self.config.length_x * self.config.length_z,
            '-Y': self.config.length_x * self.config.length_z,
            '+Z': self.config.length_x * self.config.length_y,
            '-Z': self.config.length_x * self.config.length_y,
        }
        
        # Solar panel configuration (body-mounted on +/-Z faces)
        self.solar_panel_area = self._surface_areas['+Z']
        self.solar_panel_efficiency = 0.28  # Triple-junction GaAs
        
        # Residual magnetic dipole (A*m^2)
        self.residual_dipole = np.array([0.001, 0.001, 0.002])
        
        # Drag coefficient
        self.Cd = 2.2
        
        # Solar radiation pressure properties
        self.reflectivity = 0.4
    
    @property
    def inertia_tensor(self) -> np.ndarray:
        """Get 3x3 inertia tensor (kg*m^2)."""
        return self._inertia_tensor
    
    @property
    def inertia_inv(self) -> np.ndarray:
        """Get inverse inertia tensor."""
        return self._inertia_inv
    
    @property
    def mass(self) -> float:
        """Get mass in kg."""
        return self.config.mass_kg
    
    def get_cross_sectional_area(self, velocity_body: np.ndarray) -> float:
        """
        Calculate projected cross-sectional area for drag.
        
        Args:
            velocity_body: Velocity vector in body frame (for direction)
            
        Returns:
            Cross-sectional area in m^2
        """
        v_norm = np.linalg.norm(velocity_body)
        if v_norm < 1e-9:
            return self._surface_areas['+Z']  # Default
        
        v_hat = velocity_body / v_norm
        
        # Projected area is sum of face areas * cos(angle)
        area = 0.0
        
        # +X, -X faces
        area += abs(v_hat[0]) * self._surface_areas['+X']
        # +Y, -Y faces  
        area += abs(v_hat[1]) * self._surface_areas['+Y']
        # +Z, -Z faces
        area += abs(v_hat[2]) * self._surface_areas['+Z']
        
        return area
    
    def get_illuminated_area(self, sun_direction_body: np.ndarray) -> float:
        """
        Calculate illuminated solar panel area.
        
        Args:
            sun_direction_body: Sun direction in body frame
            
        Returns:
            Effective illuminated area in m^2
        """
        s_norm = np.linalg.norm(sun_direction_body)
        if s_norm < 1e-9:
            return 0.0
        
        s_hat = sun_direction_body / s_norm
        
        # Solar panels on +Z face
        cos_angle = np.dot(s_hat, np.array([0, 0, 1]))
        
        if cos_angle > 0:
            return self.solar_panel_area * cos_angle
        else:
            return 0.0
    
    def get_solar_power(self, sun_direction_body: np.ndarray, 
                        solar_flux: float = 1361.0) -> float:
        """
        Calculate solar power generated.
        
        Args:
            sun_direction_body: Sun direction in body frame
            solar_flux: Solar flux in W/m^2
            
        Returns:
            Power in Watts
        """
        area = self.get_illuminated_area(sun_direction_body)
        return area * solar_flux * self.solar_panel_efficiency
    
    def get_disturbance_torque(self, magnetic_field_body: np.ndarray) -> np.ndarray:
        """
        Calculate disturbance torque from residual dipole.
        
        Args:
            magnetic_field_body: Magnetic field in body frame (T)
            
        Returns:
            Torque in Nm
        """
        return np.cross(self.residual_dipole, magnetic_field_body)
    
    def get_properties(self) -> Dict:
        """Get all spacecraft properties."""
        return {
            'mass_kg': self.config.mass_kg,
            'dimensions_m': [self.config.length_x, 
                           self.config.length_y, 
                           self.config.length_z],
            'inertia_diagonal': [self.config.Ixx, 
                                self.config.Iyy, 
                                self.config.Izz],
            'surface_areas_m2': self._surface_areas,
            'solar_panel_area_m2': self.solar_panel_area,
            'solar_panel_efficiency': self.solar_panel_efficiency,
            'Cd': self.Cd,
        }
