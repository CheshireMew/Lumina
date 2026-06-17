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

# --- Capability Lifecycle Events ---

class CapabilityLifecycleRequest(BaseModel):
    """
    Payload for capability.lifecycle.request_enable / request_disable
    UI -> Service
    """
    module_id: str
    requester: str = "ui" # ui, system, automation
    config_overrides: Optional[Dict[str, Any]] = None

class CapabilityLoadedPayload(BaseModel):
    """
    Payload for capability.lifecycle.enabled
    Service -> UI/Config
    """
    module_id: str
    version: str = "unknown"
    enabled: bool = True
    # [Architecture 4.2] Active Provider Info
    group_id: Optional[str] = None
    is_active_provider: bool = False

class CapabilityDisabledPayload(BaseModel):
    """
    Payload for capability.lifecycle.disabled
    Service -> UI/Config
    """
    module_id: str
    reason: str = "user_action"

class CapabilityErrorPayload(BaseModel):
    """
    Payload for capability.lifecycle.error
    Service -> UI
    """
    module_id: str
    error_type: str
    message: str
    traceback: Optional[str] = None

# --- Config Events ---

class ConfigUpdatedPayload(BaseModel):
    """
    Payload for config.updated
    Config -> UI
    """
    section: str # stt, tts, etc.
    key: str # provider, voice, etc.
    value: Any
    timestamp: float
