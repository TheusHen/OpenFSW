"""
Telemetry Archive
=================

Long-term telemetry storage and retrieval.
"""

import time
import gzip
import json
from pathlib import Path
from typing import Optional, List, Dict, Iterator
from dataclasses import dataclass
from datetime import datetime


@dataclass
class ArchiveIndex:
    """Archive file index entry."""
    filename: str
    start_time: float
    end_time: float
    packet_count: int
    size_bytes: int


class TelemetryArchive:
    """
    File-based telemetry archive.
    
    Stores telemetry in compressed JSON files organized by date.
    """
    
    def __init__(self, archive_dir: str = "./telemetry_archive"):
        """
        Initialize archive.
        
        Args:
            archive_dir: Directory for archive files
        """
        self.archive_dir = Path(archive_dir)
        self.archive_dir.mkdir(parents=True, exist_ok=True)
        
        # Current file buffer
        self._buffer: List[dict] = []
        self._buffer_start: Optional[float] = None
        self._max_buffer_size = 1000
        self._max_buffer_age = 3600  # 1 hour
        
        # Index cache
        self._index: List[ArchiveIndex] = []
        self._load_index()
    
    def _load_index(self):
        """Load archive index from files."""
        self._index.clear()
        
        for filepath in self.archive_dir.glob("*.json.gz"):
            try:
                # Parse filename for metadata
                # Format: YYYYMMDD_HHMMSS_HHMMSS.json.gz
                name = filepath.stem.replace('.json', '')
                parts = name.split('_')
                
                if len(parts) >= 3:
                    date_str = parts[0]
                    start_str = parts[1]
                    end_str = parts[2]
                    
                    start_dt = datetime.strptime(f"{date_str}_{start_str}", "%Y%m%d_%H%M%S")
                    end_dt = datetime.strptime(f"{date_str}_{end_str}", "%Y%m%d_%H%M%S")
                    
                    self._index.append(ArchiveIndex(
                        filename=filepath.name,
                        start_time=start_dt.timestamp(),
                        end_time=end_dt.timestamp(),
                        packet_count=0,  # Could read from file
                        size_bytes=filepath.stat().st_size,
                    ))
            except Exception:
                continue
        
        # Sort by start time
        self._index.sort(key=lambda x: x.start_time)
    
    def store(self, packet_data: dict, timestamp: Optional[float] = None):
        """
        Store a telemetry packet.
        
        Args:
            packet_data: Packet data dictionary
            timestamp: Optional timestamp
        """
        ts = timestamp or time.time()
        
        if self._buffer_start is None:
            self._buffer_start = ts
        
        self._buffer.append({
            'timestamp': ts,
            'data': packet_data,
        })
        
        # Check if buffer should be flushed
        if (len(self._buffer) >= self._max_buffer_size or
            ts - self._buffer_start >= self._max_buffer_age):
            self.flush()
    
    def flush(self):
        """Flush buffer to archive file."""
        if not self._buffer:
            return
        
        # Create filename
        start_dt = datetime.fromtimestamp(self._buffer_start)
        end_dt = datetime.fromtimestamp(self._buffer[-1]['timestamp'])
        
        date_str = start_dt.strftime("%Y%m%d")
        start_str = start_dt.strftime("%H%M%S")
        end_str = end_dt.strftime("%H%M%S")
        
        filename = f"{date_str}_{start_str}_{end_str}.json.gz"
        filepath = self.archive_dir / filename
        
        # Write compressed JSON
        with gzip.open(filepath, 'wt', encoding='utf-8') as f:
            json.dump({
                'start_time': self._buffer_start,
                'end_time': self._buffer[-1]['timestamp'],
                'packet_count': len(self._buffer),
                'packets': self._buffer,
            }, f)
        
        # Update index
        self._index.append(ArchiveIndex(
            filename=filename,
            start_time=self._buffer_start,
            end_time=self._buffer[-1]['timestamp'],
            packet_count=len(self._buffer),
            size_bytes=filepath.stat().st_size,
        ))
        
        # Clear buffer
        self._buffer.clear()
        self._buffer_start = None
    
    def query(self, start_time: float, end_time: float) -> Iterator[dict]:
        """
        Query archived packets in time range.
        
        Args:
            start_time: Start timestamp
            end_time: End timestamp
            
        Yields:
            Packet data dictionaries
        """
        # Find relevant files
        for entry in self._index:
            if entry.end_time < start_time:
                continue
            if entry.start_time > end_time:
                break
            
            # Read file
            filepath = self.archive_dir / entry.filename
            
            try:
                with gzip.open(filepath, 'rt', encoding='utf-8') as f:
                    data = json.load(f)
                    
                    for packet in data.get('packets', []):
                        ts = packet.get('timestamp', 0)
                        if start_time <= ts <= end_time:
                            yield packet['data']
            except Exception:
                continue
        
        # Also check current buffer
        for packet in self._buffer:
            ts = packet.get('timestamp', 0)
            if start_time <= ts <= end_time:
                yield packet['data']
    
    def get_index(self) -> List[ArchiveIndex]:
        """Get archive index."""
        return self._index.copy()
    
    def get_statistics(self) -> Dict:
        """Get archive statistics."""
        total_packets = sum(e.packet_count for e in self._index)
        total_size = sum(e.size_bytes for e in self._index)
        
        return {
            'num_files': len(self._index),
            'total_packets': total_packets,
            'total_size_bytes': total_size,
            'total_size_MB': total_size / 1024 / 1024,
            'buffer_size': len(self._buffer),
            'oldest': datetime.fromtimestamp(self._index[0].start_time).isoformat()
                      if self._index else None,
            'newest': datetime.fromtimestamp(self._index[-1].end_time).isoformat()
                      if self._index else None,
        }
    
    def close(self):
        """Flush and close archive."""
        self.flush()
