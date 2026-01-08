"""
Simulation Time Manager
=======================

Time management for the simulation framework.
Handles epoch, elapsed time, and time conversions.
"""

import numpy as np
from datetime import datetime, timedelta
from typing import Optional


class SimulationTime:
    """
    Manages simulation time.
    
    Provides:
    - Epoch and elapsed time tracking
    - Julian date conversions
    - UTC/TAI/GPS time support
    - Time step management
    """
    
    # Time system constants
    TAI_UTC_OFFSET = 37  # seconds (as of 2017, update as needed)
    GPS_TAI_OFFSET = 19  # seconds
    J2000_EPOCH = datetime(2000, 1, 1, 12, 0, 0)  # J2000 epoch
    
    def __init__(self, 
                 start_time: datetime = None,
                 time_step: float = 0.1):
        """
        Initialize simulation time.
        
        Args:
            start_time: Simulation start time (UTC)
            time_step: Time step in seconds
        """
        self.start_time = start_time or datetime(2026, 1, 8, 0, 0, 0)
        self.time_step = time_step
        self.elapsed_seconds = 0.0
        self.step_count = 0
        
    def reset(self):
        """Reset simulation time to start."""
        self.elapsed_seconds = 0.0
        self.step_count = 0
    
    def step(self) -> float:
        """
        Advance time by one step.
        
        Returns:
            Current elapsed time in seconds
        """
        self.elapsed_seconds += self.time_step
        self.step_count += 1
        return self.elapsed_seconds
    
    def set_time(self, elapsed_seconds: float):
        """Set elapsed time directly."""
        self.elapsed_seconds = elapsed_seconds
        self.step_count = int(elapsed_seconds / self.time_step)
    
    @property
    def current_utc(self) -> datetime:
        """Get current UTC time."""
        return self.start_time + timedelta(seconds=self.elapsed_seconds)
    
    @property
    def current_tai(self) -> datetime:
        """Get current TAI time (atomic time)."""
        return self.current_utc + timedelta(seconds=self.TAI_UTC_OFFSET)
    
    @property
    def current_gps(self) -> datetime:
        """Get current GPS time."""
        return self.current_tai - timedelta(seconds=self.GPS_TAI_OFFSET)
    
    @property
    def julian_date(self) -> float:
        """
        Get Julian Date for current time.
        
        Returns:
            Julian Date as float
        """
        return self.datetime_to_jd(self.current_utc)
    
    @property
    def modified_julian_date(self) -> float:
        """Get Modified Julian Date (MJD = JD - 2400000.5)."""
        return self.julian_date - 2400000.5
    
    @property
    def j2000_seconds(self) -> float:
        """Get seconds since J2000 epoch."""
        delta = self.current_utc - self.J2000_EPOCH
        return delta.total_seconds()
    
    @staticmethod
    def datetime_to_jd(dt: datetime) -> float:
        """
        Convert datetime to Julian Date.
        
        Args:
            dt: datetime object
            
        Returns:
            Julian Date
        """
        year = dt.year
        month = dt.month
        day = dt.day
        hour = dt.hour
        minute = dt.minute
        second = dt.second + dt.microsecond / 1e6
        
        if month <= 2:
            year -= 1
            month += 12
        
        A = int(year / 100)
        B = 2 - A + int(A / 4)
        
        jd = int(365.25 * (year + 4716)) + \
             int(30.6001 * (month + 1)) + \
             day + B - 1524.5 + \
             (hour + minute / 60 + second / 3600) / 24
        
        return jd
    
    @staticmethod
    def jd_to_datetime(jd: float) -> datetime:
        """
        Convert Julian Date to datetime.
        
        Args:
            jd: Julian Date
            
        Returns:
            datetime object
        """
        Z = int(jd + 0.5)
        F = jd + 0.5 - Z
        
        if Z < 2299161:
            A = Z
        else:
            alpha = int((Z - 1867216.25) / 36524.25)
            A = Z + 1 + alpha - int(alpha / 4)
        
        B = A + 1524
        C = int((B - 122.1) / 365.25)
        D = int(365.25 * C)
        E = int((B - D) / 30.6001)
        
        day = B - D - int(30.6001 * E) + F
        
        if E < 14:
            month = E - 1
        else:
            month = E - 13
            
        if month > 2:
            year = C - 4716
        else:
            year = C - 4715
        
        day_int = int(day)
        frac = day - day_int
        hour = int(frac * 24)
        frac = frac * 24 - hour
        minute = int(frac * 60)
        frac = frac * 60 - minute
        second = int(frac * 60)
        microsecond = int((frac * 60 - second) * 1e6)
        
        return datetime(year, month, day_int, hour, minute, second, microsecond)
    
    def gmst(self) -> float:
        """
        Calculate Greenwich Mean Sidereal Time.
        
        Returns:
            GMST in radians
        """
        jd = self.julian_date
        t = (jd - 2451545.0) / 36525.0  # Julian centuries since J2000
        
        # GMST in seconds at 0h UT
        gmst_sec = 24110.54841 + \
                   8640184.812866 * t + \
                   0.093104 * t**2 - \
                   6.2e-6 * t**3
        
        # Add rotation for time of day
        ut1_frac = (jd - int(jd) - 0.5) % 1.0
        gmst_sec += 86400.0 * 1.00273790935 * ut1_frac
        
        # Convert to radians
        gmst_rad = (gmst_sec / 86400.0 * 2 * np.pi) % (2 * np.pi)
        
        return gmst_rad
    
    def orbit_number(self, period_seconds: float) -> int:
        """
        Calculate current orbit number.
        
        Args:
            period_seconds: Orbital period in seconds
            
        Returns:
            Current orbit number (starting from 1)
        """
        return int(self.elapsed_seconds / period_seconds) + 1
    
    def orbit_phase(self, period_seconds: float) -> float:
        """
        Calculate phase within current orbit.
        
        Args:
            period_seconds: Orbital period in seconds
            
        Returns:
            Phase as fraction (0.0 to 1.0)
        """
        return (self.elapsed_seconds % period_seconds) / period_seconds
    
    def __repr__(self) -> str:
        return f"SimulationTime(utc={self.current_utc}, elapsed={self.elapsed_seconds:.3f}s)"
