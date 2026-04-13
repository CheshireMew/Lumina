"""
SDK Utilities
=============

Common utilities for SDK modules including exception handling.
"""

import logging
import functools
import inspect
from typing import Callable, TypeVar, Any, Optional
from contextlib import contextmanager

from .errors import DriverError, LuminaError

logger = logging.getLogger("Lumina.SDK.Utils")

T = TypeVar('T')


def driver_error_handler(
    service_name: str,
    operation: str = "operation"
) -> Callable:
    """
    Decorator for handling driver errors uniformly.
    
    Catches exceptions and converts them to DriverError with consistent logging.
    
    Args:
        service_name: Name of the service (e.g., "STT", "TTS", "LLM")
        operation: Description of the operation (e.g., "recognition", "synthesis")
    
    Example:
        @driver_error_handler("STT", "recognition")
        async def listen(self, timeout: float = 10.0):
            ...
    """
    def decorator(func: Callable) -> Callable:
        @functools.wraps(func)
        async def async_wrapper(*args, **kwargs):
            try:
                return await func(*args, **kwargs)
            except DriverError:
                # Re-raise DriverError as-is (already handled)
                raise
            except LuminaError:
                # Re-raise other Lumina errors as-is
                raise
            except Exception as e:
                logger.error(f"{service_name} {operation} failed: {e}")
                raise DriverError(f"{service_name} {operation} failed: {e}")
        
        @functools.wraps(func)
        def sync_wrapper(*args, **kwargs):
            try:
                return func(*args, **kwargs)
            except DriverError:
                raise
            except LuminaError:
                raise
            except Exception as e:
                logger.error(f"{service_name} {operation} failed: {e}")
                raise DriverError(f"{service_name} {operation} failed: {e}")
        
        # Return appropriate wrapper based on function type
        if inspect.iscoroutinefunction(func):
            return async_wrapper
        return sync_wrapper
    
    return decorator


@contextmanager
def handle_driver_error(service_name: str, operation: str = "operation"):
    """
    Context manager for handling driver errors.
    
    Example:
        with handle_driver_error("TTS", "synthesis"):
            result = await tts_manager.synthesize_async(text)
    """
    try:
        yield
    except DriverError:
        raise
    except LuminaError:
        raise
    except Exception as e:
        logger.error(f"{service_name} {operation} failed: {e}")
        raise DriverError(f"{service_name} {operation} failed: {e}")


def get_service_or_raise(container, service_name: str, display_name: str = None):
    """
    Get a service from container or raise DriverError if unavailable.
    
    Args:
        container: Service container instance
        service_name: Attribute name on container (e.g., 'stt', 'tts')
        display_name: Human-readable name for error messages
    
    Returns:
        The service instance
    
    Raises:
        DriverError: If service is not available
    
    Example:
        stt_manager = get_service_or_raise(self._container, 'stt', 'STT')
    """
    service = getattr(container, service_name, None)
    if not service:
        name = display_name or service_name.upper()
        raise DriverError(f"{name} service unavailable")
    return service
