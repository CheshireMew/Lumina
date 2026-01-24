
from fastapi import Request
from starlette.middleware.base import BaseHTTPMiddleware
import logging
from security.tokens import TokenManager

logger = logging.getLogger("ScopeGuard")

class ScopeGuardMiddleware(BaseHTTPMiddleware):
    """
    [Architecture] Plugin Scoped Authentication.
    Validates JWT tokens from plugins to enforce permission scopes.
    """
    async def dispatch(self, request: Request, call_next):
        # 1. Extract Token
        token = None
        auth_header = request.headers.get("Authorization")
        if auth_header and auth_header.startswith("Bearer "):
            token = auth_header.split(" ")[1]
        
        # Fallback to query param (for Iframe initial loads or SSE)
        if not token:
            token = request.query_params.get("token")

        if token:
            payload = TokenManager.verify_token(token)
            if payload:
                # 2. Attach Context
                request.state.plugin_id = payload.get("sub")
                request.state.permissions = set(payload.get("permissions", []))
                # logger.debug(f"🔑 Authenticated Request from Plugin: {request.state.plugin_id}")
                
                # [Optimization] If we want to enforce global bans here (e.g. Root-only APIs)
                # we could do it. For now, we just identify.
            else:
                # Invalid Token provided
                logger.warning(f"⚠️ Invalid Plugin Token on {request.url.path}")
                # We optionally block or just ignore (treat as anonymous)
                # If the client *tried* to auth and failed, maybe 401?
                # But browser might auto-send stale tokens.
                pass
        
        return await call_next(request)
