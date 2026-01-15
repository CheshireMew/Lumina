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
    entrypoint: str = Field(..., description="Format: 'module:Class' relative to plugin dir")
    
    # Metadata
    author: Optional[str] = None
    category: str = Field(default="system", description="Plugin category")
    tags: List[str] = Field(default_factory=list)
    
    # Dependencies & Permissions (Future Proofing)
    dependencies: List[str] = Field(default_factory=list, description="List of required Plugin IDs")
    permissions: List[str] = Field(default_factory=list, description="Requested capabilities")
    
    @field_validator("id")
    def validate_id(cls, v):
        if not re.match(r"^[a-z0-9_.]+$", v):
            raise ValueError("ID must consist of lowercase letters, numbers, underscores, and dots.")
        return v
    
    @field_validator("entrypoint")
    def validate_entrypoint(cls, v):
        if ":" not in v:
            raise ValueError("Entrypoint must be in 'module:Class' format")
        return v
