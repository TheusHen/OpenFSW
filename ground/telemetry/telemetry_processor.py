"""
Telemetry Processor
===================

Main telemetry processing pipeline.
"""

import time
from typing import Callable, Optional, List, Dict
from dataclasses import dataclass
from queue import Queue
import threading
from .packet_decoder import CCSDSDecoder, PUSDecoder, DecodedPacket


@dataclass
class TelemetryFrame:
    """Processed telemetry frame."""
    timestamp: float
    packet: DecodedPacket
    decoded_data: dict


class TelemetryProcessor:
    """
    Main telemetry processing class.
    
    Processes incoming telemetry stream and dispatches to handlers.
    """
    
    def __init__(self, expected_apid: int = 100):
        """
        Initialize telemetry processor.
        
        Args:
            expected_apid: Expected spacecraft APID
        """
        self.ccsds_decoder = CCSDSDecoder(expected_apid)
        self.pus_decoder = PUSDecoder()
        
        # Callbacks
        self._hk_callbacks: List[Callable[[dict], None]] = []
        self._event_callbacks: List[Callable[[dict], None]] = []
        self._raw_callbacks: List[Callable[[DecodedPacket], None]] = []
        
        # Processing queue
        self._queue: Queue = Queue()
        self._running = False
        self._thread: Optional[threading.Thread] = None
        
        # Statistics
        self.stats = {
            'frames_received': 0,
            'frames_processed': 0,
            'errors': 0,
        }
        
        # History
        self._history: List[TelemetryFrame] = []
        self._max_history = 10000
    
    def register_hk_callback(self, callback: Callable[[dict], None]):
        """Register callback for housekeeping data."""
        self._hk_callbacks.append(callback)
    
    def register_event_callback(self, callback: Callable[[dict], None]):
        """Register callback for events."""
        self._event_callbacks.append(callback)
    
    def register_raw_callback(self, callback: Callable[[DecodedPacket], None]):
        """Register callback for raw packets."""
        self._raw_callbacks.append(callback)
    
    def process_bytes(self, data: bytes) -> List[TelemetryFrame]:
        """
        Process raw telemetry bytes.
        
        Args:
            data: Raw telemetry bytes
            
        Returns:
            List of processed frames
        """
        frames = []
        
        # Decode all packets
        packets = self.ccsds_decoder.decode_stream(data)
        
        for packet in packets:
            self.stats['frames_received'] += 1
            
            try:
                # Decode PUS content
                decoded = self.pus_decoder.decode(packet)
                
                frame = TelemetryFrame(
                    timestamp=time.time(),
                    packet=packet,
                    decoded_data=decoded,
                )
                
                frames.append(frame)
                self.stats['frames_processed'] += 1
                
                # Store in history
                self._history.append(frame)
                if len(self._history) > self._max_history:
                    self._history.pop(0)
                
                # Dispatch to callbacks
                self._dispatch(frame)
                
                # Raw callbacks
                for cb in self._raw_callbacks:
                    try:
                        cb(packet)
                    except Exception:
                        pass
                
            except Exception as e:
                self.stats['errors'] += 1
        
        return frames
    
    def _dispatch(self, frame: TelemetryFrame):
        """Dispatch frame to appropriate callbacks."""
        data = frame.decoded_data
        
        if 'type' in data:
            if 'HK' in data['type']:
                for cb in self._hk_callbacks:
                    try:
                        cb(data)
                    except Exception:
                        pass
            
            elif data['type'] == 'EVENT':
                for cb in self._event_callbacks:
                    try:
                        cb(data)
                    except Exception:
                        pass
    
    def start_async_processing(self):
        """Start asynchronous processing thread."""
        self._running = True
        self._thread = threading.Thread(target=self._process_loop, daemon=True)
        self._thread.start()
    
    def stop_async_processing(self):
        """Stop asynchronous processing."""
        self._running = False
        if self._thread:
            self._thread.join(timeout=1.0)
    
    def queue_data(self, data: bytes):
        """Queue data for async processing."""
        self._queue.put(data)
    
    def _process_loop(self):
        """Async processing loop."""
        while self._running:
            try:
                data = self._queue.get(timeout=0.1)
                self.process_bytes(data)
            except Exception:
                continue
    
    def get_latest(self, count: int = 10) -> List[TelemetryFrame]:
        """Get latest telemetry frames."""
        return self._history[-count:]
    
    def get_statistics(self) -> Dict:
        """Get processing statistics."""
        return {
            **self.stats,
            **self.ccsds_decoder.stats,
            'history_size': len(self._history),
        }
    
    def clear_history(self):
        """Clear history."""
        self._history.clear()
