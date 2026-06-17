"""
Lumina Exception Hierarchy

Provides a structured exception system for the entire backend.
All custom exceptions inherit from LuminaError for unified handling.

Usage:
    from core.exceptions import (
        LuminaError,
        CapabilityModuleError, CapabilityModuleLoadError, CapabilityModulePermissionError,
        ConfigError, ConfigValidationError,
        ServiceError, ServiceUnavailableError,
        NetworkError, WorkerOfflineError,
    )
    
    try:
        await load_capability(module_id)
    except CapabilityModuleLoadError as e:
        logger.error(f"Failed to load capability module: {e}")
    except CapabilityModuleError as e:
        logger.error(f"Capability module error: {e}")
    except LuminaError as e:
        logger.error(f"System error: {e}")
"""

from typing import Optional, Dict, Any


class LuminaError(Exception):
    """
    Base exception for all Lumina errors.
    
    Attributes:
        message: Human-readable error description
        code: Machine-readable error code (e.g., "PLUGIN_LOAD_FAILED")
        details: Additional context for debugging
        cause: Original exception if this wraps another error
    """
    
    def __init__(
        self, 
        message: str, 
        code: Optional[str] = None,
        details: Optional[Dict[str, Any]] = None,
        cause: Optional[Exception] = None
    ):
        super().__init__(message)
        self.message = message
        self.code = code or self.__class__.__name__.upper()
        self.details = details or {}
        self.cause = cause
        
        # Store original traceback if wrapping
        if cause:
            self.__cause__ = cause
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to JSON-serializable dict for API responses."""
        return {
            "error": self.code,
            "message": self.message,
            "details": self.details,
        }
    
    def __str__(self) -> str:
        if self.cause:
            return f"{self.message} (caused by: {self.cause})"
        return self.message


# =============================================================================
# Capability Module Errors
# =============================================================================

class CapabilityModuleError(LuminaError):
    """Base class for all capability module-related errors."""
    
    def __init__(
        self, 
        message: str, 
        module_id: Optional[str] = None,
        **kwargs
    ):
        super().__init__(message, **kwargs)
        self.module_id = module_id
        if module_id:
            self.details["module_id"] = module_id


class CapabilityModuleLoadError(CapabilityModuleError):
    """Failed to load a capability module."""
    pass


class CapabilityModuleInitError(CapabilityModuleError):
    """Capability module loaded but failed to initialize."""
    pass


class CapabilityModulePermissionError(CapabilityModuleError):
    """Capability module attempted unauthorized action."""
    
    def __init__(
        self, 
        message: str, 
        module_id: Optional[str] = None,
        permission: Optional[str] = None,
        **kwargs
    ):
        super().__init__(message, module_id=module_id, **kwargs)
        self.permission = permission
        if permission:
            self.details["permission"] = permission


class CapabilityModuleNotFoundError(CapabilityModuleError):
    """Capability module does not exist."""
    pass


class CapabilityModuleStateError(CapabilityModuleError):
    """Capability module is in unexpected state."""
    pass


# =============================================================================
# Configuration Errors
# =============================================================================

class ConfigError(LuminaError):
    """Base class for configuration errors."""
    pass


class ConfigValidationError(ConfigError):
    """Configuration value failed validation."""
    
    def __init__(
        self, 
        message: str, 
        key: Optional[str] = None,
        value: Any = None,
        **kwargs
    ):
        super().__init__(message, **kwargs)
        if key:
            self.details["key"] = key
        if value is not None:
            self.details["value"] = str(value)[:100]  # Truncate for safety


class ConfigMissingError(ConfigError):
    """Required configuration is missing."""
    pass


# =============================================================================
# Service Errors
# =============================================================================

class ServiceError(LuminaError):
    """Base class for service-layer errors."""
    
    def __init__(
        self, 
        message: str, 
        service_name: Optional[str] = None,
        **kwargs
    ):
        super().__init__(message, **kwargs)
        if service_name:
            self.details["service"] = service_name


class ServiceUnavailableError(ServiceError):
    """Service is not available or not initialized."""
    pass


class ServiceTimeoutError(ServiceError):
    """Service operation timed out."""
    pass


# =============================================================================
# Network/Communication Errors
# =============================================================================

class NetworkError(LuminaError):
    """Base class for network-related errors."""
    pass


class WorkerOfflineError(NetworkError):
    """Worker process is not responding."""
    
    def __init__(
        self, 
        message: str, 
        worker_id: Optional[str] = None,
        **kwargs
    ):
        super().__init__(message, **kwargs)
        if worker_id:
            self.details["worker_id"] = worker_id


class ConnectionError(NetworkError):
    """Failed to establish connection."""
    pass


class APIError(NetworkError):
    """External API returned error."""
    
    def __init__(
        self, 
        message: str, 
        status_code: Optional[int] = None,
        **kwargs
    ):
        super().__init__(message, **kwargs)
        if status_code:
            self.details["status_code"] = status_code


# =============================================================================
# Data/Storage Errors
# =============================================================================

class DataError(LuminaError):
    """Base class for data-related errors."""
    pass


class DataNotFoundError(DataError):
    """Requested data does not exist."""
    pass


class DataValidationError(DataError):
    """Data failed validation."""
    pass


class PersistenceError(DataError):
    """Failed to read/write persistent data."""
    pass


# =============================================================================
# Security Errors
# =============================================================================

class SecurityError(LuminaError):
    """Base class for security-related errors."""
    pass


class PermissionDeniedError(SecurityError):
    """Operation not permitted."""
    pass


class PathTraversalError(SecurityError):
    """Attempted path traversal attack detected."""
    pass


# =============================================================================
# LLM/AI Errors
# =============================================================================

class LLMError(LuminaError):
    """Base class for LLM-related errors."""
    pass


class LLMProviderError(LLMError):
    """LLM provider returned error."""
    pass


class LLMRateLimitError(LLMError):
    """Hit rate limit on LLM provider."""
    pass


class LLMContextOverflowError(LLMError):
    """Context length exceeded model limit."""
    pass


# =============================================================================
# Convenience function for wrapping exceptions
# =============================================================================

def wrap_exception(
    exception: Exception,
    wrapper_class: type = LuminaError,
    message: Optional[str] = None,
    **kwargs
) -> LuminaError:
    """
    Wrap an exception in a LuminaError.
    
    Args:
        exception: The original exception
        wrapper_class: LuminaError subclass to use
        message: Custom message (default: str(exception))
        **kwargs: Additional arguments for wrapper
        
    Returns:
        Wrapped LuminaError instance
    """
    msg = message or str(exception)
    return wrapper_class(msg, cause=exception, **kwargs)
