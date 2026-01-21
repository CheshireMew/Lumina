
import logging
from fastapi import Request
from services.router_manager import _request_resources

logger = logging.getLogger("ResourceCleanup")

async def resource_cleanup_middleware(request: Request, call_next):
    """
    [Architecture 3.2] Request Resource Cleanup.
    Ensures that any handles tracked by SafeResource are released
    at the end of the request context.
    """
    token = _request_resources.set([])
    try:
        response = await call_next(request)
        return response
    finally:
        resources = _request_resources.get()
        if resources:
            logger.debug(f"🧹 [Safety] Cleaning up {len(resources)} request resources")
            for r in resources:
                r.release()
        _request_resources.reset(token)
