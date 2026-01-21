from pydantic import BaseModel, Field, field_validator
from typing import List, Optional
import re
# [Architecture 6.0] Capability Contract
# Use string forward reference in field definition to avoid circular imports at runtime if any, 
# but here it's safe to import as long as interfaces don't import manifest.
from core.interfaces.capability import CapabilityContract

class PluginManifest(BaseModel):
    """
    Schema for plugin.yaml/manifest.yaml files.
    Defines metadata, entrypoints, and dependencies.
    """
    id: str = Field(..., description="Unique plugin identifier (e.g. lumina.voiceprint)")
    version: str = Field(..., pattern=r"^\d+\.\d+\.\d+(-.*)?$", description="Semantic Version")
    name: str = Field(..., description="Human readable name")
    description: str = Field(default="", description="Brief description")
    
    # Entrypoints
    # Entrypoints
    entrypoint: Optional[str] = Field(default=None, description="Format: 'module:Class' relative to plugin dir. Optional for resource packs.")
    
    # Metadata
    author: Optional[str] = None
    category: str = Field(default="system", description="Plugin category")
    tags: List[str] = Field(default_factory=list)
    
    # Dependencies & Permissions (Future Proofing)
    dependencies: List[str] = Field(default_factory=list, description="List of required Plugin IDs")
    permissions: List[str] = Field(default_factory=list, description="Requested capabilities")
    
    # Execution Mode
    isolation_mode: str = Field(default="local", pattern="^(local|process)$", description="Execution isolation mode")
    is_exclusive: bool = Field(default=False, description="Legacy exclusive flag")
    
    # [Architecture 3.0] UI Grouping
    group_id: Optional[str] = Field(default=None, description="Group ID for mutually exclusive plugins (stt, tts)")
    group_exclusive: bool = Field(default=False, description="Whether this plugin demands exclusive control of its group")
    
    # [Architecture 2.0] Distributed Deployment
    runtime_target: str = Field(default="main", pattern="^(main|stt_server|tts_server)$", description="Which process this plugin should run in")
    
    # UI Integration
    # [Architecture 3.1] Strong UI Slot Validation
    class UiSlot(BaseModel):
        name: str
        slot: str
        src: str
        width: Optional[str] = None
        height: Optional[int] = None
        
    ui_slots: List[UiSlot] = Field(default_factory=list, description="UI Components to inject.")

    # [Architecture 6.0] Capability Contract
    provides: List['CapabilityContract'] = Field(default_factory=list, description="Capabilities provided by this plugin")
    consumes: List['CapabilityContract'] = Field(default_factory=list, description="Capabilities consumed by this plugin")

    # Runtime Injected
    path: Optional[str] = Field(default=None, description="Absolute path to plugin directory (Injected at runtime)")
    
    @field_validator("provides")
    def validate_capabilities(cls, v):
        """
        Enforce Pydantic Schema for reported capabilities.
        Prevents plugins from claiming 'stt.provider' without attributes.
        """
        from core.capabilities.schemas import validate_capability
        validated_list = []
        for cap in v:
            # If cap is already a dict (Pydantic model dump) or object
            # Convert to dict for validation if needed, or pass object if Compatible
            # CapabilityContract is the type.
            cap_dict = cap.model_dump() if hasattr(cap, "model_dump") else cap
            
            # This throws ValidationError if schema is violated
            validate_capability(cap_dict)
            validated_list.append(cap)
            
        return validated_list

    @field_validator("id")
    def validate_id(cls, v):
        if not re.match(r"^[a-z0-9_.]+$", v):
            raise ValueError("ID must consist of lowercase letters, numbers, underscores, and dots.")
        return v
    
    @field_validator("entrypoint")
    def validate_entrypoint(cls, v):
        if v is None or v.lower() == "none":
            return None
        if ":" not in v:
            raise ValueError("Entrypoint must be in 'module:Class' format")
        return v
