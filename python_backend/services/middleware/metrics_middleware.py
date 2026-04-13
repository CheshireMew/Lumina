"""
Metrics Middleware.
Automatically tracks HTTP request metrics for all endpoints.
"""

import time
import logging
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response

from services.observability.metrics import (
    HTTP_REQUESTS_TOTAL,
    HTTP_REQUEST_DURATION,
    HTTP_REQUESTS_IN_PROGRESS
)

logger = logging.getLogger("MetricsMiddleware")


class MetricsMiddleware(BaseHTTPMiddleware):
    """
    Middleware to automatically collect HTTP request metrics.
    
    Tracks:
    - Request count by method, endpoint, status code
    - Request duration histogram
    - Requests in progress gauge
    """
    
    # Endpoints to exclude from detailed tracking (high cardinality)
    EXCLUDE_PATHS = {"/metrics", "/health", "/ws/"}
    
    async def dispatch(self, request: Request, call_next) -> Response:
        # Skip metrics for certain paths
        path = request.url.path
        if any(path.startswith(exc) for exc in self.EXCLUDE_PATHS):
            return await call_next(request)
        
        # Normalize path to avoid high cardinality
        # e.g., /plugins/abc123 -> /plugins/{id}
        normalized_path = self._normalize_path(path)
        method = request.method
        
        # Track in-progress
        HTTP_REQUESTS_IN_PROGRESS.labels(
            method=method, 
            endpoint=normalized_path
        ).inc()
        
        start_time = time.time()
        status_code = "500"  # Default to error
        
        try:
            response = await call_next(request)
            status_code = str(response.status_code)
            return response
        except Exception:
            status_code = "500"
            raise
        finally:
            # Record duration
            duration = time.time() - start_time
            HTTP_REQUEST_DURATION.labels(
                method=method,
                endpoint=normalized_path
            ).observe(duration)
            
            # Record request count
            HTTP_REQUESTS_TOTAL.labels(
                method=method,
                endpoint=normalized_path,
                status_code=status_code
            ).inc()
            
            # Decrement in-progress
            HTTP_REQUESTS_IN_PROGRESS.labels(
                method=method,
                endpoint=normalized_path
            ).dec()
    
    def _normalize_path(self, path: str) -> str:
        """
        Normalize path to reduce cardinality.
        Replaces dynamic segments (UUIDs, IDs) with placeholders.
        """
        import re
        
        # Replace UUIDs
        path = re.sub(
            r'[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}',
            '{id}',
            path,
            flags=re.IGNORECASE
        )
        
        # Replace numeric IDs at end of path segments
        path = re.sub(r'/\d+(?=/|$)', '/{id}', path)
        
        # Replace common ID patterns (alphanumeric strings after known prefixes)
        path = re.sub(r'/(plugins|characters|memories|sessions)/[a-zA-Z0-9_-]+', r'/\1/{id}', path)
        
        return path
