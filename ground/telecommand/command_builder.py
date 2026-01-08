"""
Command Builder
===============

High-level command building interface.
"""

import time
from dataclasses import dataclass
from typing import Optional, List, Dict, Callable
from enum import IntEnum

from .packet_encoder import CCSDSEncoder, CommandFactory


class SpacecraftMode(IntEnum):
    """Spacecraft operational modes."""
    SAFE = 0
    IDLE = 1
    NOMINAL = 2
    SCIENCE = 3
    DOWNLINK = 4


class HKStructureID(IntEnum):
    """Housekeeping structure IDs."""
    SYSTEM = 0x0001
    POWER = 0x0002
    ADCS = 0x0003
    COMMS = 0x0004
    THERMAL = 0x0005
    PAYLOAD = 0x0006


@dataclass
class CommandResult:
    """Result of command generation."""
    success: bool
    packet: bytes
    description: str
    sequence_number: int
    timestamp: float


class CommandBuilder:
    """
    High-level command builder.
    
    Provides a user-friendly interface for building telecommands.
    """
    
    def __init__(self, apid: int = 100):
        """
        Initialize command builder.
        
        Args:
            apid: Application Process ID
        """
        from .packet_encoder import TCPacketConfig
        
        config = TCPacketConfig(apid=apid)
        self.encoder = CCSDSEncoder(config)
        self.factory = CommandFactory(self.encoder)
        
        # Command history
        self._history: List[CommandResult] = []
        
        # Validation callbacks
        self._validators: List[Callable[[bytes], bool]] = []
    
    def ping(self) -> CommandResult:
        """
        Create ping command.
        
        Returns:
            Command result
        """
        packet = self.factory.create_ping()
        return self._record_command(packet, "PING (TC 17,1)")
    
    def change_mode(self, mode: SpacecraftMode) -> CommandResult:
        """
        Create mode change command.
        
        Args:
            mode: Target spacecraft mode
            
        Returns:
            Command result
        """
        packet = self.factory.create_mode_change(mode.value)
        return self._record_command(packet, f"MODE_CHANGE to {mode.name}")
    
    def enable_housekeeping(self, hk_id: HKStructureID, 
                            interval_seconds: float = 10.0) -> CommandResult:
        """
        Enable periodic housekeeping.
        
        Args:
            hk_id: Housekeeping structure ID
            interval_seconds: Reporting interval
            
        Returns:
            Command result
        """
        interval_ms = int(interval_seconds * 1000)
        packet = self.factory.create_enable_hk(hk_id.value, interval_ms)
        return self._record_command(
            packet, 
            f"ENABLE_HK {hk_id.name} @ {interval_seconds}s"
        )
    
    def disable_housekeeping(self, hk_id: HKStructureID) -> CommandResult:
        """
        Disable housekeeping.
        
        Args:
            hk_id: Housekeeping structure ID
            
        Returns:
            Command result
        """
        packet = self.factory.create_disable_hk(hk_id.value)
        return self._record_command(packet, f"DISABLE_HK {hk_id.name}")
    
    def sync_time(self, timestamp: Optional[float] = None) -> CommandResult:
        """
        Synchronize spacecraft time.
        
        Args:
            timestamp: Unix timestamp (default: current time)
            
        Returns:
            Command result
        """
        if timestamp is None:
            timestamp = time.time()
        
        seconds = int(timestamp)
        subseconds = int((timestamp - seconds) * 65536)
        
        packet = self.factory.create_time_sync(seconds, subseconds)
        return self._record_command(
            packet, 
            f"TIME_SYNC to {seconds}.{subseconds:04X}"
        )
    
    def reset_spacecraft(self, cold: bool = False) -> CommandResult:
        """
        Reset spacecraft.
        
        Args:
            cold: If True, perform cold reset
            
        Returns:
            Command result
        """
        reset_type = 1 if cold else 0
        packet = self.factory.create_reset(reset_type)
        reset_str = "COLD" if cold else "WARM"
        return self._record_command(packet, f"RESET ({reset_str})")
    
    def read_memory(self, address: int, length: int) -> CommandResult:
        """
        Request memory dump.
        
        Args:
            address: Memory address
            length: Number of bytes
            
        Returns:
            Command result
        """
        packet = self.factory.create_memory_read(address, length)
        return self._record_command(
            packet, 
            f"MEM_READ 0x{address:08X} ({length} bytes)"
        )
    
    def raw_command(self, service: int, subtype: int, 
                    data: bytes = b'') -> CommandResult:
        """
        Create raw PUS command.
        
        Args:
            service: PUS service type
            subtype: PUS service subtype
            data: Command data
            
        Returns:
            Command result
        """
        packet = self.encoder.encode_packet(service, subtype, data)
        return self._record_command(
            packet, 
            f"RAW TC({service},{subtype}) [{len(data)} bytes]"
        )
    
    def _record_command(self, packet: bytes, description: str) -> CommandResult:
        """Record command in history."""
        # Validate if validators registered
        valid = all(v(packet) for v in self._validators) if self._validators else True
        
        result = CommandResult(
            success=valid,
            packet=packet,
            description=description,
            sequence_number=self.encoder.get_sequence_count() - 1,
            timestamp=time.time(),
        )
        
        self._history.append(result)
        return result
    
    def add_validator(self, validator: Callable[[bytes], bool]):
        """Add packet validation callback."""
        self._validators.append(validator)
    
    def get_history(self, count: int = 10) -> List[CommandResult]:
        """Get command history."""
        return self._history[-count:]
    
    def clear_history(self):
        """Clear command history."""
        self._history.clear()
    
    def get_statistics(self) -> Dict:
        """Get command statistics."""
        return {
            'total_commands': len(self._history),
            'sequence_number': self.encoder.get_sequence_count(),
            'success_count': sum(1 for c in self._history if c.success),
            'failure_count': sum(1 for c in self._history if not c.success),
        }
