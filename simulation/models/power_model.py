"""
Power System Model
==================

Electrical Power System (EPS) simulation.
"""

import numpy as np
from dataclasses import dataclass
from typing import List, Optional


@dataclass
class BatteryConfig:
    """Battery configuration."""
    capacity_Wh: float = 20.0         # 3U typical
    voltage_nominal: float = 7.4      # 2S Li-ion
    voltage_min: float = 6.0
    voltage_max: float = 8.4
    efficiency_charge: float = 0.95
    efficiency_discharge: float = 0.95
    initial_soc: float = 0.8          # State of charge 0-1


@dataclass
class PowerBudget:
    """Power consumption budget by subsystem."""
    eps_W: float = 0.5
    obc_W: float = 1.0
    comms_idle_W: float = 0.5
    comms_tx_W: float = 5.0
    adcs_W: float = 1.5
    payload_idle_W: float = 0.5
    payload_active_W: float = 3.0


class PowerModel:
    """
    Electrical Power System model.
    
    Simulates:
    - Solar power generation
    - Battery charge/discharge
    - Power budget and margins
    """
    
    def __init__(self, battery_config: BatteryConfig = None,
                 power_budget: PowerBudget = None):
        """
        Initialize power model.
        
        Args:
            battery_config: Battery configuration
            power_budget: Power consumption budget
        """
        self.battery = battery_config or BatteryConfig()
        self.budget = power_budget or PowerBudget()
        
        # State
        self.soc = self.battery.initial_soc  # State of charge 0-1
        self.voltage = self._soc_to_voltage(self.soc)
        
        # Current mode
        self.comms_transmitting = False
        self.payload_active = False
        
        # Statistics
        self.total_energy_generated_Wh = 0.0
        self.total_energy_consumed_Wh = 0.0
        self.min_soc = 1.0
        self.max_soc = 0.0
    
    def _soc_to_voltage(self, soc: float) -> float:
        """Convert SOC to voltage (simplified linear model)."""
        return self.battery.voltage_min + soc * (
            self.battery.voltage_max - self.battery.voltage_min)
    
    def _voltage_to_soc(self, voltage: float) -> float:
        """Convert voltage to SOC."""
        soc = (voltage - self.battery.voltage_min) / (
            self.battery.voltage_max - self.battery.voltage_min)
        return np.clip(soc, 0, 1)
    
    def get_load_power(self) -> float:
        """
        Calculate current total load power.
        
        Returns:
            Total power consumption in Watts
        """
        power = (self.budget.eps_W + 
                 self.budget.obc_W + 
                 self.budget.adcs_W)
        
        if self.comms_transmitting:
            power += self.budget.comms_tx_W
        else:
            power += self.budget.comms_idle_W
        
        if self.payload_active:
            power += self.budget.payload_active_W
        else:
            power += self.budget.payload_idle_W
        
        return power
    
    def update(self, dt: float, solar_power: float, in_eclipse: bool) -> dict:
        """
        Update power system state.
        
        Args:
            dt: Time step in seconds
            solar_power: Generated solar power in Watts
            in_eclipse: Whether spacecraft is in eclipse
            
        Returns:
            Power system status dictionary
        """
        # Zero solar power in eclipse
        if in_eclipse:
            solar_power = 0.0
        
        load_power = self.get_load_power()
        
        # Net power (positive = charging)
        net_power = solar_power - load_power
        
        # Energy delta
        dt_hours = dt / 3600.0
        
        if net_power > 0:
            # Charging
            energy_in = net_power * dt_hours * self.battery.efficiency_charge
            self.soc += energy_in / self.battery.capacity_Wh
            self.total_energy_generated_Wh += solar_power * dt_hours
        else:
            # Discharging
            energy_out = abs(net_power) * dt_hours / self.battery.efficiency_discharge
            self.soc -= energy_out / self.battery.capacity_Wh
        
        # Clamp SOC
        self.soc = np.clip(self.soc, 0, 1)
        
        # Update voltage
        self.voltage = self._soc_to_voltage(self.soc)
        
        # Track consumption
        self.total_energy_consumed_Wh += load_power * dt_hours
        
        # Track statistics
        self.min_soc = min(self.min_soc, self.soc)
        self.max_soc = max(self.max_soc, self.soc)
        
        return {
            'soc': self.soc,
            'voltage': self.voltage,
            'solar_power_W': solar_power,
            'load_power_W': load_power,
            'net_power_W': net_power,
            'in_eclipse': in_eclipse,
        }
    
    def set_mode(self, comms_tx: bool = None, payload_active: bool = None):
        """Set operational mode."""
        if comms_tx is not None:
            self.comms_transmitting = comms_tx
        if payload_active is not None:
            self.payload_active = payload_active
    
    def get_remaining_energy(self) -> float:
        """Get remaining battery energy in Wh."""
        return self.soc * self.battery.capacity_Wh
    
    def get_time_to_empty(self) -> Optional[float]:
        """
        Estimate time until battery depletion.
        
        Returns:
            Time in hours, or None if charging
        """
        load = self.get_load_power()
        remaining = self.get_remaining_energy()
        
        if load > 0:
            return remaining / load
        return None
    
    def is_low_power(self, threshold: float = 0.2) -> bool:
        """Check if in low power condition."""
        return self.soc < threshold
    
    def get_statistics(self) -> dict:
        """Get power system statistics."""
        return {
            'soc': self.soc,
            'soc_percent': self.soc * 100,
            'voltage': self.voltage,
            'remaining_Wh': self.get_remaining_energy(),
            'min_soc_percent': self.min_soc * 100,
            'max_soc_percent': self.max_soc * 100,
            'total_generated_Wh': self.total_energy_generated_Wh,
            'total_consumed_Wh': self.total_energy_consumed_Wh,
            'low_power': self.is_low_power(),
        }
