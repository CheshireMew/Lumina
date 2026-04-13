
from fastapi import Request
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import JSONResponse
import logging

logger = logging.getLogger("SystemGuard")

class PluginGuardMiddleware(BaseHTTPMiddleware):
    """
    [Architecture 5.0] The Gatekeeper.
    Intercepts all requests to /plugins/{plugin_id}/*
    Checks if plugin is ACTIVE using SystemPluginManager.
    If disabled -> 403 Forbidden.
    """
    def __init__(self, app, container):
        super().__init__(app)
        self.container = container

    async def dispatch(self, request: Request, call_next):
        path = request.url.path
        
        # Performance: Fail fast if not a plugin route
        if not path.startswith("/plugins/"):
            return await call_next(request)

        # Parse Plugin ID
        # Format: /plugins/{plugin_id}/...
        try:
            parts = path.split("/")
            if len(parts) < 3:
                return await call_next(request)
                
            plugin_id = parts[2]
            
            # [Architecture 5.0] Whitelist System Routes
            # These are management endpoints, not specific plugins.
            RESERVED_PATHS = {
                "list", "slots", "registry", "config", "toggle", 
                "upload", "search", "brave-key", "capabilities", "debug", "marketplace"
            }
            if plugin_id in RESERVED_PATHS:
                # [Security] Management Endpoints are Localhost Only
                # Prevents external network attacks if bound to 0.0.0.0
                client_host = request.client.host if request.client else "unknown"
                if client_host not in ("127.0.0.1", "::1", "localhost"):
                     logger.warning(f"🚨 Blocked external access to {path} from {client_host}")
                     return JSONResponse(status_code=403, content={"error": "Access Denied: Localhost Only"})

                return await call_next(request)
            
            # [Security] General Plugin Route Protection
            # For non-management routes, we Require:
            # 1. Localhost Origin OR
            # 2. Valid Plugin Token (set by ScopeGuard)
            client_host = request.client.host if request.client else "unknown"
            is_localhost = client_host in ("127.0.0.1", "::1", "localhost")
            has_token = getattr(request.state, "plugin_id", None) is not None
            
            if not is_localhost and not has_token:
                 logger.warning(f"🛡️ Blocked public access to {path} from {client_host} (No Token)")
                 return JSONResponse(status_code=403, content={"error": "Access Denied: Auth Required"})

            # Check Status
            spm = self.container.system_plugin_manager
            
            # If SPM not ready (booting), we might want to allow or block. 
            # Safest is to allow only if we can verify.
            if spm:
                # Active Check
                is_active = spm.is_plugin_active(plugin_id)
                if not is_active:
                     # Retry with 'system.' prefix (Common Alias)
                     if spm.is_plugin_active(f"system.{plugin_id}"):
                         is_active = True
                         # Optional: Rewrite request.path or params? 
                         # No, just allow pass-through, the router will handle or the plugin itself doesn't care about ID in path usually.
                         
                if not is_active:
                    logger.warning(f"🛡️ Blocked request to disabled plugin: {plugin_id} | Path: {path}")
                    return JSONResponse(
                        status_code=403, 
                        content={"error": "Plugin Disabled", "plugin_id": plugin_id}
                    )
            
        except Exception as e:
            logger.error(f"Guard Middleware Error: {e}")
            # Fail-closed: block request on guard error
            return JSONResponse(
                status_code=503,
                content={"error": "Plugin system temporarily unavailable"}
            )

        return await call_next(request)
