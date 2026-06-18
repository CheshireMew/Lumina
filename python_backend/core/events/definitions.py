from pydantic import BaseModel
from typing import Any

# --- System Lifecycle Events ---
class SystemReadyPayload(BaseModel):
    """Payload for system.ready"""
    timestamp: float
    modules_loaded: int
    services_available: list[str] = []

class SystemShutdownPayload(BaseModel):
    """Payload for system.shutdown"""
    reason: str = "user_request"

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
