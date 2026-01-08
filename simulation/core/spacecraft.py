"""
Spacecraft State and Model
==========================

Core spacecraft representation including state vectors,
attitude, and physical properties.
"""

import numpy as np
from dataclasses import dataclass, field
from typing import Optional, Tuple
from .config import SpacecraftParameters, OrbitalParameters


@dataclass
class OrbitalState:
    """Spacecraft orbital state in ECI frame."""
    position_km: np.ndarray = field(default_factory=lambda: np.array([6878.0, 0.0, 0.0]))
    velocity_km_s: np.ndarray = field(default_factory=lambda: np.array([0.0, 7.612, 0.0]))
    
    @property
    def radius_km(self) -> float:
        """Orbital radius magnitude."""
        return np.linalg.norm(self.position_km)
    
    @property
    def speed_km_s(self) -> float:
        """Speed magnitude."""
        return np.linalg.norm(self.velocity_km_s)
    
    @property
    def altitude_km(self) -> float:
        """Altitude above Earth surface (assuming spherical Earth)."""
        return self.radius_km - 6378.0
    
    def to_array(self) -> np.ndarray:
        """Return state as 6-element array."""
        return np.concatenate([self.position_km, self.velocity_km_s])
    
    @classmethod
    def from_array(cls, state: np.ndarray) -> 'OrbitalState':
        """Create from 6-element array."""
        return cls(
            position_km=state[:3].copy(),
            velocity_km_s=state[3:6].copy()
        )


@dataclass
class AttitudeState:
    """Spacecraft attitude state."""
    # Quaternion [w, x, y, z] - scalar first
    quaternion: np.ndarray = field(default_factory=lambda: np.array([1.0, 0.0, 0.0, 0.0]))
    # Angular velocity in body frame [rad/s]
    angular_velocity: np.ndarray = field(default_factory=lambda: np.array([0.0, 0.0, 0.0]))
    
    def normalize_quaternion(self):
        """Normalize quaternion to unit length."""
        norm = np.linalg.norm(self.quaternion)
        if norm > 1e-10:
            self.quaternion /= norm
    
    @property
    def euler_angles_deg(self) -> np.ndarray:
        """
        Convert quaternion to Euler angles (roll, pitch, yaw) in degrees.
        Using ZYX convention.
        """
        q = self.quaternion
        w, x, y, z = q[0], q[1], q[2], q[3]
        
        # Roll (x-axis rotation)
        sinr_cosp = 2 * (w * x + y * z)
        cosr_cosp = 1 - 2 * (x * x + y * y)
        roll = np.arctan2(sinr_cosp, cosr_cosp)
        
        # Pitch (y-axis rotation)
        sinp = 2 * (w * y - z * x)
        if abs(sinp) >= 1:
            pitch = np.copysign(np.pi / 2, sinp)
        else:
            pitch = np.arcsin(sinp)
        
        # Yaw (z-axis rotation)
        siny_cosp = 2 * (w * z + x * y)
        cosy_cosp = 1 - 2 * (y * y + z * z)
        yaw = np.arctan2(siny_cosp, cosy_cosp)
        
        return np.degrees(np.array([roll, pitch, yaw]))
    
    @property
    def rotation_matrix(self) -> np.ndarray:
        """
        Convert quaternion to rotation matrix (body to inertial).
        """
        q = self.quaternion
        w, x, y, z = q[0], q[1], q[2], q[3]
        
        return np.array([
            [1-2*(y*y+z*z), 2*(x*y-w*z), 2*(x*z+w*y)],
            [2*(x*y+w*z), 1-2*(x*x+z*z), 2*(y*z-w*x)],
            [2*(x*z-w*y), 2*(y*z+w*x), 1-2*(x*x+y*y)]
        ])
    
    def to_array(self) -> np.ndarray:
        """Return state as 7-element array."""
        return np.concatenate([self.quaternion, self.angular_velocity])
    
    @classmethod
    def from_array(cls, state: np.ndarray) -> 'AttitudeState':
        """Create from 7-element array."""
        attitude = cls(
            quaternion=state[:4].copy(),
            angular_velocity=state[4:7].copy()
        )
        attitude.normalize_quaternion()
        return attitude


class Spacecraft:
    """
    Complete spacecraft model.
    
    Manages:
    - Orbital state
    - Attitude state
    - Physical properties
    - Sensor readings
    - Actuator commands
    """
    
    def __init__(self, 
                 params: SpacecraftParameters = None,
                 orbital_params: OrbitalParameters = None):
        """
        Initialize spacecraft.
        
        Args:
            params: Spacecraft physical parameters
            orbital_params: Initial orbital elements
        """
        self.params = params or SpacecraftParameters()
        self.orbital_params = orbital_params or OrbitalParameters()
        
        # Initialize states
        self.orbital_state = self._initial_orbital_state()
        self.attitude_state = AttitudeState()
        
        # Actuator commands (current)
        self.magnetorquer_dipole = np.zeros(3)  # Am²
        self.reaction_wheel_torque = np.zeros(3)  # Nm
        
        # Reaction wheel momentum
        self.rw_momentum = np.zeros(3)  # Nms
        
        # Accumulated disturbance torques
        self.disturbance_torque = np.zeros(3)  # Nm
        
    def _initial_orbital_state(self) -> OrbitalState:
        """
        Calculate initial orbital state from orbital elements.
        
        Returns:
            OrbitalState with position and velocity in ECI frame
        """
        # Orbital elements to radians
        a = self.orbital_params.semi_major_axis_km
        e = self.orbital_params.eccentricity
        i = np.radians(self.orbital_params.inclination_deg)
        Omega = np.radians(self.orbital_params.raan_deg)
        omega = np.radians(self.orbital_params.arg_perigee_deg)
        nu = np.radians(self.orbital_params.true_anomaly_deg)
        
        # Gravitational parameter
        mu = 398600.4418  # km³/s²
        
        # Semi-latus rectum
        p = a * (1 - e**2)
        
        # Position and velocity in perifocal frame
        r_pqw = (p / (1 + e * np.cos(nu))) * np.array([np.cos(nu), np.sin(nu), 0])
        v_pqw = np.sqrt(mu / p) * np.array([-np.sin(nu), e + np.cos(nu), 0])
        
        # Rotation matrices
        R3_Omega = np.array([
            [np.cos(Omega), -np.sin(Omega), 0],
            [np.sin(Omega), np.cos(Omega), 0],
            [0, 0, 1]
        ])
        
        R1_i = np.array([
            [1, 0, 0],
            [0, np.cos(i), -np.sin(i)],
            [0, np.sin(i), np.cos(i)]
        ])
        
        R3_omega = np.array([
            [np.cos(omega), -np.sin(omega), 0],
            [np.sin(omega), np.cos(omega), 0],
            [0, 0, 1]
        ])
        
        # Combined rotation
        Q = R3_Omega @ R1_i @ R3_omega
        
        # Transform to ECI
        r_eci = Q @ r_pqw
        v_eci = Q @ v_pqw
        
        return OrbitalState(position_km=r_eci, velocity_km_s=v_eci)
    
    def get_nadir_vector_body(self) -> np.ndarray:
        """
        Get nadir direction in body frame.
        
        Returns:
            Unit vector pointing to Earth center in body frame
        """
        # Nadir in ECI is -position/|position|
        nadir_eci = -self.orbital_state.position_km / self.orbital_state.radius_km
        
        # Transform to body frame
        R_bi = self.attitude_state.rotation_matrix.T  # Inertial to body
        return R_bi @ nadir_eci
    
    def get_velocity_vector_body(self) -> np.ndarray:
        """
        Get velocity direction in body frame.
        
        Returns:
            Unit vector in velocity direction in body frame
        """
        vel_eci = self.orbital_state.velocity_km_s / self.orbital_state.speed_km_s
        R_bi = self.attitude_state.rotation_matrix.T
        return R_bi @ vel_eci
    
    def set_angular_velocity(self, omega: np.ndarray):
        """Set angular velocity in body frame [rad/s]."""
        self.attitude_state.angular_velocity = np.asarray(omega, dtype=float).copy()
    
    def set_quaternion(self, q: np.ndarray):
        """Set attitude quaternion [w, x, y, z]."""
        self.attitude_state.quaternion = np.asarray(q, dtype=float).copy()
        self.attitude_state.normalize_quaternion()
    
    def set_magnetorquer_command(self, dipole: np.ndarray):
        """Set magnetorquer dipole command [Am²]."""
        # Limit to maximum dipole
        max_dipole = 0.2  # Am²
        self.magnetorquer_dipole = np.clip(dipole, -max_dipole, max_dipole)
    
    def set_reaction_wheel_command(self, torque: np.ndarray):
        """Set reaction wheel torque command [Nm]."""
        max_torque = 0.001  # Nm
        self.reaction_wheel_torque = np.clip(torque, -max_torque, max_torque)
    
    def get_inertia_matrix(self) -> np.ndarray:
        """Get spacecraft inertia tensor."""
        return self.params.inertia_matrix
    
    def kinetic_energy(self) -> float:
        """Calculate rotational kinetic energy [J]."""
        omega = self.attitude_state.angular_velocity
        I = self.get_inertia_matrix()
        return 0.5 * omega @ I @ omega
    
    def angular_momentum(self) -> np.ndarray:
        """Calculate total angular momentum in body frame [Nms]."""
        omega = self.attitude_state.angular_velocity
        I = self.get_inertia_matrix()
        H_body = I @ omega
        H_wheels = self.rw_momentum
        return H_body + H_wheels
    
    def __repr__(self) -> str:
        return (f"Spacecraft(alt={self.orbital_state.altitude_km:.1f}km, "
                f"euler={self.attitude_state.euler_angles_deg}, "
                f"omega={np.degrees(self.attitude_state.angular_velocity)} deg/s)")
