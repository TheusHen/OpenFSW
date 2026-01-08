"""
Simulation Configuration
========================

Mission and simulation parameters for OpenFSW-LEO-3U.
"""

import numpy as np
from dataclasses import dataclass, field
from typing import Optional
from datetime import datetime


@dataclass
class OrbitalParameters:
    """Orbital elements for the mission."""
    semi_major_axis_km: float = 6878.0  # 500km altitude + Earth radius
    eccentricity: float = 0.001  # Near-circular
    inclination_deg: float = 97.0  # Sun-synchronous
    raan_deg: float = 0.0  # Right ascension of ascending node
    arg_perigee_deg: float = 0.0  # Argument of perigee
    true_anomaly_deg: float = 0.0  # Initial true anomaly
    
    @property
    def altitude_km(self) -> float:
        """Approximate altitude above Earth."""
        return self.semi_major_axis_km - 6378.0
    
    @property
    def period_minutes(self) -> float:
        """Orbital period using Kepler's third law."""
        mu = 398600.4418  # km³/s²
        a = self.semi_major_axis_km
        return 2 * np.pi * np.sqrt(a**3 / mu) / 60.0


@dataclass
class SpacecraftParameters:
    """Physical properties of the spacecraft."""
    # Mass properties
    mass_kg: float = 4.0  # 3U CubeSat typical mass
    
    # Dimensions (3U CubeSat: 10x10x34 cm)
    length_x_m: float = 0.10
    length_y_m: float = 0.10
    length_z_m: float = 0.34
    
    # Moments of inertia (kg·m²)
    inertia_xx: float = 0.008  # About X axis
    inertia_yy: float = 0.008  # About Y axis
    inertia_zz: float = 0.002  # About Z axis (spin axis)
    
    # Products of inertia (assumed zero for symmetric body)
    inertia_xy: float = 0.0
    inertia_xz: float = 0.0
    inertia_yz: float = 0.0
    
    @property
    def inertia_matrix(self) -> np.ndarray:
        """Return the 3x3 inertia tensor."""
        return np.array([
            [self.inertia_xx, -self.inertia_xy, -self.inertia_xz],
            [-self.inertia_xy, self.inertia_yy, -self.inertia_yz],
            [-self.inertia_xz, -self.inertia_yz, self.inertia_zz]
        ])


@dataclass
class SensorParameters:
    """Sensor configuration and noise parameters."""
    # Magnetometer
    mag_noise_std_uT: float = 0.5  # Standard deviation
    mag_bias_uT: np.ndarray = field(default_factory=lambda: np.array([0.0, 0.0, 0.0]))
    mag_sample_rate_hz: float = 10.0
    
    # Gyroscope
    gyro_noise_std_rad_s: float = 0.001  # ARW
    gyro_bias_rad_s: np.ndarray = field(default_factory=lambda: np.array([0.0, 0.0, 0.0]))
    gyro_bias_instability_rad_s: float = 0.0001
    gyro_sample_rate_hz: float = 100.0
    
    # Sun sensor
    sun_noise_std_deg: float = 1.0  # Accuracy
    sun_fov_deg: float = 120.0  # Field of view
    sun_sample_rate_hz: float = 5.0


@dataclass
class ActuatorParameters:
    """Actuator configuration."""
    # Magnetorquers
    mtq_max_dipole_Am2: float = 0.2  # Maximum magnetic dipole
    mtq_residual_dipole_Am2: float = 0.001  # Residual dipole
    mtq_rise_time_ms: float = 50.0  # Response time
    
    # Reaction wheels (optional for 3U)
    rw_max_torque_Nm: float = 0.001  # Maximum torque
    rw_max_momentum_Nms: float = 0.01  # Maximum momentum
    rw_friction_Nm: float = 0.00001  # Static friction


@dataclass
class GroundStationParameters:
    """Ground station configuration."""
    name: str = "OpenFSW-GS"
    latitude_deg: float = -23.55  # São Paulo, Brazil
    longitude_deg: float = -46.63
    altitude_m: float = 760.0
    min_elevation_deg: float = 10.0  # Minimum elevation for contact


@dataclass 
class SimulationConfig:
    """Complete simulation configuration."""
    # Mission name
    mission_name: str = "OpenFSW-LEO-3U"
    
    # Simulation timing
    start_time: datetime = field(default_factory=lambda: datetime(2026, 1, 8, 0, 0, 0))
    duration_seconds: float = 5700.0  # One orbit (~95 minutes)
    time_step_seconds: float = 0.1  # 10 Hz simulation
    
    # Component configurations
    orbit: OrbitalParameters = field(default_factory=OrbitalParameters)
    spacecraft: SpacecraftParameters = field(default_factory=SpacecraftParameters)
    sensors: SensorParameters = field(default_factory=SensorParameters)
    actuators: ActuatorParameters = field(default_factory=ActuatorParameters)
    ground_station: GroundStationParameters = field(default_factory=GroundStationParameters)
    
    # Simulation options
    enable_j2_perturbation: bool = True
    enable_atmospheric_drag: bool = False  # Simplified for 500km
    enable_solar_radiation_pressure: bool = False
    enable_gravity_gradient: bool = True
    
    # Output options
    output_rate_hz: float = 1.0  # Telemetry output rate
    save_trajectory: bool = True
    verbose: bool = True
    
    def __post_init__(self):
        """Validate configuration."""
        assert self.time_step_seconds > 0, "Time step must be positive"
        assert self.duration_seconds > 0, "Duration must be positive"
        assert self.orbit.altitude_km > 200, "Altitude too low"
        assert self.orbit.altitude_km < 2000, "Altitude too high for LEO"


# Pre-defined configurations
def create_nominal_config() -> SimulationConfig:
    """Create configuration for nominal mission scenario."""
    return SimulationConfig(
        duration_seconds=5700.0,  # One orbit
        time_step_seconds=0.1,
    )


def create_detumble_config() -> SimulationConfig:
    """Create configuration for detumble scenario with high initial rates."""
    config = SimulationConfig(
        duration_seconds=3600.0,  # 1 hour
        time_step_seconds=0.1,
    )
    return config


def create_eclipse_config() -> SimulationConfig:
    """Create configuration to simulate eclipse conditions."""
    config = SimulationConfig(
        duration_seconds=11400.0,  # 2 orbits
        time_step_seconds=0.1,
    )
    return config


def create_safe_mode_config() -> SimulationConfig:
    """Create configuration for safe mode testing."""
    config = SimulationConfig(
        duration_seconds=5700.0,
        time_step_seconds=0.1,
    )
    return config
