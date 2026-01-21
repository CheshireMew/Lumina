from pydantic import BaseModel, Field
from typing import List, Optional, Literal, Dict, Any
from datetime import datetime

class PluginState(BaseModel):
    """
    [Architecture 6.1] Shared Plugin State Contract (Scheme C).
    Represents the LIVE status of a plugin, stored in SurrealDB 'plugin_registry' table.
    """
    id: str = Field(..., description="Unique Plugin ID (e.g. system.voiceprint)")
    name: str = Field(..., description="Human-readable name")
    category: str = Field(default="other", description="UI Category (stt, tts, system, tool)")
    
    # State
    active_status: Literal["starting", "ready", "error", "stopped", "transitioning", "unknown"] = Field(
        default="unknown", description="Current runtime lifecycle status"
    )
    desired_enabled: Optional[bool] = Field(default=None, description="Controller Intent (True=Enable, False=Disable, None=No Change)")
    enabled: bool = Field(default=False, description="Effective Enabled State (UI Legacy compatible)")
    
    # Location
    worker_id: str = Field(..., description="ID of the worker process hosting this plugin")
    runtime_target: str = Field(default="main", description="Target Runtime (main, stt_server, tts_server)")
    endpoint_url: Optional[str] = Field(default=None, description="Direct URL to reach this plugin (if applicable)")
    
    # Metadata
    capabilities: List[str] = Field(default_factory=list, description="List of provided capability strings")
    permissions: List[str] = Field(default_factory=list, description="Requested Permissions")
    config_schema: Optional[Dict[str, Any]] = Field(default=None, description="Form Schema for UI")
    ui_slots: List[Dict[str, Any]] = Field(default_factory=list, description="UI Components")
    
    group_id: Optional[str] = Field(default=None, description="Exclusive grouping ID")
    group_policy: Literal["exclusive", "independent"] = Field(default="independent")
    
    # Timestamps
    last_updated: datetime = Field(default_factory=datetime.utcnow)
    
    class Config:
        extra = "ignore" # Allow extra fields (like UI slots) but don't validate them strictly yet

class WorkerState(BaseModel):
    """
    [Architecture 6.1] Shared Worker Node Contract.
    Represents a running process (Main, STT, TTS) in the mesh.
    """
    worker_id: str = Field(..., description="Unique Worker ID (e.g. stt_server)")
    host: str = Field(default="127.0.0.1")
    port: int = Field(..., description="Main API Port")
    
    status: Literal["healthy", "degraded", "offline"] = "healthy"
    load: float = Field(default=0.0, description="System load (0.0 - 1.0)")
    
    last_seen: datetime = Field(default_factory=datetime.utcnow)
