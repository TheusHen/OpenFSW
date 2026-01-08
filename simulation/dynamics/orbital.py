"""
Orbital Dynamics
================

Two-body orbital dynamics with perturbations for LEO satellites.
"""

import numpy as np
from typing import Tuple, Optional
from ..core.spacecraft import OrbitalState


class OrbitalDynamics:
    """
    Orbital dynamics model for LEO satellites.
    
    Features:
    - Two-body Keplerian dynamics
    - J2 oblateness perturbation
    - Optional atmospheric drag (simplified)
    """
    
    # Earth constants
    MU = 398600.4418  # km³/s² - gravitational parameter
    RE = 6378.137  # km - equatorial radius
    J2 = 1.08263e-3  # J2 coefficient
    
    # Atmosphere model constants (simplified exponential)
    RHO_0 = 1.225e-12  # kg/m³ reference density at sea level (scaled)
    H_0 = 7.249  # km - scale height
    
    def __init__(self, 
                 enable_j2: bool = True,
                 enable_drag: bool = False,
                 drag_coefficient: float = 2.2,
                 area_m2: float = 0.034,  # 3U CubeSat 10x34cm face
                 mass_kg: float = 4.0):
        """
        Initialize orbital dynamics.
        
        Args:
            enable_j2: Enable J2 perturbation
            enable_drag: Enable atmospheric drag
            drag_coefficient: Drag coefficient (Cd)
            area_m2: Cross-sectional area in m²
            mass_kg: Spacecraft mass in kg
        """
        self.enable_j2 = enable_j2
        self.enable_drag = enable_drag
        self.cd = drag_coefficient
        self.area = area_m2
        self.mass = mass_kg
    
    def acceleration(self, state: np.ndarray) -> np.ndarray:
        """
        Calculate total acceleration.
        
        Args:
            state: [x, y, z, vx, vy, vz] in km and km/s
            
        Returns:
            Acceleration [ax, ay, az] in km/s²
        """
        r = state[:3]
        v = state[3:6]
        
        # Two-body acceleration
        a = self._two_body_acceleration(r)
        
        # Add perturbations
        if self.enable_j2:
            a += self._j2_acceleration(r)
        
        if self.enable_drag:
            a += self._drag_acceleration(r, v)
        
        return a
    
    def _two_body_acceleration(self, r: np.ndarray) -> np.ndarray:
        """Keplerian two-body acceleration."""
        r_mag = np.linalg.norm(r)
        return -self.MU * r / r_mag**3
    
    def _j2_acceleration(self, r: np.ndarray) -> np.ndarray:
        """
        J2 oblateness perturbation acceleration.
        
        Accounts for Earth's equatorial bulge.
        """
        r_mag = np.linalg.norm(r)
        x, y, z = r
        
        # J2 coefficient
        factor = 1.5 * self.J2 * self.MU * self.RE**2 / r_mag**5
        z_factor = 5 * z**2 / r_mag**2 - 1
        
        ax = factor * x * z_factor
        ay = factor * y * z_factor
        az = factor * z * (5 * z**2 / r_mag**2 - 3)
        
        return np.array([ax, ay, az])
    
    def _drag_acceleration(self, r: np.ndarray, v: np.ndarray) -> np.ndarray:
        """
        Simplified atmospheric drag acceleration.
        
        Uses exponential atmosphere model.
        """
        r_mag = np.linalg.norm(r)
        altitude = r_mag - self.RE
        
        # Atmospheric density (exponential model)
        if altitude < 200:
            # Below 200km, use higher density
            rho = self.RHO_0 * np.exp(-(altitude) / self.H_0)
        elif altitude < 1000:
            # Simplified model for LEO
            rho = 1e-12 * np.exp(-(altitude - 500) / 60)  # kg/km³
        else:
            rho = 0.0
        
        # Relative velocity (assuming co-rotating atmosphere)
        omega_earth = 7.2921159e-5  # rad/s
        v_atm = np.array([-omega_earth * r[1], omega_earth * r[0], 0])  # km/s
        v_rel = v - v_atm
        v_rel_mag = np.linalg.norm(v_rel)
        
        if v_rel_mag < 1e-10:
            return np.zeros(3)
        
        # Drag acceleration (km/s²)
        # Area and density need unit conversion
        area_km2 = self.area * 1e-6  # m² to km²
        a_drag = -0.5 * rho * self.cd * area_km2 / self.mass * v_rel_mag * v_rel
        
        return a_drag
    
    def derivatives(self, t: float, state: np.ndarray) -> np.ndarray:
        """
        State derivatives for integration.
        
        Args:
            t: Time (unused for autonomous system)
            state: [x, y, z, vx, vy, vz]
            
        Returns:
            [vx, vy, vz, ax, ay, az]
        """
        v = state[3:6]
        a = self.acceleration(state)
        return np.concatenate([v, a])
    
    def propagate(self, 
                  initial_state: OrbitalState, 
                  dt: float,
                  method: str = 'rk4') -> OrbitalState:
        """
        Propagate orbital state by time step.
        
        Args:
            initial_state: Initial orbital state
            dt: Time step in seconds
            method: Integration method ('euler', 'rk4')
            
        Returns:
            Propagated orbital state
        """
        state = initial_state.to_array()
        
        if method == 'euler':
            state = self._euler_step(state, dt)
        elif method == 'rk4':
            state = self._rk4_step(state, dt)
        else:
            raise ValueError(f"Unknown integration method: {method}")
        
        return OrbitalState.from_array(state)
    
    def _euler_step(self, state: np.ndarray, dt: float) -> np.ndarray:
        """Simple Euler integration step."""
        return state + self.derivatives(0, state) * dt
    
    def _rk4_step(self, state: np.ndarray, dt: float) -> np.ndarray:
        """4th order Runge-Kutta integration step."""
        k1 = self.derivatives(0, state)
        k2 = self.derivatives(0, state + 0.5 * dt * k1)
        k3 = self.derivatives(0, state + 0.5 * dt * k2)
        k4 = self.derivatives(0, state + dt * k3)
        
        return state + (dt / 6) * (k1 + 2*k2 + 2*k3 + k4)
    
    def orbital_elements(self, state: OrbitalState) -> dict:
        """
        Calculate classical orbital elements from state vector.
        
        Args:
            state: Orbital state
            
        Returns:
            Dictionary with orbital elements
        """
        r = state.position_km
        v = state.velocity_km_s
        r_mag = np.linalg.norm(r)
        v_mag = np.linalg.norm(v)
        
        # Specific angular momentum
        h = np.cross(r, v)
        h_mag = np.linalg.norm(h)
        
        # Node vector
        n = np.cross([0, 0, 1], h)
        n_mag = np.linalg.norm(n)
        
        # Eccentricity vector
        e_vec = ((v_mag**2 - self.MU/r_mag) * r - np.dot(r, v) * v) / self.MU
        e = np.linalg.norm(e_vec)
        
        # Semi-major axis
        energy = v_mag**2 / 2 - self.MU / r_mag
        if abs(e - 1.0) > 1e-10:
            a = -self.MU / (2 * energy)
        else:
            a = float('inf')
        
        # Inclination
        i = np.arccos(h[2] / h_mag)
        
        # RAAN
        if n_mag > 1e-10:
            Omega = np.arccos(n[0] / n_mag)
            if n[1] < 0:
                Omega = 2*np.pi - Omega
        else:
            Omega = 0.0
        
        # Argument of perigee
        if n_mag > 1e-10 and e > 1e-10:
            omega = np.arccos(np.dot(n, e_vec) / (n_mag * e))
            if e_vec[2] < 0:
                omega = 2*np.pi - omega
        else:
            omega = 0.0
        
        # True anomaly
        if e > 1e-10:
            nu = np.arccos(np.dot(e_vec, r) / (e * r_mag))
            if np.dot(r, v) < 0:
                nu = 2*np.pi - nu
        else:
            nu = 0.0
        
        return {
            'semi_major_axis_km': a,
            'eccentricity': e,
            'inclination_deg': np.degrees(i),
            'raan_deg': np.degrees(Omega),
            'arg_perigee_deg': np.degrees(omega),
            'true_anomaly_deg': np.degrees(nu),
            'period_minutes': 2*np.pi*np.sqrt(a**3/self.MU)/60 if a > 0 else 0
        }
