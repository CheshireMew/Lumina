"""
Pydantic Request/Response Models
Extracted from memory_server.py for shared use
"""
from pydantic import BaseModel, Field
from typing import List, Optional



class MessageModel(BaseModel):
    """Strict Chat Message Model"""
    role: str  # user, assistant, system
    content: str
    timestamp: Optional[float] = None
    name: Optional[str] = None


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


