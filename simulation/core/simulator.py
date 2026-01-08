"""
Main Simulator
==============

Central simulation engine orchestrating all components.
"""

import numpy as np
from typing import Optional, Dict, List, Callable
from datetime import datetime
from dataclasses import dataclass, field

from .config import SimulationConfig
from .spacecraft import Spacecraft
from .time_manager import SimulationTime
from ..dynamics.orbital import OrbitalDynamics
from ..dynamics.attitude import AttitudeDynamics
from ..sensors.magnetometer import Magnetometer
from ..sensors.gyroscope import Gyroscope
from ..sensors.sun_sensor import SunSensorArray
from ..actuators.magnetorquer import MagnetorquerSet
from ..environment.magnetic_field import MagneticFieldModel
from ..environment.sun import SunModel
from ..environment.eclipse import EclipseModel
from ..environment.ground_station import GroundStation


@dataclass
class SimulationState:
    """Complete simulation state for logging."""
    time_s: float = 0.0
    position_km: np.ndarray = field(default_factory=lambda: np.zeros(3))
    velocity_km_s: np.ndarray = field(default_factory=lambda: np.zeros(3))
    quaternion: np.ndarray = field(default_factory=lambda: np.array([1., 0., 0., 0.]))
    angular_velocity: np.ndarray = field(default_factory=lambda: np.zeros(3))
    
    # Sensor readings
    mag_field_body_uT: np.ndarray = field(default_factory=lambda: np.zeros(3))
    gyro_rate: np.ndarray = field(default_factory=lambda: np.zeros(3))
    sun_direction_body: np.ndarray = field(default_factory=lambda: np.zeros(3))
    sun_visible: bool = False
    
    # Environment
    in_eclipse: bool = False
    altitude_km: float = 0.0
    
    # Ground station
    gs_visible: bool = False
    gs_elevation_deg: float = 0.0


class Simulator:
    """
    OpenFSW-LEO-3U Simulation Engine.
    
    Integrates:
    - Orbital dynamics with J2 perturbation
    - Attitude dynamics with disturbance torques
    - Sensor models with noise
    - Actuator models with dynamics
    - Environment models (magnetic field, sun, eclipse)
    - Ground station passes
    """
    
    def __init__(self, config: SimulationConfig = None):
        """
        Initialize simulator.
        
        Args:
            config: Simulation configuration
        """
        self.config = config or SimulationConfig()
        
        # Initialize time
        self.time = SimulationTime(
            start_time=self.config.start_time,
            time_step=self.config.time_step_seconds
        )
        
        # Initialize spacecraft
        self.spacecraft = Spacecraft(
            params=self.config.spacecraft,
            orbital_params=self.config.orbit
        )
        
        # Initialize dynamics
        self.orbital_dynamics = OrbitalDynamics(
            enable_j2=self.config.enable_j2_perturbation,
            enable_drag=self.config.enable_atmospheric_drag,
            mass_kg=self.config.spacecraft.mass_kg
        )
        
        self.attitude_dynamics = AttitudeDynamics(
            inertia=self.config.spacecraft.inertia_matrix,
            enable_gravity_gradient=self.config.enable_gravity_gradient
        )
        
        # Initialize sensors
        self.magnetometer = Magnetometer()
        self.gyroscope = Gyroscope()
        self.sun_sensors = SunSensorArray()
        
        # Initialize actuators
        self.magnetorquers = MagnetorquerSet()
        
        # Initialize environment
        self.magnetic_field = MagneticFieldModel(date=self.config.start_time)
        self.sun_model = SunModel()
        self.eclipse_model = EclipseModel()
        self.ground_station = GroundStation()
        
        # Simulation state
        self.is_running = False
        self.step_count = 0
        
        # Data logging
        self.history: List[SimulationState] = []
        
        # Callbacks
        self.step_callbacks: List[Callable] = []
        
    def reset(self):
        """Reset simulation to initial state."""
        self.time.reset()
        self.spacecraft = Spacecraft(
            params=self.config.spacecraft,
            orbital_params=self.config.orbit
        )
        self.magnetorquers.reset()
        self.magnetometer.reset()
        self.gyroscope.reset()
        self.sun_sensors.reset()
        self.history.clear()
        self.step_count = 0
    
    def step(self) -> SimulationState:
        """
        Advance simulation by one time step.
        
        Returns:
            Current simulation state
        """
        dt = self.config.time_step_seconds
        
        # Get current time parameters
        jd = self.time.julian_date
        gmst = self.time.gmst()
        
        # Current state
        pos = self.spacecraft.orbital_state.position_km
        vel = self.spacecraft.orbital_state.velocity_km_s
        quat = self.spacecraft.attitude_state.quaternion
        omega = self.spacecraft.attitude_state.angular_velocity
        
        # === Environment ===
        
        # Magnetic field in body frame
        b_field_body = self.magnetic_field.get_field_body(pos, quat, gmst)
        b_field_body_uT = b_field_body * 1e6
        
        # Sun position and direction
        sun_pos = self.sun_model.position_eci(jd)
        sun_dir_body = self.sun_model.direction_body(jd, quat)
        
        # Eclipse check
        eclipse_type, illumination = self.eclipse_model.check_eclipse(pos, sun_pos)
        in_eclipse = illumination < 0.5
        
        # Ground station visibility
        gs_visible = self.ground_station.is_visible(pos, gmst)
        gs_elevation, _ = self.ground_station.elevation_azimuth(pos, gmst)
        
        # === Sensors ===
        
        # Magnetometer
        mag_meas = self.magnetometer.measure(b_field_body_uT)
        
        # Gyroscope
        gyro_meas = self.gyroscope.measure(omega, dt)
        
        # Sun sensor
        sun_meas, sun_visible, _ = self.sun_sensors.measure(sun_dir_body, in_eclipse)
        
        # === Actuators ===
        
        # Update magnetorquers and get torque
        self.magnetorquers.update(dt)
        mag_torque = self.magnetorquers.get_torque(b_field_body)
        
        # Total torque
        total_torque = mag_torque + self.spacecraft.disturbance_torque
        
        # === Dynamics Propagation ===
        
        # Orbital dynamics
        self.spacecraft.orbital_state = self.orbital_dynamics.propagate(
            self.spacecraft.orbital_state, dt, method='rk4'
        )
        
        # Attitude dynamics
        self.spacecraft.attitude_state = self.attitude_dynamics.propagate(
            self.spacecraft.attitude_state, total_torque, dt, method='rk4'
        )
        
        # === Create state record ===
        
        state = SimulationState(
            time_s=self.time.elapsed_seconds,
            position_km=pos.copy(),
            velocity_km_s=vel.copy(),
            quaternion=quat.copy(),
            angular_velocity=omega.copy(),
            mag_field_body_uT=mag_meas.copy(),
            gyro_rate=gyro_meas.copy(),
            sun_direction_body=sun_meas.copy(),
            sun_visible=sun_visible,
            in_eclipse=in_eclipse,
            altitude_km=self.spacecraft.orbital_state.altitude_km,
            gs_visible=gs_visible,
            gs_elevation_deg=gs_elevation
        )
        
        # Log state
        if len(self.history) == 0 or \
           (self.time.elapsed_seconds - self.history[-1].time_s) >= (1.0 / self.config.output_rate_hz):
            self.history.append(state)
        
        # Call callbacks
        for callback in self.step_callbacks:
            callback(self, state)
        
        # Advance time
        self.time.step()
        self.step_count += 1
        
        return state
    
    def run(self, 
            duration_seconds: float = None,
            progress_callback: Callable = None) -> List[SimulationState]:
        """
        Run simulation for specified duration.
        
        Args:
            duration_seconds: Duration (default: config duration)
            progress_callback: Called with progress (0-1)
            
        Returns:
            List of logged states
        """
        duration = duration_seconds or self.config.duration_seconds
        
        self.is_running = True
        
        while self.time.elapsed_seconds < duration:
            self.step()
            
            if progress_callback and self.step_count % 100 == 0:
                progress = self.time.elapsed_seconds / duration
                progress_callback(progress)
        
        self.is_running = False
        
        if self.config.verbose:
            print(f"Simulation complete: {self.step_count} steps, "
                  f"{len(self.history)} logged states")
        
        return self.history
    
    def set_initial_attitude(self, 
                             quaternion: np.ndarray = None,
                             angular_velocity_deg_s: np.ndarray = None):
        """
        Set initial attitude conditions.
        
        Args:
            quaternion: Initial quaternion [w, x, y, z]
            angular_velocity_deg_s: Initial angular velocity [deg/s]
        """
        if quaternion is not None:
            self.spacecraft.set_quaternion(quaternion)
        
        if angular_velocity_deg_s is not None:
            omega_rad = np.radians(angular_velocity_deg_s)
            self.spacecraft.set_angular_velocity(omega_rad)
    
    def set_detumble_initial_conditions(self, 
                                         max_rate_deg_s: float = 10.0):
        """
        Set random tumbling initial conditions for detumble scenario.
        
        Args:
            max_rate_deg_s: Maximum initial angular rate [deg/s]
        """
        # Random quaternion
        u1, u2, u3 = np.random.random(3)
        q = np.array([
            np.sqrt(1-u1) * np.sin(2*np.pi*u2),
            np.sqrt(1-u1) * np.cos(2*np.pi*u2),
            np.sqrt(u1) * np.sin(2*np.pi*u3),
            np.sqrt(u1) * np.cos(2*np.pi*u3)
        ])
        
        # Random angular velocity
        omega = np.random.uniform(-max_rate_deg_s, max_rate_deg_s, 3)
        
        self.set_initial_attitude(q, omega)
    
    def command_magnetorquers(self, dipole_Am2: np.ndarray):
        """Command magnetorquer dipole moment."""
        self.magnetorquers.command(dipole_Am2)
        self.spacecraft.set_magnetorquer_command(dipole_Am2)
    
    def add_step_callback(self, callback: Callable):
        """Add callback to be called each step."""
        self.step_callbacks.append(callback)
    
    def get_telemetry(self) -> Dict:
        """
        Get current telemetry data.
        
        Returns:
            Dictionary of telemetry values
        """
        return {
            'time_s': self.time.elapsed_seconds,
            'orbit_number': self.time.orbit_number(self.config.orbit.period_minutes * 60),
            'altitude_km': self.spacecraft.orbital_state.altitude_km,
            'position_km': self.spacecraft.orbital_state.position_km.tolist(),
            'velocity_km_s': self.spacecraft.orbital_state.velocity_km_s.tolist(),
            'quaternion': self.spacecraft.attitude_state.quaternion.tolist(),
            'euler_deg': self.spacecraft.attitude_state.euler_angles_deg.tolist(),
            'angular_velocity_deg_s': np.degrees(
                self.spacecraft.attitude_state.angular_velocity
            ).tolist(),
        }
    
    def export_trajectory(self, filename: str = None) -> np.ndarray:
        """
        Export trajectory data.
        
        Args:
            filename: Optional CSV filename
            
        Returns:
            Trajectory data array
        """
        if not self.history:
            return np.array([])
        
        data = np.zeros((len(self.history), 17))
        
        for i, state in enumerate(self.history):
            data[i, 0] = state.time_s
            data[i, 1:4] = state.position_km
            data[i, 4:7] = state.velocity_km_s
            data[i, 7:11] = state.quaternion
            data[i, 11:14] = state.angular_velocity
            data[i, 14] = 1.0 if state.in_eclipse else 0.0
            data[i, 15] = state.altitude_km
            data[i, 16] = 1.0 if state.gs_visible else 0.0
        
        if filename:
            header = "time_s,x_km,y_km,z_km,vx_km_s,vy_km_s,vz_km_s," + \
                     "qw,qx,qy,qz,wx,wy,wz,eclipse,altitude_km,gs_visible"
            np.savetxt(filename, data, delimiter=',', header=header)
        
        return data
