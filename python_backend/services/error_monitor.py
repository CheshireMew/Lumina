"""
Error Monitor Service

Centralized error tracking for observability and debugging.
Aggregates errors across the system and provides statistics.

Usage:
    from services.error_monitor import error_monitor, track_error
    
    # Track an error
    track_error(exception, context={"module_id": "my_capability"})
    
    # Get stats
    stats = error_monitor.get_stats()
    
    # Get recent errors
    errors = error_monitor.get_recent_errors(limit=20)
"""

import logging
import time
import traceback
from typing import Optional, Dict, Any, List
from collections import deque, defaultdict
from threading import Lock
from dataclasses import dataclass, field
from datetime import datetime

logger = logging.getLogger("ErrorMonitor")


@dataclass
class ErrorRecord:
    """Record of a single error occurrence."""
    error_type: str
    message: str
    code: Optional[str]
    timestamp: float
    context: Dict[str, Any] = field(default_factory=dict)
    traceback: Optional[str] = None
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "error_type": self.error_type,
            "message": self.message,
            "code": self.code,
            "timestamp": self.timestamp,
            "timestamp_iso": datetime.fromtimestamp(self.timestamp).isoformat(),
            "context": self.context,
        }


class ErrorMonitor:
    """
    Centralized error tracking and statistics.
    
    Features:
    - Track error occurrences with context
    - Maintain rolling window of recent errors
    - Count errors by type
    - Detect error spikes
    """
    
    DEFAULT_MAX_ERRORS = 500  # Keep last N errors
    ERROR_SPIKE_THRESHOLD = 10  # Errors per minute to trigger warning
    ERROR_SPIKE_WINDOW = 60  # Seconds
    
    def __init__(self, max_errors: int = DEFAULT_MAX_ERRORS):
        self._errors: deque = deque(maxlen=max_errors)
        self._error_counts: Dict[str, int] = defaultdict(int)
        self._recent_timestamps: deque = deque(maxlen=100)  # For spike detection
        self._lock = Lock()
        
        # Stats
        self._total_errors = 0
        self._start_time = time.time()
    
    def track(
        self,
        exception: Exception,
        context: Optional[Dict[str, Any]] = None,
        include_traceback: bool = True
    ):
        """
        Track an error occurrence.
        
        Args:
            exception: The exception that occurred
            context: Additional context (module_id, service, etc.)
            include_traceback: Whether to store traceback string
        """
        now = time.time()
        
        # Extract info
        error_type = type(exception).__name__
        message = str(exception)[:500]  # Truncate long messages
        
        # Get code from LuminaError if available
        code = getattr(exception, 'code', None)
        
        # Get traceback
        tb_str = None
        if include_traceback:
            tb_str = traceback.format_exc()[:2000]  # Truncate
        
        record = ErrorRecord(
            error_type=error_type,
            message=message,
            code=code,
            timestamp=now,
            context=context or {},
            traceback=tb_str
        )
        
        with self._lock:
            self._errors.append(record)
            self._error_counts[error_type] += 1
            self._recent_timestamps.append(now)
            self._total_errors += 1
            
            # Check for spike
            self._check_spike(now)
    
    def _check_spike(self, now: float):
        """Check for error spike and log warning."""
        # Count errors in recent window
        cutoff = now - self.ERROR_SPIKE_WINDOW
        recent_count = sum(1 for ts in self._recent_timestamps if ts > cutoff)
        
        if recent_count >= self.ERROR_SPIKE_THRESHOLD:
            logger.warning(
                f"🚨 Error spike detected: {recent_count} errors in last "
                f"{self.ERROR_SPIKE_WINDOW}s (threshold: {self.ERROR_SPIKE_THRESHOLD})"
            )
    
    def get_stats(self) -> Dict[str, Any]:
        """Get error statistics."""
        with self._lock:
            uptime = time.time() - self._start_time
            
            # Top error types
            top_errors = sorted(
                self._error_counts.items(),
                key=lambda x: -x[1]
            )[:10]
            
            return {
                "total_errors": self._total_errors,
                "errors_per_hour": round(self._total_errors / (uptime / 3600), 2) if uptime > 0 else 0,
                "uptime_seconds": round(uptime),
                "recent_errors_count": len(self._errors),
                "error_types": dict(top_errors),
            }
    
    def get_recent_errors(self, limit: int = 20) -> List[Dict[str, Any]]:
        """Get most recent errors."""
        with self._lock:
            errors = list(self._errors)[-limit:]
            return [e.to_dict() for e in reversed(errors)]
    
    def get_errors_by_type(self, error_type: str, limit: int = 10) -> List[Dict[str, Any]]:
        """Get recent errors of a specific type."""
        with self._lock:
            matching = [e for e in self._errors if e.error_type == error_type]
            return [e.to_dict() for e in list(matching)[-limit:]]
    
    def clear(self):
        """Clear all error records (for testing)."""
        with self._lock:
            self._errors.clear()
            self._error_counts.clear()
            self._recent_timestamps.clear()
            self._total_errors = 0
            self._start_time = time.time()
    
    def log_stats(self):
        """Log current error statistics."""
        stats = self.get_stats()
        if stats["total_errors"] > 0:
            logger.info(
                f"📊 ErrorMonitor: {stats['total_errors']} total errors, "
                f"{stats['errors_per_hour']}/hr, "
                f"top types: {list(stats['error_types'].keys())[:3]}"
            )


# Global instance
_monitor: Optional[ErrorMonitor] = None


def get_error_monitor() -> ErrorMonitor:
    """Get the global error monitor."""
    global _monitor
    if _monitor is None:
        _monitor = ErrorMonitor()
        logger.info("⚡ ErrorMonitor initialized")
    return _monitor


def track_error(
    exception: Exception,
    context: Optional[Dict[str, Any]] = None,
    include_traceback: bool = True
):
    """
    Convenience function to track an error.
    
    Args:
        exception: The exception to track
        context: Additional context
        include_traceback: Whether to include traceback
    """
    get_error_monitor().track(exception, context, include_traceback)


def get_error_stats() -> Dict[str, Any]:
    """Get error statistics."""
    return get_error_monitor().get_stats()


# Convenience alias
error_monitor = get_error_monitor
