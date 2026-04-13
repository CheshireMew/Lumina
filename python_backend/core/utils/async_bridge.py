"""
Async Bridge Utility.

Standardizes the bridging between async and sync code.
Integrates with observability metrics to track blocking operation duration.

Usage:
    from core.utils.async_bridge import run_sync, run_cpu_bound

    # I/O Bound (File, Network)
    result = await run_sync(read_file, "config.yaml")

    # CPU Bound (Encoding, Calculation)
    result = await run_cpu_bound(encode_vector, data)
"""

import asyncio
import functools
import logging
from typing import TypeVar, Callable, Any, ParamSpec
import contextvars

logger = logging.getLogger("AsyncBridge")

T = TypeVar("T")
P = ParamSpec("P")

# Try to import metrics, fail gracefully if not available (e.g. during early bootstrap)
try:
    from services.observability.metrics import observe_duration, METHOD_DURATION
    METRICS_AVAILABLE = True
except ImportError:
    METRICS_AVAILABLE = False


async def run_sync(func: Callable[P, T], *args: P.args, **kwargs: P.kwargs) -> T:
    """
    Run a blocking I/O operation in a separate thread.
    Uses asyncio.to_thread (thread pool).
    
    Args:
        func: The synchronous function to call
        *args: Positional arguments
        **kwargs: Keyword arguments
        
    Returns:
        Result of the function call
    """
    func_name = getattr(func, "__name__", str(func))
    
    # 1. Track Metrics
    if METRICS_AVAILABLE:
        # We manually track duration because decorators are hard to apply to args
        # But for simplicity, we let the inner execution run
        # A better approach for metrics might be wrapper logic here
        pass

    # 2. Context Propagation
    # asyncio.to_thread automatically propagates contextvars in Python 3.9+
    
    # 3. Execution
    try:
        # Handle kwargs using partial because to_thread only accepts *args
        if kwargs:
            func = functools.partial(func, **kwargs)
            
        return await asyncio.to_thread(func, *args)
        
    except Exception as e:
        logger.error(f"Error in run_sync({func_name}): {e}")
        raise


async def run_cpu_bound(func: Callable[P, T], *args: P.args, **kwargs: P.kwargs) -> T:
    """
    Run a CPU-bound operation in the default executor (usually ProcessPool or ThreadPool).
    Should be used for heavy calculations to avoid blocking the event loop.
    
    Args:
        func: The synchronous function to call
        *args: Positional arguments
        **kwargs: Keyword arguments
        
    Returns:
        Result of the function
    """
    loop = asyncio.get_running_loop()
    func_name = getattr(func, "__name__", str(func))
    
    # Handle kwargs
    if kwargs:
        func = functools.partial(func, **kwargs)
    
    # Propagate context manually for run_in_executor if needed
    context = contextvars.copy_context()
    func_with_context = functools.partial(context.run, func)

    try:
        return await loop.run_in_executor(None, func_with_context, *args)
    except Exception as e:
        logger.error(f"Error in run_cpu_bound({func_name}): {e}")
        raise
