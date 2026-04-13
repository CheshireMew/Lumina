"""
Resilience Utilities for Inter-Process Communication.
Provides RetryPolicy and CircuitBreaker patterns for robust HTTP calls.
"""

import asyncio
import logging
import time
from enum import Enum
from typing import TypeVar, Callable, Any, Optional
from dataclasses import dataclass, field

logger = logging.getLogger("Resilience")

T = TypeVar("T")


class CircuitState(Enum):
    CLOSED = "closed"      # Normal operation
    OPEN = "open"          # Failing, reject calls
    HALF_OPEN = "half_open"  # Testing if recovered


@dataclass
class RetryPolicy:
    """Configuration for retry behavior."""
    max_retries: int = 3
    base_delay: float = 0.5  # seconds
    max_delay: float = 5.0   # seconds
    exponential_backoff: bool = True
    retryable_exceptions: tuple = (Exception,)

    def get_delay(self, attempt: int) -> float:
        """Calculate delay for given attempt number."""
        if self.exponential_backoff:
            delay = min(self.base_delay * (2 ** attempt), self.max_delay)
        else:
            delay = self.base_delay
        return delay


@dataclass
class CircuitBreakerConfig:
    """Configuration for circuit breaker."""
    failure_threshold: int = 5       # Failures before opening
    success_threshold: int = 2       # Successes in half-open to close
    timeout: float = 30.0            # Seconds to stay open before half-open


class CircuitBreaker:
    """
    Circuit Breaker Pattern Implementation.
    
    States:
    - CLOSED: Normal operation. Track failures.
    - OPEN: Reject all calls immediately. Wait for timeout.
    - HALF_OPEN: Allow limited calls to test recovery.
    """
    
    def __init__(self, name: str, config: CircuitBreakerConfig = None):
        self.name = name
        self.config = config or CircuitBreakerConfig()
        self._state = CircuitState.CLOSED
        self._failure_count = 0
        self._success_count = 0
        self._last_failure_time: Optional[float] = None

    @property
    def state(self) -> CircuitState:
        # Auto-transition from OPEN to HALF_OPEN after timeout
        if self._state == CircuitState.OPEN:
            if self._last_failure_time:
                elapsed = time.time() - self._last_failure_time
                if elapsed >= self.config.timeout:
                    logger.info(f"🔄 [CircuitBreaker:{self.name}] Transitioning OPEN -> HALF_OPEN")
                    self._state = CircuitState.HALF_OPEN
                    self._success_count = 0
        return self._state

    def record_success(self):
        """Record a successful call."""
        if self._state == CircuitState.HALF_OPEN:
            self._success_count += 1
            if self._success_count >= self.config.success_threshold:
                logger.info(f"✅ [CircuitBreaker:{self.name}] Recovered. HALF_OPEN -> CLOSED")
                self._state = CircuitState.CLOSED
                self._failure_count = 0
        elif self._state == CircuitState.CLOSED:
            # Reset failure count on success in closed state
            self._failure_count = 0

    def record_failure(self):
        """Record a failed call."""
        self._failure_count += 1
        self._last_failure_time = time.time()
        
        if self._state == CircuitState.HALF_OPEN:
            logger.warning(f"❌ [CircuitBreaker:{self.name}] Failed in HALF_OPEN. Reopening.")
            self._state = CircuitState.OPEN
        elif self._state == CircuitState.CLOSED:
            if self._failure_count >= self.config.failure_threshold:
                logger.warning(f"🔥 [CircuitBreaker:{self.name}] Threshold reached. CLOSED -> OPEN")
                self._state = CircuitState.OPEN

    def allow_request(self) -> bool:
        """Check if a request should be allowed."""
        current_state = self.state  # Triggers auto-transition
        if current_state == CircuitState.OPEN:
            return False
        return True


# --- Global Circuit Breaker Registry ---
_circuit_breakers: dict[str, CircuitBreaker] = {}


def get_circuit_breaker(name: str, config: CircuitBreakerConfig = None) -> CircuitBreaker:
    """Get or create a named circuit breaker."""
    if name not in _circuit_breakers:
        _circuit_breakers[name] = CircuitBreaker(name, config)
    return _circuit_breakers[name]


# --- Resilient HTTP Call ---

async def resilient_call(
    func: Callable[..., Any],
    *args,
    retry_policy: RetryPolicy = None,
    circuit_breaker_name: str = None,
    fallback: Callable[..., Any] = None,
    **kwargs
) -> Any:
    """
    Execute an async function with retry and circuit breaker protection.
    
    Args:
        func: The async function to call.
        retry_policy: Retry configuration. Defaults to 3 retries with exponential backoff.
        circuit_breaker_name: Name of circuit breaker to use. If None, no circuit breaker.
        fallback: Optional fallback function to call if all retries fail.
        *args, **kwargs: Arguments to pass to func.
    
    Returns:
        The result of func, or fallback result if all retries fail and fallback is provided.
    
    Raises:
        The last exception if all retries fail and no fallback is provided.
    """
    policy = retry_policy or RetryPolicy()
    cb = get_circuit_breaker(circuit_breaker_name) if circuit_breaker_name else None
    
    last_exception = None
    
    for attempt in range(policy.max_retries + 1):
        # Circuit Breaker Check
        if cb and not cb.allow_request():
            logger.warning(f"🚫 [Resilience] Circuit breaker '{circuit_breaker_name}' is OPEN. Skipping call.")
            if fallback:
                return await fallback(*args, **kwargs) if asyncio.iscoroutinefunction(fallback) else fallback(*args, **kwargs)
            raise CircuitOpenError(f"Circuit breaker '{circuit_breaker_name}' is open")
        
        try:
            result = await func(*args, **kwargs)
            if cb:
                cb.record_success()
            return result
            
        except policy.retryable_exceptions as e:
            last_exception = e
            if cb:
                cb.record_failure()
            
            if attempt < policy.max_retries:
                delay = policy.get_delay(attempt)
                logger.warning(f"⚠️ [Resilience] Attempt {attempt + 1}/{policy.max_retries + 1} failed: {e}. Retrying in {delay:.1f}s...")
                await asyncio.sleep(delay)
            else:
                logger.error(f"❌ [Resilience] All {policy.max_retries + 1} attempts failed.")
    
    # All retries exhausted
    if fallback:
        logger.info(f"🔄 [Resilience] Executing fallback...")
        return await fallback(*args, **kwargs) if asyncio.iscoroutinefunction(fallback) else fallback(*args, **kwargs)
    
    raise last_exception


class CircuitOpenError(Exception):
    """Raised when a circuit breaker is open and rejects a call."""
    pass


# --- Convenience Wrapper for HTTP ---

async def resilient_http_post(
    url: str,
    json: dict = None,
    timeout: float = 5.0,
    circuit_breaker_name: str = None,
    retry_policy: RetryPolicy = None
) -> dict:
    """
    Perform a POST request with resilience.
    
    Returns:
        Parsed JSON response as dict.
    
    Raises:
        CircuitOpenError: If circuit breaker is open.
        httpx.HTTPError: If request fails after all retries.
    """
    import httpx
    
    async def _do_post():
        async with httpx.AsyncClient() as client:
            resp = await client.post(url, json=json, timeout=timeout)
            resp.raise_for_status()
            return resp.json()
    
    return await resilient_call(
        _do_post,
        retry_policy=retry_policy or RetryPolicy(
            max_retries=2,
            base_delay=0.3,
            retryable_exceptions=(httpx.ConnectError, httpx.TimeoutException, httpx.HTTPStatusError)
        ),
        circuit_breaker_name=circuit_breaker_name
    )
