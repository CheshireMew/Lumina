"""
Structured Logger Extensions.
Enhanced logging utilities with additional context and metrics integration.
"""

import logging
import time
import functools
from typing import Any, Dict, Optional, Callable
from contextvars import ContextVar

# Re-export core context vars from logger_setup
from logger_setup import request_id_ctx, session_id_ctx

# Additional context vars for structured logging
trace_id_ctx: ContextVar[str] = ContextVar("trace_id", default="-")
user_id_ctx: ContextVar[str] = ContextVar("user_id", default="-")
operation_ctx: ContextVar[str] = ContextVar("operation", default="-")


def set_log_context(
    request_id: str = None,
    session_id: str = None,
    trace_id: str = None,
    user_id: str = None,
    operation: str = None
):
    """
    Set multiple log context values at once.
    Returns tokens that can be used to reset context.
    """
    tokens = {}
    if request_id:
        tokens['request_id'] = request_id_ctx.set(request_id)
    if session_id:
        tokens['session_id'] = session_id_ctx.set(session_id)
    if trace_id:
        tokens['trace_id'] = trace_id_ctx.set(trace_id)
    if user_id:
        tokens['user_id'] = user_id_ctx.set(user_id)
    if operation:
        tokens['operation'] = operation_ctx.set(operation)
    return tokens


def reset_log_context(tokens: Dict[str, Any]):
    """Reset log context to previous values using tokens."""
    if 'request_id' in tokens:
        request_id_ctx.reset(tokens['request_id'])
    if 'session_id' in tokens:
        session_id_ctx.reset(tokens['session_id'])
    if 'trace_id' in tokens:
        trace_id_ctx.reset(tokens['trace_id'])
    if 'user_id' in tokens:
        user_id_ctx.reset(tokens['user_id'])
    if 'operation' in tokens:
        operation_ctx.reset(tokens['operation'])


class StructuredLogger:
    """
    Enhanced logger with structured logging methods.
    Provides convenience methods for common logging patterns.
    """
    
    def __init__(self, name: str):
        self._logger = logging.getLogger(name)
    
    def _build_extra(self, extra: Dict[str, Any] = None) -> Dict[str, Any]:
        """Build extra dict with context vars."""
        result = {
            "trace_id": trace_id_ctx.get(),
            "user_id": user_id_ctx.get(),
            "operation": operation_ctx.get()
        }
        if extra:
            result.update(extra)
        return result
    
    def info(self, msg: str, **kwargs):
        self._logger.info(msg, extra=self._build_extra(kwargs))
    
    def debug(self, msg: str, **kwargs):
        self._logger.debug(msg, extra=self._build_extra(kwargs))
    
    def warning(self, msg: str, **kwargs):
        self._logger.warning(msg, extra=self._build_extra(kwargs))
    
    def error(self, msg: str, exc_info: bool = False, **kwargs):
        self._logger.error(msg, exc_info=exc_info, extra=self._build_extra(kwargs))
    
    def critical(self, msg: str, exc_info: bool = True, **kwargs):
        self._logger.critical(msg, exc_info=exc_info, extra=self._build_extra(kwargs))
    
    # --- Specialized Logging Methods ---
    
    def log_request(
        self,
        method: str,
        path: str,
        status_code: int,
        latency_ms: float,
        user_id: str = None,
        **extra
    ):
        """Log an HTTP request with structured fields."""
        self._logger.info(
            f"{method} {path} -> {status_code} ({latency_ms:.2f}ms)",
            extra=self._build_extra({
                "event_type": "http_request",
                "method": method,
                "path": path,
                "status_code": status_code,
                "latency_ms": latency_ms,
                "user_id": user_id or user_id_ctx.get(),
                **extra
            })
        )
    
    def log_llm_call(
        self,
        model: str,
        prompt_tokens: int,
        completion_tokens: int,
        latency_ms: float,
        success: bool = True,
        **extra
    ):
        """Log an LLM API call with structured fields."""
        level = logging.INFO if success else logging.WARNING
        self._logger.log(
            level,
            f"LLM [{model}] {prompt_tokens}+{completion_tokens} tokens ({latency_ms:.0f}ms)",
            extra=self._build_extra({
                "event_type": "llm_call",
                "model": model,
                "prompt_tokens": prompt_tokens,
                "completion_tokens": completion_tokens,
                "latency_ms": latency_ms,
                "success": success,
                **extra
            })
        )
    
    def log_capability_module_event(
        self,
        module_id: str,
        event: str,
        success: bool = True,
        **extra
    ):
        """Log a capability module lifecycle event."""
        level = logging.INFO if success else logging.WARNING
        self._logger.log(
            level,
            f"Capability module [{module_id}] {event}",
            extra=self._build_extra({
                "event_type": "capability_module_event",
                "module_id": module_id,
                "event": event,
                "success": success,
                **extra
            })
        )
    
    def log_worker_event(
        self,
        worker_id: str,
        event: str,
        worker_type: str = None,
        **extra
    ):
        """Log a worker process event."""
        self._logger.info(
            f"Worker [{worker_id}] {event}",
            extra=self._build_extra({
                "event_type": "worker_event",
                "worker_id": worker_id,
                "worker_type": worker_type,
                "event": event,
                **extra
            })
        )


def get_structured_logger(name: str) -> StructuredLogger:
    """Get a structured logger instance."""
    return StructuredLogger(name)


def log_duration(logger_name: str = None, operation: str = None):
    """
    Decorator that logs function execution duration.
    
    Usage:
        @log_duration("MyService", "process_data")
        async def my_function():
            ...
    """
    def decorator(func: Callable):
        nonlocal logger_name, operation
        logger_name = logger_name or func.__module__
        operation = operation or func.__name__
        slogger = get_structured_logger(logger_name)
        
        @functools.wraps(func)
        async def async_wrapper(*args, **kwargs):
            start = time.time()
            tokens = set_log_context(operation=operation)
            try:
                result = await func(*args, **kwargs)
                slogger.debug(
                    f"{operation} completed",
                    duration_ms=(time.time() - start) * 1000
                )
                return result
            except Exception as e:
                slogger.error(
                    f"{operation} failed: {e}",
                    duration_ms=(time.time() - start) * 1000,
                    exc_info=True
                )
                raise
            finally:
                reset_log_context(tokens)
        
        @functools.wraps(func)
        def sync_wrapper(*args, **kwargs):
            start = time.time()
            tokens = set_log_context(operation=operation)
            try:
                result = func(*args, **kwargs)
                slogger.debug(
                    f"{operation} completed",
                    duration_ms=(time.time() - start) * 1000
                )
                return result
            except Exception as e:
                slogger.error(
                    f"{operation} failed: {e}",
                    duration_ms=(time.time() - start) * 1000,
                    exc_info=True
                )
                raise
            finally:
                reset_log_context(tokens)
        
        import asyncio
        if asyncio.iscoroutinefunction(func):
            return async_wrapper
        return sync_wrapper
    
    return decorator
