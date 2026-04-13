"""
Metrics API Router.
Exposes Prometheus-compatible /metrics endpoint.
"""

import logging
from fastapi import APIRouter, Response, Request
from fastapi.responses import PlainTextResponse

from services.observability import get_metrics, get_metrics_content_type

logger = logging.getLogger("MetricsRouter")

router = APIRouter(prefix="/metrics", tags=["Observability"])


@router.get("")
async def metrics_endpoint(request: Request):
    """
    Prometheus metrics endpoint.
    
    Returns all collected metrics in Prometheus text format.
    Access: Localhost only for security.
    """
    # Security: Localhost only
    client_host = request.client.host if request.client else ""
    if client_host not in ["127.0.0.1", "::1", "localhost"]:
        return PlainTextResponse(
            content="Forbidden: Localhost access only",
            status_code=403
        )
    
    metrics_output = get_metrics()
    return Response(
        content=metrics_output,
        media_type=get_metrics_content_type()
    )


@router.get("/health")
async def metrics_health():
    """Health check for metrics subsystem."""
    return {"status": "ok", "subsystem": "metrics"}
