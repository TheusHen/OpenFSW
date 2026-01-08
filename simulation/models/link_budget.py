"""
Link Budget Model
=================

RF link budget calculations for communication analysis.
"""

import numpy as np
from dataclasses import dataclass
from typing import Dict


@dataclass
class TransmitterConfig:
    """Transmitter configuration."""
    power_dBm: float = 30.0        # 1W = 30 dBm
    antenna_gain_dBi: float = 2.0  # Dipole/patch
    frequency_MHz: float = 437.0   # UHF amateur
    data_rate_bps: float = 9600.0
    modulation: str = 'GMSK'
    losses_dB: float = 2.0         # Cable/connector losses


@dataclass
class ReceiverConfig:
    """Ground station receiver configuration."""
    antenna_gain_dBi: float = 12.0   # Yagi
    noise_figure_dB: float = 1.5
    system_temp_K: float = 290.0
    implementation_loss_dB: float = 2.0
    required_ebno_dB: float = 10.0   # For target BER


class LinkBudget:
    """
    RF link budget calculator.
    
    Calculates:
    - Free space path loss
    - Received power
    - SNR and link margin
    """
    
    SPEED_OF_LIGHT = 299792458.0  # m/s
    BOLTZMANN = 1.38e-23  # J/K
    
    def __init__(self, tx: TransmitterConfig = None, 
                 rx: ReceiverConfig = None):
        """
        Initialize link budget calculator.
        
        Args:
            tx: Transmitter configuration
            rx: Receiver configuration
        """
        self.tx = tx or TransmitterConfig()
        self.rx = rx or ReceiverConfig()
        
        # Calculate wavelength
        self.wavelength = self.SPEED_OF_LIGHT / (self.tx.frequency_MHz * 1e6)
    
    def calculate_fspl(self, distance_km: float) -> float:
        """
        Calculate Free Space Path Loss.
        
        Args:
            distance_km: Distance in kilometers
            
        Returns:
            FSPL in dB
        """
        distance_m = distance_km * 1000
        
        # FSPL = 20*log10(4*pi*d/lambda)
        fspl = 20 * np.log10(4 * np.pi * distance_m / self.wavelength)
        
        return fspl
    
    def calculate_link(self, distance_km: float, 
                       elevation_deg: float) -> Dict:
        """
        Calculate complete link budget.
        
        Args:
            distance_km: Slant range in kilometers
            elevation_deg: Ground station elevation angle
            
        Returns:
            Link budget analysis dictionary
        """
        # EIRP (Effective Isotropic Radiated Power)
        eirp_dBm = (self.tx.power_dBm + 
                   self.tx.antenna_gain_dBi - 
                   self.tx.losses_dB)
        
        # Free space path loss
        fspl = self.calculate_fspl(distance_km)
        
        # Atmospheric loss (simplified, varies with elevation)
        if elevation_deg < 10:
            atm_loss = 2.0
        elif elevation_deg < 30:
            atm_loss = 0.5
        else:
            atm_loss = 0.2
        
        # Polarization loss
        pol_loss = 3.0  # Assumes some mismatch
        
        # Received power
        rx_power_dBm = (eirp_dBm - 
                       fspl - 
                       atm_loss - 
                       pol_loss + 
                       self.rx.antenna_gain_dBi - 
                       self.rx.implementation_loss_dB)
        
        # Noise power
        bandwidth = self.tx.data_rate_bps  # Approximate
        noise_power_dBm = (10 * np.log10(self.BOLTZMANN * 
                          self.rx.system_temp_K * bandwidth) + 30 +
                          self.rx.noise_figure_dB)
        
        # SNR
        snr_dB = rx_power_dBm - noise_power_dBm
        
        # Eb/N0 (for digital modulation)
        ebno_dB = snr_dB + 10 * np.log10(bandwidth / self.tx.data_rate_bps)
        
        # Link margin
        margin_dB = ebno_dB - self.rx.required_ebno_dB
        
        return {
            'distance_km': distance_km,
            'elevation_deg': elevation_deg,
            'eirp_dBm': eirp_dBm,
            'fspl_dB': fspl,
            'atmospheric_loss_dB': atm_loss,
            'polarization_loss_dB': pol_loss,
            'rx_power_dBm': rx_power_dBm,
            'noise_power_dBm': noise_power_dBm,
            'snr_dB': snr_dB,
            'ebno_dB': ebno_dB,
            'margin_dB': margin_dB,
            'link_closed': margin_dB > 0,
        }
    
    def calculate_max_range(self, min_margin_dB: float = 3.0) -> float:
        """
        Calculate maximum range for link closure.
        
        Args:
            min_margin_dB: Minimum required margin
            
        Returns:
            Maximum range in km
        """
        # Binary search for max range
        low, high = 100.0, 10000.0
        
        while high - low > 10:
            mid = (low + high) / 2
            result = self.calculate_link(mid, elevation_deg=10)
            
            if result['margin_dB'] > min_margin_dB:
                low = mid
            else:
                high = mid
        
        return low
    
    def get_data_volume(self, pass_duration_s: float, 
                        efficiency: float = 0.7) -> float:
        """
        Calculate data volume for a pass.
        
        Args:
            pass_duration_s: Pass duration in seconds
            efficiency: Protocol efficiency factor
            
        Returns:
            Data volume in kilobytes
        """
        bits = self.tx.data_rate_bps * pass_duration_s * efficiency
        return bits / 8 / 1024  # Convert to KB
    
    def print_budget(self, distance_km: float, elevation_deg: float):
        """Print formatted link budget."""
        result = self.calculate_link(distance_km, elevation_deg)
        
        status = "✓ CLOSED" if result['link_closed'] else "✗ OPEN"
        
        print(f"""
Link Budget Analysis
====================
Distance: {distance_km:.1f} km
Elevation: {elevation_deg:.1f}°
Frequency: {self.tx.frequency_MHz} MHz
Data Rate: {self.tx.data_rate_bps} bps

Transmitter:
  Power: {self.tx.power_dBm:.1f} dBm
  Antenna Gain: {self.tx.antenna_gain_dBi:.1f} dBi
  EIRP: {result['eirp_dBm']:.1f} dBm

Path:
  FSPL: {result['fspl_dB']:.1f} dB
  Atmospheric: {result['atmospheric_loss_dB']:.1f} dB
  Polarization: {result['polarization_loss_dB']:.1f} dB

Receiver:
  Antenna Gain: {self.rx.antenna_gain_dBi:.1f} dBi
  Rx Power: {result['rx_power_dBm']:.1f} dBm
  Noise Power: {result['noise_power_dBm']:.1f} dBm

Performance:
  SNR: {result['snr_dB']:.1f} dB
  Eb/N0: {result['ebno_dB']:.1f} dB
  Required Eb/N0: {self.rx.required_ebno_dB:.1f} dB
  Margin: {result['margin_dB']:.1f} dB

Result: {status}
""")
