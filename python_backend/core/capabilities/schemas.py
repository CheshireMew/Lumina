from enum import Enum
from typing import Dict, List, Any
from pydantic import BaseModel, Field

class CapabilityType(str, Enum):
    """
    Standardized Capability Types (Registry).
    """
    STT_PROVIDER = "stt.provider"
    TTS_PROVIDER = "tts.provider"
    LLM_PROVIDER = "llm.provider"
    TOOL_EXECUTION = "tool.execution" # Internal tools
    SYSTEM_EXTENSION = "system.extension"
    MEMORY_STORE = "memory.store"


class BaseCapabilitySchema(BaseModel):
    """Base Contract for all Capabilities"""
    type: CapabilityType
    version: str = "1.0.0"
    attributes: Dict[str, Any] = Field(default_factory=dict)

    class Config:
        extra = "allow" 

class STTCapability(BaseCapabilitySchema):
    type: CapabilityType = CapabilityType.STT_PROVIDER
    attributes: Dict[str, Any] = {
        "models": [],     # List[str] e.g. ["whisper-base"]
        "streaming": True # bool
    }

class TTSCapability(BaseCapabilitySchema):
    type: CapabilityType = CapabilityType.TTS_PROVIDER
    attributes: Dict[str, Any] = {
        "voices": [],     # List[str]
        "languages": []   # List[str]
    }

class ToolCapability(BaseCapabilitySchema):
    """
    Contract for internal tool providers.
    Must provide a JSON Schema for parameters.
    """
    type: CapabilityType = CapabilityType.TOOL_EXECUTION
    # attributes must contain 'functions' or 'schema'
    
    @property
    def tools_schema(self) -> List[Dict]:
        """Return OpenAI-compatible tool definitions"""
        return self.attributes.get("tools", [])

def validate_capability(cap: Dict[str, Any]) -> BaseCapabilitySchema:
    """Factory to validate arbitrary dict against specific schema"""
    c_type = cap.get("type")
    
    if c_type == CapabilityType.STT_PROVIDER:
        return STTCapability(**cap)
    elif c_type == CapabilityType.TTS_PROVIDER:
        return TTSCapability(**cap)
    elif c_type == CapabilityType.TOOL_EXECUTION:
        return ToolCapability(**cap)
    
    return BaseCapabilitySchema(**cap)
