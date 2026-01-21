
import logging
import contextvars
from typing import Any, Dict, Optional, Callable, List
from fastapi import FastAPI, APIRouter, Request
from fastapi.responses import JSONResponse
from pydantic import BaseModel

from core.events import get_event_bus

logger = logging.getLogger("RouterManager")

# [Architecture 7.0] Request Context Tracking
_request_resources: contextvars.ContextVar[List['SafeResource']] = contextvars.ContextVar("resources", default=[])

class SafeResource:
    """
    [Architecture 3.2] Resource Wrapper.
    Ensures that any handle (File, Lock, Stream) is automatically
    released at the end of a request context.
    """
    def __init__(self, resource: Any, cleanup_fn: Callable[[Any], None]):
        self.resource = resource
        self.cleanup_fn = cleanup_fn
        self._released = False

    def release(self):
        if not self._released:
            try:
                self.cleanup_fn(self.resource)
            except Exception as e:
                logger.error(f"Failed to release resource: {e}")
            finally:
                self._released = True

    @staticmethod
    def track(resource: Any, cleanup_fn: Callable[[Any], None]) -> Any:
        """Register a resource for auto-cleanup in current context."""
        sr = SafeResource(resource, cleanup_fn)
        current = _request_resources.get()
        current.append(sr)
        _request_resources.set(current)
        return resource

class RouterManager:
    """
    Manages dynamic route registration for Plugins.
    Decouples Plugins from FastAPI by acting as a Protocol Adapter.
    """
    def __init__(self, app: FastAPI, bus: Optional[Any] = None):
        self.app = app
        self.bus = bus if bus else get_event_bus()
        self.router_map: Dict[str, APIRouter] = {}
        
        # Subscribe to Registration Events
        self.bus.subscribe("core.register_route_def", self._handle_route_def)
        # self.bus.subscribe("core.register_router", self._handle_legacy_router) # Optional: Legacy Support

    def _handle_route_def(self, event: Any):
        """
        Handles generic route definition.
        Event.data: { ... }
        """
        try:
            payload = event.data
            plugin_id = payload["plugin_id"]
            path = payload["path"]
            method = payload["method"]
            handler = payload["handler"]
            response_model = payload.get("response_model")
            
            # 1. Get or Create Plugin Router
            router = self._get_plugin_router(plugin_id)
            
            # 2. Add Route to Router
            # We wrap the handler to ensure async compatibility if needed, 
            # though FastAPI handles async def fine.
            
            full_path = f"/plugins/{plugin_id}{path}"
            logger.info(f"🔗 Mounting Route Directly: [{method}] {full_path}")
            
            # DIRECT MOUNT TO APP (Bypasses APIRouter freeze)
            self.app.add_api_route(
                path=full_path,
                endpoint=handler,
                methods=[method],
                response_model=response_model,
                tags=[f"Plugin: {plugin_id}"]
            )
            
        except Exception as e:
            logger.error(f"Failed to mount route definition: {e}", exc_info=True)

    def _get_plugin_router(self, plugin_id: str) -> APIRouter:
        """Gets existing router or mounts a new one for the plugin."""
        if plugin_id in self.router_map:
            return self.router_map[plugin_id]
        
        # Create new APIRouter
        prefix = f"/plugins/{plugin_id}"
        router = APIRouter(prefix=prefix, tags=[f"Plugin: {plugin_id}"])
        
        # Mount to Main App
        # Note: Dynamic include_router in FastAPI might not update OpenAPI schema automatically 
        # without some hacks, but it usually works for routing.
        self.app.include_router(router)
        self.router_map[plugin_id] = router
        
        return router


    def unload_routes(self, plugin_id: str) -> int:
        """
        [Architecture 6.1] Dynamic Route Unloading.
        Removes all routes associated with the given plugin_id.
        Returns the number of routes removed.
        """
        target_tag = f"Plugin: {plugin_id}"
        removed_count = 0
        
        # 1. Filter Main Router Routes
        # FastAPI stores routes in app.router.routes (a list)
        # We must iterate and rebuild or remove in place. Rebuilding is safer for concurrency.
        
        original_count = len(self.app.router.routes)
        new_routes = []
        
        for route in self.app.router.routes:
            # Check Tags
            # APIRoute objects have 'tags' attribute (List[str] or Enum)
            route_tags = getattr(route, "tags", []) or []
            
            if target_tag in route_tags:
                removed_count += 1
                logger.debug(f"🗑️ Unloading Route: {route.path} [{route.methods}]")
                continue # Skip adding this route to new list
            
            new_routes.append(route)
            
        # 2. Apply Changes
        if removed_count > 0:
            self.app.router.routes = new_routes
            logger.info(f"✅ Unloaded {removed_count} routes for plugin {plugin_id}")
            
            # 3. Clean up cache map
            if plugin_id in self.router_map:
                del self.router_map[plugin_id]
        else:
            logger.debug(f"No routes found to unload for {plugin_id}")
            
        return removed_count
