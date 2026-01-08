#!/usr/bin/env python3
"""
Ground Segment Example
======================

Demonstrates the ground telemetry/telecommand system.
"""

import time
import struct
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from ground.telemetry import TelemetryProcessor, CCSDSDecoder, PUSDecoder, HousekeepingDatabase
from ground.telecommand import CommandBuilder, CommandScheduler


def demonstrate_telecommand():
    """Demonstrate command building."""
    print("=" * 60)
    print("Telecommand System Demonstration")
    print("=" * 60)
    
    from ground.telecommand.command_builder import CommandBuilder, SpacecraftMode, HKStructureID
    
    # Create command builder
    builder = CommandBuilder(apid=100)
    
    print("\nBuilding commands:")
    print("-" * 40)
    
    # Build various commands
    result = builder.ping()
    print(f"1. {result.description}")
    print(f"   Packet: {result.packet.hex()}")
    print(f"   Length: {len(result.packet)} bytes")
    
    result = builder.change_mode(SpacecraftMode.NOMINAL)
    print(f"\n2. {result.description}")
    print(f"   Packet: {result.packet.hex()}")
    
    result = builder.enable_housekeeping(HKStructureID.SYSTEM, interval_seconds=10)
    print(f"\n3. {result.description}")
    print(f"   Packet: {result.packet.hex()}")
    
    result = builder.sync_time()
    print(f"\n4. {result.description}")
    print(f"   Packet: {result.packet.hex()}")
    
    # Print statistics
    stats = builder.get_statistics()
    print(f"\nCommand Statistics:")
    print(f"  Total commands: {stats['total_commands']}")
    print(f"  Current sequence: {stats['sequence_number']}")


def demonstrate_telemetry_decode():
    """Demonstrate telemetry decoding."""
    print("\n" + "=" * 60)
    print("Telemetry Decoder Demonstration")
    print("=" * 60)
    
    # Create a sample CCSDS packet (simulating what spacecraft would send)
    def create_sample_hk_packet():
        """Create a sample housekeeping packet."""
        # Primary header (6 bytes)
        apid = 100
        word1 = (0 << 13) | (0 << 12) | (1 << 11) | apid  # Version=0, Type=TM, SecHdr=1, APID
        word2 = (3 << 14) | 1  # Seq flags=3 (standalone), Seq count=1
        
        # Secondary header (10 bytes) - PUS TM
        pus_version = 1
        service = 3  # Housekeeping
        subtype = 25  # HK report
        dest_id = 0
        timestamp = int(time.time())
        subsec = 0
        
        sec_header = struct.pack('>BBBBIIH', 
                                 pus_version << 4,
                                 service, subtype, dest_id,
                                 timestamp, subsec,
                                 0x0001)  # HK ID = SYSTEM
        
        # System HK data
        hk_data = struct.pack('>BIHBBIxxx',
                             2,          # Mode = NOMINAL
                             3600,       # Uptime = 1 hour
                             5,          # Reset count
                             0,          # Last reset reason
                             25,         # CPU usage 25%
                             102400)     # Memory used
        
        # Calculate packet data length
        data = sec_header + hk_data
        word3 = len(data) + 2 - 1  # +2 for CRC, -1 per CCSDS
        
        header = struct.pack('>HHH', word1, word2, word3)
        
        # CRC placeholder (would need proper calculation)
        crc = 0x0000
        
        return header + data + struct.pack('>H', crc)
    
    # Create decoder
    decoder = CCSDSDecoder(expected_apid=100)
    pus_decoder = PUSDecoder()
    
    # Create and decode sample packet
    packet_bytes = create_sample_hk_packet()
    print(f"\nSample packet ({len(packet_bytes)} bytes):")
    print(f"  Raw: {packet_bytes.hex()}")
    
    # Decode CCSDS
    decoded = decoder.decode_packet(packet_bytes)
    
    if decoded:
        print(f"\nDecoded CCSDS Header:")
        print(f"  Version: {decoded.primary_header.version}")
        print(f"  Type: {decoded.primary_header.packet_type.name}")
        print(f"  APID: {decoded.primary_header.apid}")
        print(f"  Sequence: {decoded.primary_header.sequence_count}")
        
        if decoded.secondary_header:
            print(f"\nDecoded PUS Header:")
            print(f"  Service: {decoded.secondary_header.service_type}")
            print(f"  Subtype: {decoded.secondary_header.service_subtype}")
            print(f"  Timestamp: {decoded.secondary_header.time_seconds}")
        
        # Decode service-specific data
        pus_data = pus_decoder.decode(decoded)
        print(f"\nDecoded HK Data:")
        for key, value in pus_data.items():
            print(f"  {key}: {value}")


def demonstrate_scheduler():
    """Demonstrate command scheduler."""
    print("\n" + "=" * 60)
    print("Command Scheduler Demonstration")
    print("=" * 60)
    
    from ground.telecommand.command_builder import CommandBuilder
    
    builder = CommandBuilder()
    scheduler = CommandScheduler()
    
    # Schedule some commands
    ping_cmd = builder.ping().packet
    scheduler.schedule_relative(ping_cmd, delay_seconds=0.1, description="Ping in 0.1s")
    scheduler.schedule_relative(ping_cmd, delay_seconds=0.2, description="Ping in 0.2s")
    scheduler.schedule_relative(ping_cmd, delay_seconds=0.3, description="Ping in 0.3s")
    
    print("\nPending commands:")
    for cmd in scheduler.get_pending():
        print(f"  [{cmd['schedule_id']}] {cmd['description']} in {cmd['time_until']:.2f}s")
    
    # Process commands
    print("\nProcessing commands...")
    time.sleep(0.5)
    results = scheduler.process()
    
    print(f"\nExecuted {len(results)} commands:")
    for r in results:
        print(f"  [{r.schedule_id}] Success={r.success}, "
              f"Delay={r.actual_time - r.scheduled_time:.3f}s")


def demonstrate_hk_database():
    """Demonstrate housekeeping database."""
    print("\n" + "=" * 60)
    print("Housekeeping Database Demonstration")
    print("=" * 60)
    
    # Create in-memory database
    db = HousekeepingDatabase()
    
    # Store some sample data
    print("\nStoring sample housekeeping data...")
    
    for i in range(10):
        db.store({
            'type': 'SYSTEM_HK',
            'mode': 2,
            'uptime_s': 3600 + i * 60,
            'reset_count': 5,
            'cpu_usage_percent': 20 + i,
            'memory_used_bytes': 100000 + i * 1000,
        }, timestamp=time.time() + i)
        
        db.store({
            'type': 'POWER_HK',
            'battery_voltage_mV': 7400 - i * 10,
            'battery_current_mA': 500 - i * 5,
            'battery_soc_percent': 80 - i,
            'solar_voltage_mV': 8400,
            'solar_current_mA': 300,
            'power_consumption_mW': 3000,
        }, timestamp=time.time() + i)
    
    # Query database
    stats = db.get_statistics()
    print(f"\nDatabase statistics:")
    print(f"  Total records: {stats['total_records']}")
    print(f"  By type: {stats['by_type']}")
    
    # Get latest
    latest = db.get_latest('SYSTEM_HK', count=3)
    print(f"\nLatest 3 SYSTEM_HK records:")
    for record in latest:
        print(f"  Uptime: {record.data['uptime_s']}s, CPU: {record.data['cpu_usage_percent']}%")
    
    db.close()


if __name__ == "__main__":
    demonstrate_telecommand()
    demonstrate_telemetry_decode()
    demonstrate_scheduler()
    demonstrate_hk_database()
    
    print("\n" + "=" * 60)
    print("Ground segment examples complete!")
    print("=" * 60)
