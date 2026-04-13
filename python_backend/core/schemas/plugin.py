from pydantic import BaseModel, Field, field_validator
from typing import List, Optional, Literal, Dict, Any
from datetime import datetime

from core.runtime import normalize_runtime_target

class PluginState(BaseModel):
    """
    [Architecture 6.1] Shared Plugin State Contract (Scheme C).
    Represents the live status of a plugin, stored in the lifecycle state store.
    """
    id: str = Field(..., description="Unique Plugin ID (e.g. system.voiceprint)")
    name: str = Field(..., description="Human-readable name")
    description: str = Field(default="", description="Human-readable description")
    kind: str = Field(default="system", description="Plugin kind")
    category: str = Field(default="other", description="UI Category (stt, tts, system, tool)")
    
    # State
    active_status: Literal["starting", "ready", "idle", "running", "healthy", "offline", "error", "stopped", "transitioning", "unknown"] = Field(
        default="unknown", description="Current runtime lifecycle status"
    )
    desired_enabled: Optional[bool] = Field(default=None, description="Controller Intent (True=Enable, False=Disable, None=No Change)")
    enabled: bool = Field(default=False, description="Effective Enabled State (UI Legacy compatible)")
    active: bool = Field(default=False, description="True when runtime is active")
    active_in_group: bool = Field(default=False, description="True when selected within an exclusive group")
    computed_status: str = Field(default="unknown", description="UI-friendly aggregated status")
    
    # Location
    worker_id: str = Field(default="main", description="ID of the worker process hosting this plugin")
    runtime_target: str = Field(default="main", description="Target Runtime (main, worker:stt, worker:tts, ...)")
    endpoint_url: Optional[str] = Field(default=None, description="Direct URL to reach this plugin (if applicable)")
    
    # Metadata
    capabilities: List[str] = Field(default_factory=list, description="List of provided capability strings")
    permissions: List[str] = Field(default_factory=list, description="Requested Permissions")
    config_schema: Optional[Dict[str, Any]] = Field(default=None, description="Form Schema for UI")
    current_config: Dict[str, Any] = Field(default_factory=dict, description="Current persisted config")
    ui_slots: List[Dict[str, Any]] = Field(default_factory=list, description="UI Components")
    
    group_id: Optional[str] = Field(default=None, description="Exclusive grouping ID")
    group_policy: Literal["exclusive", "independent"] = Field(default="independent")
    group_exclusive: bool = Field(default=False, description="Legacy exclusive-group flag")
    func_tag: str = Field(default="General", description="Display grouping for frontend")
    tags: List[str] = Field(default_factory=list, description="Display and behavior tags")
    error: Optional[str] = Field(default=None, description="Last load or runtime error")
    
    # Timestamps
    last_updated: datetime = Field(default_factory=datetime.utcnow)
    
    class Config:
        extra = "ignore" # Allow extra fields (like UI slots) but don't validate them strictly yet

    @field_validator("runtime_target", mode="before")
    @classmethod
    def normalize_runtime(cls, value):
        return normalize_runtime_target(str(value) if value is not None else None)

class WorkerState(BaseModel):
    """
    [Architecture 6.1] Shared Worker Node Contract.
    Represents a running process (Main, STT, TTS) in the mesh.
    """
    worker_id: str = Field(..., description="Unique Worker ID (e.g. worker:stt)")
    host: str = Field(default="127.0.0.1")
    port: int = Field(..., description="Main API Port")
    
    status: Literal["healthy", "degraded", "offline"] = "healthy"
    load: float = Field(default=0.0, description="System load (0.0 - 1.0)")
    
    last_seen: datetime = Field(default_factory=datetime.utcnow)


class PluginListResponse(BaseModel):
    items: List[PluginState]
