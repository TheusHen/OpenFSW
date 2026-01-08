"""
Housekeeping Database
=====================

Storage and querying for housekeeping telemetry.
"""

import time
import sqlite3
from pathlib import Path
from typing import Dict, List, Optional, Any
from dataclasses import dataclass
import json


@dataclass
class HKRecord:
    """Housekeeping record."""
    timestamp: float
    hk_type: str
    data: dict


class HousekeepingDatabase:
    """
    SQLite-based housekeeping storage.
    
    Stores and queries housekeeping telemetry for analysis.
    """
    
    def __init__(self, db_path: Optional[str] = None):
        """
        Initialize database.
        
        Args:
            db_path: Path to SQLite database (default: in-memory)
        """
        self.db_path = db_path or ':memory:'
        self.conn = sqlite3.connect(self.db_path, check_same_thread=False)
        self._create_tables()
    
    def _create_tables(self):
        """Create database tables."""
        cursor = self.conn.cursor()
        
        # Main housekeeping table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS housekeeping (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                timestamp REAL NOT NULL,
                hk_type TEXT NOT NULL,
                data_json TEXT NOT NULL,
                created_at REAL DEFAULT (strftime('%s', 'now'))
            )
        ''')
        
        # System HK table (denormalized for fast queries)
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS system_hk (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                timestamp REAL NOT NULL,
                mode INTEGER,
                uptime_s INTEGER,
                reset_count INTEGER,
                cpu_usage_percent INTEGER,
                memory_used_bytes INTEGER
            )
        ''')
        
        # Power HK table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS power_hk (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                timestamp REAL NOT NULL,
                battery_voltage_mV INTEGER,
                battery_current_mA INTEGER,
                battery_soc_percent INTEGER,
                solar_voltage_mV INTEGER,
                solar_current_mA INTEGER,
                power_consumption_mW INTEGER
            )
        ''')
        
        # ADCS HK table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS adcs_hk (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                timestamp REAL NOT NULL,
                q0 REAL, q1 REAL, q2 REAL, q3 REAL,
                omega_x REAL, omega_y REAL, omega_z REAL,
                mode INTEGER,
                sun_valid INTEGER
            )
        ''')
        
        # Events table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS events (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                timestamp REAL NOT NULL,
                event_id INTEGER,
                severity INTEGER,
                onboard_time INTEGER,
                data TEXT
            )
        ''')
        
        # Create indices
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_hk_timestamp ON housekeeping(timestamp)')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_hk_type ON housekeeping(hk_type)')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_system_time ON system_hk(timestamp)')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_power_time ON power_hk(timestamp)')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_adcs_time ON adcs_hk(timestamp)')
        
        self.conn.commit()
    
    def store(self, hk_data: dict, timestamp: Optional[float] = None):
        """
        Store housekeeping data.
        
        Args:
            hk_data: Decoded housekeeping dictionary
            timestamp: Optional timestamp (default: now)
        """
        ts = timestamp or time.time()
        hk_type = hk_data.get('type', 'UNKNOWN')
        
        cursor = self.conn.cursor()
        
        # Store in main table
        cursor.execute(
            'INSERT INTO housekeeping (timestamp, hk_type, data_json) VALUES (?, ?, ?)',
            (ts, hk_type, json.dumps(hk_data))
        )
        
        # Store in specialized tables
        if hk_type == 'SYSTEM_HK':
            cursor.execute('''
                INSERT INTO system_hk 
                (timestamp, mode, uptime_s, reset_count, cpu_usage_percent, memory_used_bytes)
                VALUES (?, ?, ?, ?, ?, ?)
            ''', (ts, hk_data.get('mode'), hk_data.get('uptime_s'),
                  hk_data.get('reset_count'), hk_data.get('cpu_usage_percent'),
                  hk_data.get('memory_used_bytes')))
        
        elif hk_type == 'POWER_HK':
            cursor.execute('''
                INSERT INTO power_hk 
                (timestamp, battery_voltage_mV, battery_current_mA, battery_soc_percent,
                 solar_voltage_mV, solar_current_mA, power_consumption_mW)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            ''', (ts, hk_data.get('battery_voltage_mV'), hk_data.get('battery_current_mA'),
                  hk_data.get('battery_soc_percent'), hk_data.get('solar_voltage_mV'),
                  hk_data.get('solar_current_mA'), hk_data.get('power_consumption_mW')))
        
        elif hk_type == 'ADCS_HK':
            q = hk_data.get('quaternion', [0, 0, 0, 1])
            omega = hk_data.get('angular_velocity_deg_s', [0, 0, 0])
            cursor.execute('''
                INSERT INTO adcs_hk 
                (timestamp, q0, q1, q2, q3, omega_x, omega_y, omega_z, mode, sun_valid)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', (ts, q[0], q[1], q[2], q[3], omega[0], omega[1], omega[2],
                  hk_data.get('mode'), hk_data.get('sun_valid')))
        
        elif hk_type == 'EVENT':
            cursor.execute('''
                INSERT INTO events 
                (timestamp, event_id, severity, onboard_time, data)
                VALUES (?, ?, ?, ?, ?)
            ''', (ts, hk_data.get('event_id'), hk_data.get('severity'),
                  hk_data.get('timestamp'), hk_data.get('data', '')))
        
        self.conn.commit()
    
    def query_range(self, hk_type: str, start_time: float, 
                    end_time: float) -> List[HKRecord]:
        """
        Query housekeeping in time range.
        
        Args:
            hk_type: Type of housekeeping
            start_time: Start timestamp
            end_time: End timestamp
            
        Returns:
            List of HK records
        """
        cursor = self.conn.cursor()
        
        cursor.execute('''
            SELECT timestamp, hk_type, data_json FROM housekeeping
            WHERE hk_type = ? AND timestamp >= ? AND timestamp <= ?
            ORDER BY timestamp
        ''', (hk_type, start_time, end_time))
        
        records = []
        for row in cursor.fetchall():
            records.append(HKRecord(
                timestamp=row[0],
                hk_type=row[1],
                data=json.loads(row[2])
            ))
        
        return records
    
    def get_latest(self, hk_type: str, count: int = 1) -> List[HKRecord]:
        """Get latest HK records."""
        cursor = self.conn.cursor()
        
        cursor.execute('''
            SELECT timestamp, hk_type, data_json FROM housekeeping
            WHERE hk_type = ?
            ORDER BY timestamp DESC
            LIMIT ?
        ''', (hk_type, count))
        
        records = []
        for row in cursor.fetchall():
            records.append(HKRecord(
                timestamp=row[0],
                hk_type=row[1],
                data=json.loads(row[2])
            ))
        
        return records
    
    def get_power_trend(self, hours: float = 24) -> Dict[str, List]:
        """Get power system trend data."""
        cursor = self.conn.cursor()
        
        start_time = time.time() - hours * 3600
        
        cursor.execute('''
            SELECT timestamp, battery_voltage_mV, battery_soc_percent, 
                   solar_current_mA, power_consumption_mW
            FROM power_hk
            WHERE timestamp >= ?
            ORDER BY timestamp
        ''', (start_time,))
        
        timestamps = []
        voltage = []
        soc = []
        solar = []
        power = []
        
        for row in cursor.fetchall():
            timestamps.append(row[0])
            voltage.append(row[1])
            soc.append(row[2])
            solar.append(row[3])
            power.append(row[4])
        
        return {
            'timestamps': timestamps,
            'voltage_mV': voltage,
            'soc_percent': soc,
            'solar_current_mA': solar,
            'power_mW': power,
        }
    
    def get_statistics(self) -> Dict:
        """Get database statistics."""
        cursor = self.conn.cursor()
        
        cursor.execute('SELECT COUNT(*) FROM housekeeping')
        total = cursor.fetchone()[0]
        
        cursor.execute('SELECT hk_type, COUNT(*) FROM housekeeping GROUP BY hk_type')
        by_type = dict(cursor.fetchall())
        
        return {
            'total_records': total,
            'by_type': by_type,
        }
    
    def close(self):
        """Close database connection."""
        self.conn.close()
