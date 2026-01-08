"""
Command Scheduler
=================

Schedules commands for execution at specific times.
"""

import time
import heapq
import threading
from dataclasses import dataclass, field
from typing import Optional, List, Callable, Dict, Any
from enum import IntEnum


class ScheduleType(IntEnum):
    """Command schedule type."""
    ABSOLUTE = 0      # Execute at specific time
    RELATIVE = 1      # Execute after delay
    PERIODIC = 2      # Execute periodically
    CONDITIONAL = 3   # Execute when condition met


@dataclass(order=True)
class ScheduledCommand:
    """Scheduled command entry."""
    execution_time: float
    schedule_id: int = field(compare=False)
    command_bytes: bytes = field(compare=False)
    description: str = field(compare=False)
    schedule_type: ScheduleType = field(compare=False)
    period_seconds: Optional[float] = field(compare=False, default=None)
    condition: Optional[Callable[[], bool]] = field(compare=False, default=None)
    executed: bool = field(compare=False, default=False)
    execution_count: int = field(compare=False, default=0)


@dataclass
class ExecutionResult:
    """Command execution result."""
    schedule_id: int
    command_bytes: bytes
    scheduled_time: float
    actual_time: float
    success: bool
    error_message: Optional[str] = None


class CommandScheduler:
    """
    Command scheduler for time-based command execution.
    
    Supports:
    - Absolute time scheduling
    - Relative time scheduling
    - Periodic command execution
    - Conditional execution
    """
    
    def __init__(self, executor: Optional[Callable[[bytes], bool]] = None):
        """
        Initialize scheduler.
        
        Args:
            executor: Callback to execute commands
        """
        self.executor = executor
        
        # Priority queue of scheduled commands
        self._queue: List[ScheduledCommand] = []
        self._schedule_id_counter = 0
        
        # Results history
        self._results: List[ExecutionResult] = []
        
        # Background thread
        self._running = False
        self._thread: Optional[threading.Thread] = None
        self._lock = threading.Lock()
        
        # Callbacks
        self._on_execute: List[Callable[[ExecutionResult], None]] = []
    
    def schedule_absolute(self, command: bytes, execution_time: float,
                         description: str = "") -> int:
        """
        Schedule command for absolute time.
        
        Args:
            command: Command bytes
            execution_time: Unix timestamp
            description: Command description
            
        Returns:
            Schedule ID
        """
        return self._add_schedule(ScheduledCommand(
            execution_time=execution_time,
            schedule_id=self._get_next_id(),
            command_bytes=command,
            description=description,
            schedule_type=ScheduleType.ABSOLUTE,
        ))
    
    def schedule_relative(self, command: bytes, delay_seconds: float,
                         description: str = "") -> int:
        """
        Schedule command for relative time.
        
        Args:
            command: Command bytes
            delay_seconds: Delay from now
            description: Command description
            
        Returns:
            Schedule ID
        """
        execution_time = time.time() + delay_seconds
        return self._add_schedule(ScheduledCommand(
            execution_time=execution_time,
            schedule_id=self._get_next_id(),
            command_bytes=command,
            description=description,
            schedule_type=ScheduleType.RELATIVE,
        ))
    
    def schedule_periodic(self, command: bytes, period_seconds: float,
                         start_time: Optional[float] = None,
                         description: str = "") -> int:
        """
        Schedule periodic command.
        
        Args:
            command: Command bytes
            period_seconds: Repeat period
            start_time: First execution time (default: now)
            description: Command description
            
        Returns:
            Schedule ID
        """
        exec_time = start_time or time.time()
        return self._add_schedule(ScheduledCommand(
            execution_time=exec_time,
            schedule_id=self._get_next_id(),
            command_bytes=command,
            description=description,
            schedule_type=ScheduleType.PERIODIC,
            period_seconds=period_seconds,
        ))
    
    def schedule_conditional(self, command: bytes, 
                            condition: Callable[[], bool],
                            check_interval: float = 1.0,
                            timeout: float = 3600.0,
                            description: str = "") -> int:
        """
        Schedule conditional command.
        
        Args:
            command: Command bytes
            condition: Condition callback
            check_interval: How often to check condition
            timeout: Maximum time to wait
            description: Command description
            
        Returns:
            Schedule ID
        """
        # Store condition info
        return self._add_schedule(ScheduledCommand(
            execution_time=time.time() + check_interval,
            schedule_id=self._get_next_id(),
            command_bytes=command,
            description=description,
            schedule_type=ScheduleType.CONDITIONAL,
            period_seconds=check_interval,
            condition=condition,
        ))
    
    def _add_schedule(self, cmd: ScheduledCommand) -> int:
        """Add command to schedule."""
        with self._lock:
            heapq.heappush(self._queue, cmd)
        return cmd.schedule_id
    
    def _get_next_id(self) -> int:
        """Get next schedule ID."""
        self._schedule_id_counter += 1
        return self._schedule_id_counter
    
    def cancel(self, schedule_id: int) -> bool:
        """
        Cancel scheduled command.
        
        Args:
            schedule_id: Schedule ID to cancel
            
        Returns:
            True if found and cancelled
        """
        with self._lock:
            for i, cmd in enumerate(self._queue):
                if cmd.schedule_id == schedule_id:
                    self._queue.pop(i)
                    heapq.heapify(self._queue)
                    return True
        return False
    
    def cancel_all(self):
        """Cancel all scheduled commands."""
        with self._lock:
            self._queue.clear()
    
    def process(self) -> List[ExecutionResult]:
        """
        Process due commands (synchronous).
        
        Returns:
            List of execution results
        """
        results = []
        current_time = time.time()
        
        with self._lock:
            while self._queue and self._queue[0].execution_time <= current_time:
                cmd = heapq.heappop(self._queue)
                
                # Handle conditional commands
                if cmd.schedule_type == ScheduleType.CONDITIONAL:
                    if cmd.condition and not cmd.condition():
                        # Condition not met, reschedule
                        cmd.execution_time = current_time + cmd.period_seconds
                        heapq.heappush(self._queue, cmd)
                        continue
                
                # Execute command
                result = self._execute_command(cmd, current_time)
                results.append(result)
                
                # Reschedule periodic commands
                if (cmd.schedule_type == ScheduleType.PERIODIC and 
                    cmd.period_seconds):
                    cmd.execution_time = current_time + cmd.period_seconds
                    cmd.execution_count += 1
                    heapq.heappush(self._queue, cmd)
        
        return results
    
    def _execute_command(self, cmd: ScheduledCommand, 
                         current_time: float) -> ExecutionResult:
        """Execute a single command."""
        success = False
        error = None
        
        if self.executor:
            try:
                success = self.executor(cmd.command_bytes)
            except Exception as e:
                error = str(e)
        else:
            success = True  # No executor, assume success
        
        result = ExecutionResult(
            schedule_id=cmd.schedule_id,
            command_bytes=cmd.command_bytes,
            scheduled_time=cmd.execution_time,
            actual_time=current_time,
            success=success,
            error_message=error,
        )
        
        self._results.append(result)
        
        # Notify callbacks
        for cb in self._on_execute:
            try:
                cb(result)
            except Exception:
                pass
        
        return result
    
    def start_background(self, interval: float = 0.1):
        """
        Start background processing thread.
        
        Args:
            interval: Processing interval in seconds
        """
        if self._running:
            return
        
        self._running = True
        self._thread = threading.Thread(
            target=self._background_loop,
            args=(interval,),
            daemon=True
        )
        self._thread.start()
    
    def stop_background(self):
        """Stop background processing."""
        self._running = False
        if self._thread:
            self._thread.join(timeout=1.0)
    
    def _background_loop(self, interval: float):
        """Background processing loop."""
        while self._running:
            self.process()
            time.sleep(interval)
    
    def on_execute(self, callback: Callable[[ExecutionResult], None]):
        """Register execution callback."""
        self._on_execute.append(callback)
    
    def get_pending(self) -> List[Dict]:
        """Get pending commands."""
        with self._lock:
            return [{
                'schedule_id': cmd.schedule_id,
                'execution_time': cmd.execution_time,
                'description': cmd.description,
                'type': cmd.schedule_type.name,
                'time_until': cmd.execution_time - time.time(),
            } for cmd in sorted(self._queue)]
    
    def get_results(self, count: int = 10) -> List[ExecutionResult]:
        """Get recent execution results."""
        return self._results[-count:]
    
    def get_statistics(self) -> Dict:
        """Get scheduler statistics."""
        success_count = sum(1 for r in self._results if r.success)
        
        return {
            'pending_commands': len(self._queue),
            'executed_commands': len(self._results),
            'success_count': success_count,
            'failure_count': len(self._results) - success_count,
            'background_running': self._running,
        }
