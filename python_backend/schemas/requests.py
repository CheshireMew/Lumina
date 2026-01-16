"""
Pydantic Request/Response Models
Extracted from memory_server.py for shared use
"""
from pydantic import BaseModel, Field, field_validator
from typing import Dict, Any, List, Optional



class MessageModel(BaseModel):
    """Strict Chat Message Model"""
    role: str  # user, assistant, system
    content: str
    timestamp: Optional[float] = None
    name: Optional[str] = None


class ConfigRequest(BaseModel):
    """Memory Service Config Request"""
    base_url: str
    api_key: Optional[str] = "sk-dummy-key"
    model: Optional[str] = "deepseek-chat"
    embedder: Optional[str] = "paraphrase-multilingual-MiniLM-L12-v2"
    character_id: str = "hiyori"
    # Heartbeat Settings
    heartbeat_enabled: Optional[bool] = None
    proactive_threshold_minutes: Optional[float] = None
    proactive_chat_enabled: Optional[bool] = None # Added for completeness/future explicit explicit use
    galgame_mode_enabled: Optional[bool] = None
    soul_evolution_enabled: Optional[bool] = None # ⚙️ New toggle
    history_limit: Optional[int] = Field(default=20, ge=0, le=50) # 📜 New: Max context turns
    overflow_strategy: Optional[str] = Field(default="slide", pattern="^(slide|reset)$") # 🌊 slide=FIFO, reset=ClearAll
    
    @field_validator('base_url')
    @classmethod
    def validate_base_url(cls, v):
        """Validate base_url format"""
        if not v:
            # Allow empty base_url if we want? No, let's keep it required for now, or relax if needed.
            # But the error was API Key.
            # If user selects Custom but leaves URL empty?
            pass 
        return v
        
    # Removed validate_api_key to allow free/local usage


class AddMemoryRequest(BaseModel):
    """Add Memory Request"""
    user_id: str = "user"
    character_id: Optional[str] = None
    user_name: str = "User"
    character_name: str = Field(default="AI", alias="char_name")
    messages: List[MessageModel]

    class Config:
        populate_by_name = True


class SearchRequest(BaseModel):
    """Search Memory Request"""
    user_id: str
    character_id: Optional[str] = None
    query: str
    limit: Optional[int] = 10
    empower_factor: Optional[float] = 0.5


class ConsolidateRequest(BaseModel):
    """Consolidate History Request"""
    user_id: str = "user"
    character_id: Optional[str] = None
    user_name: str = "User"
    character_name: str = Field(default="AI", alias="char_name")
    messages: List[MessageModel]

    class Config:
        populate_by_name = True


class DreamRequest(BaseModel):
    """Deep Dreaming Request"""
    user_id: str = "user"
    character_id: Optional[str] = None
    user_name: str = "User"
    character_name: str = Field(default="AI", alias="char_name")

    class Config:
        populate_by_name = True


class UpdateIdentityRequest(BaseModel):
    """Update Identity Request"""
    name: str
    description: str


class UpdateUserNameRequest(BaseModel):
    """Update User Name Request"""
    user_name: str
