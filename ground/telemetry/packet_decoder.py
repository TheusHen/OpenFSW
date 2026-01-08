"""
CCSDS Packet Decoder
====================

Decodes CCSDS Space Packets and PUS packets.
"""

import struct
from dataclasses import dataclass
from typing import Optional, List, Tuple
from enum import IntEnum


class CCSDSPacketType(IntEnum):
    """CCSDS Packet type."""
    TELEMETRY = 0
    TELECOMMAND = 1


class PUSService(IntEnum):
    """PUS service types."""
    HOUSEKEEPING = 3
    EVENT_REPORTING = 5
    MEMORY_MANAGEMENT = 6
    FUNCTION_MANAGEMENT = 8
    TIME_MANAGEMENT = 9
    SCHEDULING = 11
    ON_BOARD_MONITORING = 12
    LARGE_PACKET = 13
    PACKET_FORWARDING = 14
    ON_BOARD_STORAGE = 15
    TEST = 17


@dataclass
class CCSDSPrimaryHeader:
    """CCSDS Space Packet Primary Header (6 bytes)."""
    version: int              # 3 bits
    packet_type: CCSDSPacketType  # 1 bit
    secondary_header_flag: bool   # 1 bit
    apid: int                 # 11 bits
    sequence_flags: int       # 2 bits
    sequence_count: int       # 14 bits
    packet_data_length: int   # 16 bits (length of data field - 1)
    
    @property
    def total_length(self) -> int:
        """Total packet length including header."""
        return 6 + self.packet_data_length + 1


@dataclass
class PUSSecondaryHeader:
    """PUS Telemetry Secondary Header."""
    pus_version: int          # 4 bits
    service_type: int         # 8 bits
    service_subtype: int      # 8 bits
    destination_id: int       # 8 bits
    time_seconds: int         # 32 bits
    time_subseconds: int      # 16 bits


@dataclass
class DecodedPacket:
    """Fully decoded packet."""
    primary_header: CCSDSPrimaryHeader
    secondary_header: Optional[PUSSecondaryHeader]
    data: bytes
    crc_valid: bool
    raw_bytes: bytes


class CCSDSDecoder:
    """
    CCSDS Space Packet decoder.
    
    Decodes CCSDS primary headers and extracts packet data.
    """
    
    SYNC_PATTERN = bytes([0x1A, 0xCF, 0xFC, 0x1D])  # ASM pattern
    
    def __init__(self, expected_apid: Optional[int] = None):
        """
        Initialize decoder.
        
        Args:
            expected_apid: If set, filter for this APID only
        """
        self.expected_apid = expected_apid
        self.stats = {
            'packets_decoded': 0,
            'crc_errors': 0,
            'sync_errors': 0,
        }
    
    def decode_primary_header(self, data: bytes) -> Optional[CCSDSPrimaryHeader]:
        """
        Decode CCSDS primary header.
        
        Args:
            data: At least 6 bytes of packet data
            
        Returns:
            Decoded header or None if invalid
        """
        if len(data) < 6:
            return None
        
        # Unpack 6 bytes
        word1, word2, word3 = struct.unpack('>HHH', data[:6])
        
        # Parse first word
        version = (word1 >> 13) & 0x07
        packet_type = CCSDSPacketType((word1 >> 12) & 0x01)
        sec_header_flag = bool((word1 >> 11) & 0x01)
        apid = word1 & 0x07FF
        
        # Parse second word
        sequence_flags = (word2 >> 14) & 0x03
        sequence_count = word2 & 0x3FFF
        
        # Third word is packet data length
        packet_data_length = word3
        
        return CCSDSPrimaryHeader(
            version=version,
            packet_type=packet_type,
            secondary_header_flag=sec_header_flag,
            apid=apid,
            sequence_flags=sequence_flags,
            sequence_count=sequence_count,
            packet_data_length=packet_data_length,
        )
    
    def find_packet_start(self, data: bytes) -> int:
        """
        Find start of next packet using sync pattern.
        
        Args:
            data: Raw byte stream
            
        Returns:
            Index of packet start, or -1 if not found
        """
        return data.find(self.SYNC_PATTERN)
    
    def decode_packet(self, data: bytes) -> Optional[DecodedPacket]:
        """
        Decode a complete CCSDS packet.
        
        Args:
            data: Raw packet bytes (without sync pattern)
            
        Returns:
            Decoded packet or None
        """
        # Decode primary header
        primary = self.decode_primary_header(data)
        if primary is None:
            return None
        
        # Check APID filter
        if self.expected_apid is not None and primary.apid != self.expected_apid:
            return None
        
        # Extract full packet
        total_length = primary.total_length
        if len(data) < total_length:
            return None
        
        packet_data = data[6:total_length]
        
        # Decode secondary header if present
        secondary = None
        if primary.secondary_header_flag and len(packet_data) >= 10:
            secondary = self._decode_pus_secondary(packet_data[:10])
            user_data = packet_data[10:-2] if len(packet_data) > 12 else b''
        else:
            user_data = packet_data[:-2] if len(packet_data) > 2 else packet_data
        
        # Verify CRC (last 2 bytes)
        crc_valid = True
        if len(packet_data) >= 2:
            received_crc = struct.unpack('>H', packet_data[-2:])[0]
            calculated_crc = self._calculate_crc(data[:total_length-2])
            crc_valid = (received_crc == calculated_crc)
            
            if not crc_valid:
                self.stats['crc_errors'] += 1
        
        self.stats['packets_decoded'] += 1
        
        return DecodedPacket(
            primary_header=primary,
            secondary_header=secondary,
            data=user_data,
            crc_valid=crc_valid,
            raw_bytes=data[:total_length],
        )
    
    def _decode_pus_secondary(self, data: bytes) -> PUSSecondaryHeader:
        """Decode PUS secondary header."""
        pus_version = (data[0] >> 4) & 0x0F
        service_type = data[1]
        service_subtype = data[2]
        dest_id = data[3]
        time_seconds = struct.unpack('>I', data[4:8])[0]
        time_subseconds = struct.unpack('>H', data[8:10])[0]
        
        return PUSSecondaryHeader(
            pus_version=pus_version,
            service_type=service_type,
            service_subtype=service_subtype,
            destination_id=dest_id,
            time_seconds=time_seconds,
            time_subseconds=time_subseconds,
        )
    
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
    
    def decode_stream(self, data: bytes) -> List[DecodedPacket]:
        """
        Decode multiple packets from a byte stream.
        
        Args:
            data: Raw byte stream
            
        Returns:
            List of decoded packets
        """
        packets = []
        offset = 0
        
        while offset < len(data) - 6:
            # Try to decode packet at current offset
            packet = self.decode_packet(data[offset:])
            
            if packet is not None:
                packets.append(packet)
                offset += packet.primary_header.total_length
            else:
                offset += 1  # Move to next byte and try again
        
        return packets


class PUSDecoder:
    """
    PUS service-specific decoder.
    
    Decodes data fields for specific PUS services.
    """
    
    def __init__(self):
        """Initialize PUS decoder."""
        self.handlers = {
            PUSService.HOUSEKEEPING: self._decode_housekeeping,
            PUSService.EVENT_REPORTING: self._decode_event,
            PUSService.TEST: self._decode_test,
        }
    
    def decode(self, packet: DecodedPacket) -> dict:
        """
        Decode PUS packet data.
        
        Args:
            packet: Decoded CCSDS packet with PUS secondary header
            
        Returns:
            Service-specific decoded data
        """
        if packet.secondary_header is None:
            return {'error': 'No PUS secondary header'}
        
        service = packet.secondary_header.service_type
        
        if service in self.handlers:
            return self.handlers[service](packet)
        
        return {'raw_data': packet.data.hex()}
    
    def _decode_housekeeping(self, packet: DecodedPacket) -> dict:
        """Decode housekeeping packet."""
        data = packet.data
        subtype = packet.secondary_header.service_subtype
        
        if subtype == 25 and len(data) >= 4:  # HK report
            hk_id = struct.unpack('>H', data[0:2])[0]
            
            # Parse based on HK ID (matches telemetry.h definitions)
            if hk_id == 0x0001:  # SYSTEM_HK
                return self._parse_system_hk(data[2:])
            elif hk_id == 0x0002:  # POWER_HK
                return self._parse_power_hk(data[2:])
            elif hk_id == 0x0003:  # ADCS_HK
                return self._parse_adcs_hk(data[2:])
            elif hk_id == 0x0004:  # COMMS_HK
                return self._parse_comms_hk(data[2:])
        
        return {'hk_id': hk_id if 'hk_id' in dir() else None, 
                'raw': data.hex()}
    
    def _parse_system_hk(self, data: bytes) -> dict:
        """Parse system housekeeping."""
        if len(data) < 16:
            return {'error': 'Insufficient data'}
        
        return {
            'type': 'SYSTEM_HK',
            'mode': struct.unpack('>B', data[0:1])[0],
            'uptime_s': struct.unpack('>I', data[1:5])[0],
            'reset_count': struct.unpack('>H', data[5:7])[0],
            'last_reset_reason': struct.unpack('>B', data[7:8])[0],
            'cpu_usage_percent': struct.unpack('>B', data[8:9])[0],
            'memory_used_bytes': struct.unpack('>I', data[9:13])[0],
        }
    
    def _parse_power_hk(self, data: bytes) -> dict:
        """Parse power housekeeping."""
        if len(data) < 14:
            return {'error': 'Insufficient data'}
        
        return {
            'type': 'POWER_HK',
            'battery_voltage_mV': struct.unpack('>H', data[0:2])[0],
            'battery_current_mA': struct.unpack('>h', data[2:4])[0],
            'battery_soc_percent': struct.unpack('>B', data[4:5])[0],
            'solar_voltage_mV': struct.unpack('>H', data[5:7])[0],
            'solar_current_mA': struct.unpack('>H', data[7:9])[0],
            'power_consumption_mW': struct.unpack('>H', data[9:11])[0],
        }
    
    def _parse_adcs_hk(self, data: bytes) -> dict:
        """Parse ADCS housekeeping."""
        if len(data) < 32:
            return {'error': 'Insufficient data'}
        
        # Parse quaternion (4 x int16 scaled)
        q = [struct.unpack('>h', data[i:i+2])[0] / 32767.0 for i in range(0, 8, 2)]
        
        # Parse angular velocity (3 x int16)
        omega = [struct.unpack('>h', data[i:i+2])[0] / 1000.0 
                 for i in range(8, 14, 2)]
        
        return {
            'type': 'ADCS_HK',
            'quaternion': q,
            'angular_velocity_deg_s': omega,
            'mode': struct.unpack('>B', data[14:15])[0],
            'sun_valid': bool(data[15] & 0x01),
        }
    
    def _parse_comms_hk(self, data: bytes) -> dict:
        """Parse communications housekeeping."""
        if len(data) < 12:
            return {'error': 'Insufficient data'}
        
        return {
            'type': 'COMMS_HK',
            'packets_received': struct.unpack('>I', data[0:4])[0],
            'packets_transmitted': struct.unpack('>I', data[4:8])[0],
            'rx_rssi_dBm': struct.unpack('>b', data[8:9])[0],
            'tx_power_dBm': struct.unpack('>B', data[9:10])[0],
        }
    
    def _decode_event(self, packet: DecodedPacket) -> dict:
        """Decode event report."""
        data = packet.data
        
        if len(data) >= 8:
            return {
                'type': 'EVENT',
                'event_id': struct.unpack('>H', data[0:2])[0],
                'severity': data[2],
                'timestamp': struct.unpack('>I', data[3:7])[0],
                'data': data[7:].hex() if len(data) > 7 else '',
            }
        
        return {'raw': data.hex()}
    
    def _decode_test(self, packet: DecodedPacket) -> dict:
        """Decode test packet (ping response)."""
        return {
            'type': 'TEST',
            'subtype': packet.secondary_header.service_subtype,
            'data': packet.data.hex(),
        }
