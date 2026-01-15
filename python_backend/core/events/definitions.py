from pydantic import BaseModel
from typing import Dict, Any, Optional

# --- System Lifecycle Events ---
class SystemReadyPayload(BaseModel):
    """Payload for system.ready"""
    timestamp: float
    modules_loaded: int
    services_available: list[str] = []

class SystemShutdownPayload(BaseModel):
    """Payload for system.shutdown"""
    reason: str = "user_request"

# --- Plugin Lifecycle Events ---
class PluginLoadedPayload(BaseModel):
    """Payload for plugin.loaded"""
    plugin_id: str
    version: str = "unknown"
    enabled: bool = True

class PluginErrorPayload(BaseModel):
    """Payload for plugin.error"""
    plugin_id: str
    error_type: str
    message: str
    traceback: Optional[str] = None
