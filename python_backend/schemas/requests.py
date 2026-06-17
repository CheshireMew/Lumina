"""
Pydantic Request/Response Models
Extracted from memory_server.py for shared use
"""
from pydantic import BaseModel
from typing import List, Optional



class MessageModel(BaseModel):
    """Strict Chat Message Model"""
    role: str  # user, assistant, system
    content: str
    timestamp: Optional[float] = None
    name: Optional[str] = None


class AddMemoryRequest(BaseModel):
    """Add Memory Request"""
    user_id: Optional[str] = None
    character_id: Optional[str] = None
    user_name: str = "User"
    companion_name: str = "AI"
    messages: List[MessageModel]


class SearchRequest(BaseModel):
    """Search Memory Request"""
    user_id: Optional[str] = None
    character_id: Optional[str] = None
    query: str
    limit: Optional[int] = 10
    empower_factor: Optional[float] = 0.5


