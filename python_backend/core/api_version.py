"""
API Version Decorators for Plugin Development

Provides decorators to mark API stability and deprecation status,
helping plugin developers understand which APIs are safe to use.

Usage:
    @api_stable("1.0")
    def my_stable_api(): ...

    @api_experimental
    def my_new_api(): ...

    @deprecated("2.0", use="new_method")
    def old_api(): ...
"""

import functools
import warnings
import logging
from typing import Optional, Callable

logger = logging.getLogger("API")

# Current API version
PLUGIN_API_VERSION = "1.0"


def api_stable(version: str):
    """
    Mark an API as stable since the specified version.
    
    Stable APIs guarantee:
    - No breaking changes until major version bump
    - Deprecation warnings before removal
    
    Args:
        version: The version since this API is stable (e.g., "1.0")
    """
    def decorator(func: Callable) -> Callable:
        func._api_stable = True
        func._api_version = version
        
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            return func(*args, **kwargs)
        
        wrapper._api_stable = True
        wrapper._api_version = version
        return wrapper
    return decorator


def api_experimental(func: Callable) -> Callable:
    """
    Mark an API as experimental.
    
    Experimental APIs:
    - May change without notice
    - Should not be used in production plugins
    - Will log a warning on first use
    """
    warned = [False]  # Mutable to track warning state
    
    @functools.wraps(func)
    def wrapper(*args, **kwargs):
        if not warned[0]:
            logger.warning(
                f"⚠️ Experimental API: {func.__module__}.{func.__name__}() "
                f"may change in future versions."
            )
            warned[0] = True
        return func(*args, **kwargs)
    
    wrapper._api_experimental = True
    return wrapper


def deprecated(remove_in: str, use: Optional[str] = None):
    """
    Mark an API as deprecated.
    
    Args:
        remove_in: Version when this API will be removed (e.g., "2.0")
        use: Name of the replacement API (optional)
    
    Deprecated APIs:
    - Will log a warning on every use
    - Will be removed in the specified version
    """
    def decorator(func: Callable) -> Callable:
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            msg = f"⚠️ Deprecated: {func.__name__}() will be removed in v{remove_in}."
            if use:
                msg += f" Use {use}() instead."
            
            # Log warning
            logger.warning(msg)
            
            # Also emit Python warning for IDE/linter detection
            warnings.warn(msg, DeprecationWarning, stacklevel=2)
            
            return func(*args, **kwargs)
        
        wrapper._deprecated = True
        wrapper._deprecated_in = remove_in
        wrapper._deprecated_use = use
        return wrapper
    return decorator


def get_api_info(func: Callable) -> dict:
    """
    Get API metadata from a function.
    
    Returns:
        {
            "stable": bool,
            "version": str or None,
            "experimental": bool,
            "deprecated": bool,
            "deprecated_in": str or None,
            "deprecated_use": str or None
        }
    """
    return {
        "stable": getattr(func, "_api_stable", False),
        "version": getattr(func, "_api_version", None),
        "experimental": getattr(func, "_api_experimental", False),
        "deprecated": getattr(func, "_deprecated", False),
        "deprecated_in": getattr(func, "_deprecated_in", None),
        "deprecated_use": getattr(func, "_deprecated_use", None),
    }


# Context Protocol version (for manifest compatibility checking)
CONTEXT_PROTOCOL_VERSION = "1.0"


def check_manifest_compatibility(manifest_api_version: str) -> bool:
    """
    Check if a plugin manifest's API version is compatible with current.
    
    Args:
        manifest_api_version: The api_version field from manifest.yaml
        
    Returns:
        True if compatible, False otherwise
    """
    if not manifest_api_version:
        return True  # No version specified, assume compatible
    
    try:
        manifest_major = int(manifest_api_version.split(".")[0])
        current_major = int(PLUGIN_API_VERSION.split(".")[0])
        
        # Same major version = compatible
        return manifest_major == current_major
    except (ValueError, IndexError):
        logger.warning(f"Invalid api_version format: {manifest_api_version}")
        return True  # Be lenient
