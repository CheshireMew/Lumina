from pydantic import BaseModel, Field, field_validator
from typing import List, Optional
import re

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
    is_exclusive: bool = Field(default=False, description="Whether this plugin demands exclusive control of its group")
    
    # Runtime Injected
    path: Optional[str] = Field(default=None, description="Absolute path to plugin directory (Injected at runtime)")
    
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
