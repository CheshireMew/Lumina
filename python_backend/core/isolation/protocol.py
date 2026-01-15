from enum import Enum
from typing import Any, Dict, List, Optional
from pydantic import BaseModel

class CommandType(str, Enum):
    LOAD = "load"
    START = "start"
    STOP = "stop"
    TERMINATE = "terminate"
    UPDATE_CONFIG = "update_config"
    EVENT_EMIT = "event_emit" # Main -> Worker (for subscribed events)
    METHOD_CALL = "method_call" # FUTURE: Call generic method

class EventType(str, Enum):
    READY = "ready"
    ERROR = "error"
    LOG = "log"
    EVENT_EMIT = "event_emit" # Worker -> Main (bus.emit)
    REGISTER_ROUTER = "register_router"
    REGISTER_SERVICE = "register_service"
    SYNC_STATE = "sync_state" # Update 'enabled', 'status', etc.
    SAVE_DATA = "save_data"   # Worker -> Host (request persistence)
    UPDATE_CONFIG = "update_config" # Worker -> Host (update kv)

# --- Host -> Worker ---

class PluginCommand(BaseModel):
    id: str           # Correlation ID
    type: CommandType
    payload: Dict[str, Any] = {}

class LoadPayload(BaseModel):
    plugin_id: str
    manifest_path: str
    config: Dict[str, Any] = {}
    permissions: List[str] = []

class ConfigPayload(BaseModel):
    key: str
    value: Any

class EventEmitPayload(BaseModel):
    event_name: str
    data: Dict[str, Any]

# --- Worker -> Host ---

class PluginEvent(BaseModel):
    type: EventType
    plugin_id: str
    payload: Dict[str, Any] = {}

class LogPayload(BaseModel):
    level: str # info, warning, error, debug
    message: str

class ErrorPayload(BaseModel):
    message: str
    traceback: str

class RouterPayload(BaseModel):
    prefix: str
    # Note: We can't pass actual APIRouter objects over Pickle/IPC easily 
    # if they contain complex types. 
    # Strategy: Worker defines Router, Main mounts a "Proxy Router" that forwards HTTP?
    # OR: for V1 Isolation, we might limit Router support or use a different validation strategy.
    # For now, let's assume we might just signal that router exists, 
    # but strictly speaking, standard FastAPI routers must be in the MAIN process to serve requests.
    # CRITICAL: Remote Routers are HARD. 
    # Alternative: The Worker exposes a local port? Or we proxy requests?
    # Let's flag this as a limitation: Process-Isolated plugins might have limited Router support intially,
    # OR we use a standardized JSON-RPC style for API calls.
    pass 
