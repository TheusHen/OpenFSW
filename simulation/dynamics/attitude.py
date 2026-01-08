"""
Attitude Dynamics
=================

Rigid body attitude dynamics using quaternion representation.
"""

import numpy as np
from typing import Tuple, Optional
from ..core.spacecraft import AttitudeState, Spacecraft


class AttitudeDynamics:
    """
    Attitude dynamics model for rigid body spacecraft.
    
    Features:
    - Quaternion-based attitude representation
    - Euler's equations of motion
    - Gravity gradient torque
    - Magnetic torque
    - External disturbances
    """
    
    # Earth constants
    MU = 398600.4418e9  # m³/s² - gravitational parameter
    
    def __init__(self,
                 inertia: np.ndarray = None,
                 enable_gravity_gradient: bool = True,
                 enable_magnetic_torque: bool = True):
        """
        Initialize attitude dynamics.
        
        Args:
            inertia: 3x3 inertia tensor [kg·m²]
            enable_gravity_gradient: Enable gravity gradient torque
            enable_magnetic_torque: Enable magnetic field interaction torque
        """
        if inertia is None:
            # Default 3U CubeSat inertia
            self.inertia = np.diag([0.008, 0.008, 0.002])
        else:
            self.inertia = inertia
        
        self.inertia_inv = np.linalg.inv(self.inertia)
        
        self.enable_gravity_gradient = enable_gravity_gradient
        self.enable_magnetic_torque = enable_magnetic_torque
    
    def set_inertia(self, inertia: np.ndarray):
        """Update inertia tensor."""
        self.inertia = inertia
        self.inertia_inv = np.linalg.inv(inertia)
    
    def quaternion_derivative(self, 
                               q: np.ndarray, 
                               omega: np.ndarray) -> np.ndarray:
        """
        Quaternion kinematics equation.
        
        Args:
            q: Quaternion [w, x, y, z]
            omega: Angular velocity in body frame [rad/s]
            
        Returns:
            Quaternion derivative dq/dt
        """
        w, x, y, z = q
        wx, wy, wz = omega
        
        # Quaternion multiplication matrix
        Omega = 0.5 * np.array([
            [0, -wx, -wy, -wz],
            [wx, 0, wz, -wy],
            [wy, -wz, 0, wx],
            [wz, wy, -wx, 0]
        ])
        
        return Omega @ q
    
    def angular_acceleration(self,
                              omega: np.ndarray,
                              torque: np.ndarray) -> np.ndarray:
        """
        Euler's equations for angular acceleration.
        
        Args:
            omega: Angular velocity in body frame [rad/s]
            torque: Total torque in body frame [Nm]
            
        Returns:
            Angular acceleration [rad/s²]
        """
        # Euler's equation: I·ω̇ = τ - ω × (I·ω)
        H = self.inertia @ omega  # Angular momentum
        gyro_torque = np.cross(omega, H)  # Gyroscopic torque
        
        omega_dot = self.inertia_inv @ (torque - gyro_torque)
        
        return omega_dot
    
    def gravity_gradient_torque(self,
                                 q: np.ndarray,
                                 r_eci: np.ndarray) -> np.ndarray:
        """
        Calculate gravity gradient torque.
        
        Args:
            q: Attitude quaternion [w, x, y, z]
            r_eci: Position in ECI frame [km]
            
        Returns:
            Gravity gradient torque in body frame [Nm]
        """
        r_km = np.linalg.norm(r_eci)
        r_m = r_km * 1000  # Convert to meters
        
        # Nadir direction in ECI
        nadir_eci = -r_eci / r_km
        
        # Transform to body frame
        R = self._quaternion_to_matrix(q)  # Body to inertial
        nadir_body = R.T @ nadir_eci
        
        # Gravity gradient torque
        # τ_gg = (3μ/r³) * nadir × (I · nadir)
        factor = 3 * self.MU / r_m**3
        
        tau = factor * np.cross(nadir_body, self.inertia @ nadir_body)
        
        return tau
    
    def magnetic_torque(self,
                         dipole: np.ndarray,
                         b_field: np.ndarray) -> np.ndarray:
        """
        Calculate magnetic torque from magnetorquers.
        
        Args:
            dipole: Magnetic dipole moment in body frame [Am²]
            b_field: Magnetic field in body frame [T]
            
        Returns:
            Magnetic torque [Nm]
        """
        return np.cross(dipole, b_field)
    
    def total_torque(self,
                     spacecraft: 'Spacecraft',
                     b_field_body: np.ndarray = None) -> np.ndarray:
        """
        Calculate total torque on spacecraft.
        
        Args:
            spacecraft: Spacecraft object
            b_field_body: Magnetic field in body frame [T]
            
        Returns:
            Total torque in body frame [Nm]
        """
        q = spacecraft.attitude_state.quaternion
        r_eci = spacecraft.orbital_state.position_km
        
        torque = np.zeros(3)
        
        # Gravity gradient
        if self.enable_gravity_gradient:
            torque += self.gravity_gradient_torque(q, r_eci)
        
        # Magnetorquer torque
        if self.enable_magnetic_torque and b_field_body is not None:
            torque += self.magnetic_torque(spacecraft.magnetorquer_dipole, b_field_body)
        
        # Reaction wheel torque (reaction on body)
        torque -= spacecraft.reaction_wheel_torque
        
        # External disturbances
        torque += spacecraft.disturbance_torque
        
        return torque
    
    def derivatives(self, 
                    t: float, 
                    state: np.ndarray,
                    torque: np.ndarray) -> np.ndarray:
        """
        State derivatives for integration.
        
        Args:
            t: Time (unused)
            state: [q_w, q_x, q_y, q_z, omega_x, omega_y, omega_z]
            torque: External torque [Nm]
            
        Returns:
            State derivative
        """
        q = state[:4]
        omega = state[4:7]
        
        # Quaternion derivative
        q_dot = self.quaternion_derivative(q, omega)
        
        # Angular acceleration
        omega_dot = self.angular_acceleration(omega, torque)
        
        return np.concatenate([q_dot, omega_dot])
    
    def propagate(self,
                  attitude: AttitudeState,
                  torque: np.ndarray,
                  dt: float,
                  method: str = 'rk4') -> AttitudeState:
        """
        Propagate attitude state by time step.
        
        Args:
            attitude: Current attitude state
            torque: External torque [Nm]
            dt: Time step [s]
            method: Integration method
            
        Returns:
            Propagated attitude state
        """
        state = attitude.to_array()
        
        if method == 'euler':
            state = self._euler_step(state, torque, dt)
        elif method == 'rk4':
            state = self._rk4_step(state, torque, dt)
        else:
            raise ValueError(f"Unknown method: {method}")
        
        return AttitudeState.from_array(state)
    
    def _euler_step(self, state: np.ndarray, torque: np.ndarray, dt: float) -> np.ndarray:
        """Euler integration step."""
        deriv = self.derivatives(0, state, torque)
        new_state = state + deriv * dt
        
        # Normalize quaternion
        new_state[:4] /= np.linalg.norm(new_state[:4])
        
        return new_state
    
    def _rk4_step(self, state: np.ndarray, torque: np.ndarray, dt: float) -> np.ndarray:
        """RK4 integration step."""
        k1 = self.derivatives(0, state, torque)
        k2 = self.derivatives(0, state + 0.5*dt*k1, torque)
        k3 = self.derivatives(0, state + 0.5*dt*k2, torque)
        k4 = self.derivatives(0, state + dt*k3, torque)
        
        new_state = state + (dt/6) * (k1 + 2*k2 + 2*k3 + k4)
        
        # Normalize quaternion
        new_state[:4] /= np.linalg.norm(new_state[:4])
        
        return new_state
    
    @staticmethod
    def _quaternion_to_matrix(q: np.ndarray) -> np.ndarray:
        """Convert quaternion to rotation matrix (body to inertial)."""
        w, x, y, z = q
        
        return np.array([
            [1-2*(y*y+z*z), 2*(x*y-w*z), 2*(x*z+w*y)],
            [2*(x*y+w*z), 1-2*(x*x+z*z), 2*(y*z-w*x)],
            [2*(x*z-w*y), 2*(y*z+w*x), 1-2*(x*x+y*y)]
        ])


class DetumbleController:
    """
    B-dot detumbling controller.
    
    Simple magnetic detumbling using rate damping.
    """
    
    def __init__(self, gain: float = 1e6):
        """
        Initialize B-dot controller.
        
        Args:
            gain: Controller gain (typically 1e5 to 1e7)
        """
        self.gain = gain
        self.b_prev = None
        self.dt_prev = None
    
    def compute_dipole(self,
                       b_field: np.ndarray,
                       dt: float) -> np.ndarray:
        """
        Compute magnetorquer dipole command using B-dot law.
        
        m = -k * Ḃ
        
        Args:
            b_field: Magnetic field in body frame [T]
            dt: Time step [s]
            
        Returns:
            Dipole command [Am²]
        """
        if self.b_prev is None:
            self.b_prev = b_field
            self.dt_prev = dt
            return np.zeros(3)
        
        # Estimate Ḃ (derivative of B in body frame)
        b_dot = (b_field - self.b_prev) / dt
        
        # B-dot control law
        dipole = -self.gain * b_dot
        
        # Store for next iteration
        self.b_prev = b_field
        self.dt_prev = dt
        
        return dipole
    
    def reset(self):
        """Reset controller state."""
        self.b_prev = None
        self.dt_prev = None
