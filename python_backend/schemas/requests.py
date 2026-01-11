"""
Pydantic 请求/响应模型
从 memory_server.py 提取，供各路由模块共享
"""
from pydantic import BaseModel, Field, field_validator
from typing import Dict, Any, List, Optional


class ConfigRequest(BaseModel):
    """Memory 服务配置请求"""
    base_url: str
    api_key: str
    model: Optional[str] = "deepseek-chat"
    embedder: Optional[str] = "paraphrase-multilingual-MiniLM-L12-v2"
    character_id: str = "hiyori"
    # Heartbeat Settings
    heartbeat_enabled: Optional[bool] = None
    proactive_threshold_minutes: Optional[float] = None
    proactive_chat_enabled: Optional[bool] = None # Added for completeness/future explicit explicit use
    galgame_mode_enabled: Optional[bool] = None
    soul_evolution_enabled: Optional[bool] = None # ⚡ New toggle
    
    @field_validator('base_url')
    @classmethod
    def validate_base_url(cls, v):
        """验证 base_url 格式"""
        if not v:
            raise ValueError('base_url cannot be empty')
        if not v.startswith(('http://', 'https://')):
            raise ValueError('base_url must start with http:// or https://')
        return v.rstrip('/')
    
    @field_validator('api_key')
    @classmethod
    def validate_api_key(cls, v):
        """验证 api_key 非空且长度合理"""
        if not v or len(v.strip()) < 8:
            raise ValueError('api_key must be at least 8 characters')
        return v.strip()


class AddMemoryRequest(BaseModel):
    """添加记忆请求"""
    user_id: str = "user"
    character_id: Optional[str] = None
    user_name: str = "User"
    character_name: str = Field(default="AI", alias="char_name")
    messages: List[Dict[str, Any]]

    class Config:
        populate_by_name = True


class SearchRequest(BaseModel):
    """记忆搜索请求"""
    user_id: str
    character_id: Optional[str] = None
    query: str
    limit: Optional[int] = 10
    empower_factor: Optional[float] = 0.5


class ConsolidateRequest(BaseModel):
    """历史整合请求"""
    user_id: str = "user"
    character_id: Optional[str] = None
    user_name: str = "User"
    character_name: str = Field(default="AI", alias="char_name")
    messages: List[Dict[str, Any]]

    class Config:
        populate_by_name = True


class DreamRequest(BaseModel):
    """深度整合/做梦请求"""
    user_id: str = "user"
    character_id: Optional[str] = None
    user_name: str = "User"
    character_name: str = Field(default="AI", alias="char_name")

    class Config:
        populate_by_name = True


class UpdateIdentityRequest(BaseModel):
    """更新身份信息请求"""
    name: str
    description: str


class UpdateUserNameRequest(BaseModel):
    """更新用户名请求"""
    user_name: str
