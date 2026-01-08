"""
CCSDS Packet Encoder
====================

Encodes telecommand packets in CCSDS/PUS format.
"""

import struct
from dataclasses import dataclass
from typing import Optional
from enum import IntEnum


class TCService(IntEnum):
    """PUS telecommand service types."""
    HOUSEKEEPING = 3
    FUNCTION_MANAGEMENT = 8
    TIME_MANAGEMENT = 9
    TEST = 17
    MODE_MANAGEMENT = 200  # Custom service


@dataclass
class TCPacketConfig:
    """Telecommand packet configuration."""
    apid: int = 100
    sequence_count: int = 0
    destination_id: int = 0
    ack_flags: int = 0x0F  # All acknowledgements


class CCSDSEncoder:
    """
    CCSDS telecommand packet encoder.
    
    Creates properly formatted CCSDS Space Packets with PUS headers.
    """
    
    SYNC_PATTERN = bytes([0x1A, 0xCF, 0xFC, 0x1D])
    
    def __init__(self, config: TCPacketConfig = None):
        """
        Initialize encoder.
        
        Args:
            config: Packet configuration
        """
        self.config = config or TCPacketConfig()
        self._sequence_counter = 0
    
    def encode_packet(self, service_type: int, service_subtype: int,
                      data: bytes = b'', 
                      include_sync: bool = False) -> bytes:
        """
        Encode a complete telecommand packet.
        
        Args:
            service_type: PUS service type
            service_subtype: PUS service subtype
            data: User data
            include_sync: Whether to include sync pattern
            
        Returns:
            Encoded packet bytes
        """
        # Build PUS secondary header (10 bytes for TC)
        secondary_header = self._build_secondary_header(
            service_type, service_subtype)
        
        # Combine secondary header and data
        packet_data = secondary_header + data
        
        # Calculate packet data length (data + CRC - 1)
        packet_data_length = len(packet_data) + 2 - 1  # +2 for CRC
        
        # Build primary header
        primary_header = self._build_primary_header(packet_data_length)
        
        # Combine and calculate CRC
        packet = primary_header + packet_data
        crc = self._calculate_crc(packet)
        
        full_packet = packet + struct.pack('>H', crc)
        
        # Increment sequence counter
        self._sequence_counter = (self._sequence_counter + 1) & 0x3FFF
        
        if include_sync:
            return self.SYNC_PATTERN + full_packet
        
        return full_packet
    
    def _build_primary_header(self, packet_data_length: int) -> bytes:
        """Build CCSDS primary header."""
        # Word 1: version (3) | type (1) | sec header flag (1) | APID (11)
        word1 = (0 << 13) | (1 << 12) | (1 << 11) | (self.config.apid & 0x7FF)
        
        # Word 2: sequence flags (2) | sequence count (14)
        word2 = (3 << 14) | (self._sequence_counter & 0x3FFF)
        
        # Word 3: packet data length
        word3 = packet_data_length
        
        return struct.pack('>HHH', word1, word2, word3)
    
    def _build_secondary_header(self, service_type: int, 
                                 service_subtype: int) -> bytes:
        """Build PUS TC secondary header."""
        # Byte 0: Version (4 bits) | Ack flags (4 bits)
        byte0 = (1 << 4) | (self.config.ack_flags & 0x0F)
        
        # Byte 1: Service type
        # Byte 2: Service subtype
        # Byte 3: Source ID
        
        return struct.pack('>BBBB', byte0, service_type, service_subtype,
                          self.config.destination_id)
    
    def _calculate_crc(self, data: bytes) -> int:
        """Calculate CRC-16 CCITT."""
        crc = 0xFFFF
        polynomial = 0x1021
        
        for byte in data:
            crc ^= byte << 8
            for _ in range(8):
                if crc & 0x8000:
                    crc = (crc << 1) ^ polynomial
                else:
                    crc = crc << 1
                crc &= 0xFFFF
        
        return crc
    
    def get_sequence_count(self) -> int:
        """Get current sequence count."""
        return self._sequence_counter
    
    def reset_sequence(self):
        """Reset sequence counter."""
        self._sequence_counter = 0


class CommandFactory:
    """
    Factory for creating common telecommands.
    """
    
    def __init__(self, encoder: CCSDSEncoder = None):
        """
        Initialize factory.
        
        Args:
            encoder: CCSDS encoder instance
        """
        self.encoder = encoder or CCSDSEncoder()
    
    def create_ping(self) -> bytes:
        """Create ping command (TC 17,1)."""
        return self.encoder.encode_packet(
            service_type=17,
            service_subtype=1,
        )
    
    def create_mode_change(self, new_mode: int) -> bytes:
        """
        Create mode change command.
        
        Args:
            new_mode: Target mode (0=SAFE, 1=IDLE, 2=NOMINAL, 3=SCIENCE, 4=DOWNLINK)
        """
        data = struct.pack('>B', new_mode)
        return self.encoder.encode_packet(
            service_type=200,  # Mode management
            service_subtype=1,  # Change mode
            data=data,
        )
    
    def create_enable_hk(self, hk_id: int, interval_ms: int) -> bytes:
        """
        Create enable housekeeping command (TC 3,5).
        
        Args:
            hk_id: Housekeeping structure ID
            interval_ms: Reporting interval in milliseconds
        """
        data = struct.pack('>HI', hk_id, interval_ms)
        return self.encoder.encode_packet(
            service_type=3,
            service_subtype=5,
            data=data,
        )
    
    def create_disable_hk(self, hk_id: int) -> bytes:
        """
        Create disable housekeeping command (TC 3,6).
        
        Args:
            hk_id: Housekeeping structure ID
        """
        data = struct.pack('>H', hk_id)
        return self.encoder.encode_packet(
            service_type=3,
            service_subtype=6,
            data=data,
        )
    
    def create_time_sync(self, timestamp_s: int, 
                         timestamp_subsec: int = 0) -> bytes:
        """
        Create time synchronization command (TC 9,1).
        
        Args:
            timestamp_s: Seconds since epoch
            timestamp_subsec: Sub-second component
        """
        data = struct.pack('>IH', timestamp_s, timestamp_subsec)
        return self.encoder.encode_packet(
            service_type=9,
            service_subtype=1,
            data=data,
        )
    
    def create_reset(self, reset_type: int = 0) -> bytes:
        """
        Create reset command (TC 8,1).
        
        Args:
            reset_type: 0=warm reset, 1=cold reset
        """
        data = struct.pack('>B', reset_type)
        return self.encoder.encode_packet(
            service_type=8,
            service_subtype=1,
            data=data,
        )
    
    def create_memory_read(self, address: int, length: int) -> bytes:
        """
        Create memory read command (TC 6,5).
        
        Args:
            address: Memory address
            length: Number of bytes to read
        """
        data = struct.pack('>IH', address, length)
        return self.encoder.encode_packet(
            service_type=6,
            service_subtype=5,
            data=data,
        )
    
    def create_function_call(self, function_id: int, 
                             params: bytes = b'') -> bytes:
        """
        Create function management command (TC 8,1).
        
        Args:
            function_id: Function identifier
            params: Function parameters
        """
        data = struct.pack('>H', function_id) + params
        return self.encoder.encode_packet(
            service_type=8,
            service_subtype=1,
            data=data,
        )
