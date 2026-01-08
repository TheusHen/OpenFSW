"""
Numerical Integrators
=====================

Integration methods for dynamics simulation.
"""

import numpy as np
from typing import Callable, Tuple


class RK4Integrator:
    """
    4th order Runge-Kutta integrator.
    
    Classic fixed-step RK4 method for ODEs.
    """
    
    def __init__(self, derivative_func: Callable[[float, np.ndarray], np.ndarray]):
        """
        Initialize integrator.
        
        Args:
            derivative_func: Function f(t, y) returning dy/dt
        """
        self.derivative = derivative_func
    
    def step(self, t: float, y: np.ndarray, dt: float) -> np.ndarray:
        """
        Perform single RK4 step.
        
        Args:
            t: Current time
            y: Current state
            dt: Time step
            
        Returns:
            New state after step
        """
        k1 = self.derivative(t, y)
        k2 = self.derivative(t + 0.5*dt, y + 0.5*dt*k1)
        k3 = self.derivative(t + 0.5*dt, y + 0.5*dt*k2)
        k4 = self.derivative(t + dt, y + dt*k3)
        
        return y + (dt/6) * (k1 + 2*k2 + 2*k3 + k4)
    
    def integrate(self, 
                  t0: float, 
                  y0: np.ndarray, 
                  t_end: float, 
                  dt: float) -> Tuple[np.ndarray, np.ndarray]:
        """
        Integrate from t0 to t_end.
        
        Args:
            t0: Initial time
            y0: Initial state
            t_end: Final time
            dt: Time step
            
        Returns:
            Tuple of (times, states)
        """
        n_steps = int((t_end - t0) / dt) + 1
        
        times = np.zeros(n_steps)
        states = np.zeros((n_steps, len(y0)))
        
        times[0] = t0
        states[0] = y0
        
        t = t0
        y = y0.copy()
        
        for i in range(1, n_steps):
            y = self.step(t, y, dt)
            t += dt
            times[i] = t
            states[i] = y
        
        return times, states


class RK45Integrator:
    """
    Runge-Kutta-Fehlberg 4(5) adaptive step integrator.
    
    Embedded RK method with error estimation for step control.
    """
    
    # Butcher tableau coefficients
    A = np.array([0, 1/4, 3/8, 12/13, 1, 1/2])
    B = np.array([
        [0, 0, 0, 0, 0],
        [1/4, 0, 0, 0, 0],
        [3/32, 9/32, 0, 0, 0],
        [1932/2197, -7200/2197, 7296/2197, 0, 0],
        [439/216, -8, 3680/513, -845/4104, 0],
        [-8/27, 2, -3544/2565, 1859/4104, -11/40]
    ])
    C4 = np.array([25/216, 0, 1408/2565, 2197/4104, -1/5, 0])
    C5 = np.array([16/135, 0, 6656/12825, 28561/56430, -9/50, 2/55])
    
    def __init__(self, 
                 derivative_func: Callable[[float, np.ndarray], np.ndarray],
                 rtol: float = 1e-6,
                 atol: float = 1e-9,
                 dt_min: float = 1e-10,
                 dt_max: float = 10.0):
        """
        Initialize adaptive integrator.
        
        Args:
            derivative_func: Function f(t, y) returning dy/dt
            rtol: Relative tolerance
            atol: Absolute tolerance
            dt_min: Minimum time step
            dt_max: Maximum time step
        """
        self.derivative = derivative_func
        self.rtol = rtol
        self.atol = atol
        self.dt_min = dt_min
        self.dt_max = dt_max
    
    def step(self, t: float, y: np.ndarray, dt: float) -> Tuple[np.ndarray, float, float]:
        """
        Perform adaptive RK45 step.
        
        Args:
            t: Current time
            y: Current state
            dt: Proposed time step
            
        Returns:
            Tuple of (new_state, actual_dt, error_estimate)
        """
        # Compute k values
        k = np.zeros((6, len(y)))
        k[0] = self.derivative(t, y)
        
        for i in range(1, 6):
            y_temp = y + dt * np.sum(self.B[i, :i, np.newaxis] * k[:i], axis=0)
            k[i] = self.derivative(t + self.A[i] * dt, y_temp)
        
        # 4th and 5th order solutions
        y4 = y + dt * np.sum(self.C4[:, np.newaxis] * k, axis=0)
        y5 = y + dt * np.sum(self.C5[:, np.newaxis] * k, axis=0)
        
        # Error estimate
        error = np.linalg.norm(y5 - y4)
        
        return y5, dt, error
    
    def integrate(self,
                  t0: float,
                  y0: np.ndarray,
                  t_end: float,
                  dt_initial: float = 0.01) -> Tuple[np.ndarray, np.ndarray]:
        """
        Integrate with adaptive stepping.
        
        Args:
            t0: Initial time
            y0: Initial state
            t_end: Final time
            dt_initial: Initial time step guess
            
        Returns:
            Tuple of (times, states)
        """
        times = [t0]
        states = [y0.copy()]
        
        t = t0
        y = y0.copy()
        dt = dt_initial
        
        while t < t_end:
            # Don't overshoot end time
            if t + dt > t_end:
                dt = t_end - t
            
            y_new, _, error = self.step(t, y, dt)
            
            # Tolerance check
            tol = self.atol + self.rtol * max(np.linalg.norm(y), np.linalg.norm(y_new))
            
            if error <= tol:
                # Accept step
                t += dt
                y = y_new
                times.append(t)
                states.append(y.copy())
                
                # Increase step size
                if error > 0:
                    factor = 0.9 * (tol / error) ** 0.2
                else:
                    factor = 2.0
                dt = min(dt * factor, self.dt_max)
            else:
                # Reject step, decrease dt
                factor = 0.9 * (tol / error) ** 0.25
                dt = max(dt * factor, self.dt_min)
        
        return np.array(times), np.array(states)


class SymplecticEuler:
    """
    Symplectic Euler integrator for Hamiltonian systems.
    
    Preserves phase space volume (important for long-term orbital dynamics).
    """
    
    def __init__(self,
                 velocity_func: Callable[[np.ndarray], np.ndarray],
                 acceleration_func: Callable[[np.ndarray], np.ndarray]):
        """
        Initialize symplectic integrator.
        
        Args:
            velocity_func: v = dr/dt
            acceleration_func: a = dv/dt = f(r)
        """
        self.velocity = velocity_func
        self.acceleration = acceleration_func
    
    def step(self, r: np.ndarray, v: np.ndarray, dt: float) -> Tuple[np.ndarray, np.ndarray]:
        """
        Perform symplectic Euler step.
        
        Args:
            r: Position
            v: Velocity
            dt: Time step
            
        Returns:
            Tuple of (new_position, new_velocity)
        """
        # Semi-implicit: update velocity first, then position
        v_new = v + self.acceleration(r) * dt
        r_new = r + v_new * dt
        
        return r_new, v_new
