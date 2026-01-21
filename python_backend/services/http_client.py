"""
Shared HTTP Client Pool

Provides a reusable httpx.AsyncClient for efficient HTTP connection pooling.
Avoids the overhead of creating new connections for each request.

Usage:
    from services.http_client import get_http_client, close_http_client
    
    client = get_http_client()
    response = await client.get("http://example.com")
    
    # Call on shutdown
    await close_http_client()
"""

import logging
import asyncio
from typing import Optional
import httpx

logger = logging.getLogger("HTTPClient")


class HTTPClientPool:
    """
    Manages a shared httpx.AsyncClient with connection pooling.
    
    Features:
    - Lazy initialization
    - Automatic connection pooling (httpx default: 100 connections)
    - Configurable timeouts
    - Thread-safe (asyncio)
    """
    
    # Default configuration
    DEFAULT_TIMEOUT = httpx.Timeout(
        connect=5.0,    # Connection timeout
        read=30.0,      # Read timeout
        write=30.0,     # Write timeout
        pool=5.0        # Pool timeout (waiting for available connection)
    )
    
    # Connection pool limits
    DEFAULT_LIMITS = httpx.Limits(
        max_keepalive_connections=20,  # Persistent connections to keep
        max_connections=50,             # Maximum total connections
        keepalive_expiry=30.0           # How long to keep idle connections
    )
    
    def __init__(self):
        self._client: Optional[httpx.AsyncClient] = None
        self._lock = asyncio.Lock()
        self._is_closed = False
    
    async def get_client(self) -> httpx.AsyncClient:
        """
        Get the shared HTTP client.
        Creates one if it doesn't exist.
        """
        if self._client is not None and not self._is_closed:
            return self._client
        
        async with self._lock:
            if self._client is not None and not self._is_closed:
                return self._client
            
            self._client = httpx.AsyncClient(
                timeout=self.DEFAULT_TIMEOUT,
                limits=self.DEFAULT_LIMITS,
                http2=True,  # Enable HTTP/2 for better performance
            )
            self._is_closed = False
            logger.info("⚡ Shared HTTP client initialized (pool: 50 max connections)")
            return self._client
    
    async def close(self):
        """Close the HTTP client and release all connections."""
        async with self._lock:
            if self._client and not self._is_closed:
                await self._client.aclose()
                self._is_closed = True
                self._client = None
                logger.info("🔌 Shared HTTP client closed")
    
    def get_stats(self) -> dict:
        """Get connection pool statistics (if available)."""
        if not self._client:
            return {"status": "not_initialized"}
        
        # httpx doesn't expose detailed pool stats, but we can show config
        return {
            "status": "active" if not self._is_closed else "closed",
            "max_connections": self.DEFAULT_LIMITS.max_connections,
            "max_keepalive": self.DEFAULT_LIMITS.max_keepalive_connections,
            "timeout_connect": self.DEFAULT_TIMEOUT.connect,
            "timeout_read": self.DEFAULT_TIMEOUT.read,
        }


# Global instance
_pool: Optional[HTTPClientPool] = None


def _get_pool() -> HTTPClientPool:
    """Get or create the global pool."""
    global _pool
    if _pool is None:
        _pool = HTTPClientPool()
    return _pool


async def get_http_client() -> httpx.AsyncClient:
    """
    Get the shared HTTP client.
    
    Example:
        client = await get_http_client()
        response = await client.get("http://localhost:8010/health")
    """
    return await _get_pool().get_client()


async def close_http_client():
    """
    Close the shared HTTP client.
    Call this during application shutdown.
    """
    await _get_pool().close()


def get_http_stats() -> dict:
    """Get HTTP client statistics."""
    return _get_pool().get_stats()


# Convenience functions for common patterns

async def http_get(url: str, **kwargs) -> httpx.Response:
    """Shorthand for GET request using shared client."""
    client = await get_http_client()
    return await client.get(url, **kwargs)


async def http_post(url: str, **kwargs) -> httpx.Response:
    """Shorthand for POST request using shared client."""
    client = await get_http_client()
    return await client.post(url, **kwargs)


async def http_get_json(url: str, **kwargs) -> dict:
    """GET request returning JSON."""
    response = await http_get(url, **kwargs)
    response.raise_for_status()
    return response.json()


async def http_post_json(url: str, json_data: dict, **kwargs) -> dict:
    """POST JSON request returning JSON."""
    response = await http_post(url, json=json_data, **kwargs)
    response.raise_for_status()
    return response.json()
