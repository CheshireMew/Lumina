"""Pydantic models for Lumina backend configuration."""

from typing import Any, Dict, Optional

from pydantic import BaseModel, Field


class PostgresConfig(BaseModel):
    host: str = Field(default="localhost")
    port: int = Field(default=5432)
    user: str = Field(default="lumina_user")
    password: str = Field(default="lumina_password")
    database: str = Field(default="lumina_db")


class MemoryConfig(BaseModel):
    provider: str = Field(default="driver.memory.postgres")
    postgres: PostgresConfig = Field(default_factory=PostgresConfig)
    namespace: str = Field(default="lumina")
    database: str = Field(default="memory")
    character_id: str = Field(default="hiyori")
    history_limit: int = Field(default=20, ge=0, le=200)
    overflow_strategy: str = Field(default="slide", pattern="^(slide|reset)$")


class LLMConfig(BaseModel):
    api_key: str = Field(default="")
    base_url: str = Field(default="https://api.deepseek.com/v1")
    model: str = Field(default="deepseek-chat")


class STTConfig(BaseModel):
    provider: str = "sense-voice"
    model: str = "base"
    device: str = "cuda"
    compute_type: str = "float16"
    language: str = "zh"


class TTSConfig(BaseModel):
    provider: str = "edge-tts"
    voice: str = "zh-CN-XiaoxiaoNeural"


class AudioConfig(BaseModel):
    device_name: Optional[str] = None
    enable_voiceprint_filter: bool = True
    voiceprint_threshold: float = 0.45
    voiceprint_profile: str = "default"


class SearchConfig(BaseModel):
    provider: str = "brave"
    enabled: bool = True


class PluginsConfig(BaseModel):
    desired_state: Dict[str, bool] = Field(default_factory=dict)
    selected_providers: Dict[str, str] = Field(default_factory=dict)
    prewarm_core: bool = Field(default=True)
    settings: Dict[str, Dict[str, Any]] = Field(default_factory=dict)

    def is_enabled(self, plugin_id: str) -> bool:
        return self.desired_state.get(plugin_id, True)

    def is_disabled(self, plugin_id: str) -> bool:
        return not self.is_enabled(plugin_id)

    def set_enabled(self, plugin_id: str, enabled: bool):
        self.desired_state[plugin_id] = enabled

    def set_disabled(self, plugin_id: str, disabled: bool):
        self.set_enabled(plugin_id, not disabled)

class WorkerNodeConfig(BaseModel):
    host: str = "127.0.0.1"
    port: int
    id: str


class NetworkConfig(BaseModel):
    host: str = "127.0.0.1"
    memory_port: int = 8010
    stt_port: int = 8765
    tts_port: int = 8766
    bind_localhost_only: bool = True
    workers: Dict[str, WorkerNodeConfig] = Field(default_factory=dict)

    @property
    def stt_url(self) -> str:
        return f"http://{self.host}:{self.stt_port}"

    @property
    def tts_url(self) -> str:
        return f"http://{self.host}:{self.tts_port}"

    @property
    def memory_url(self) -> str:
        return f"http://{self.host}:{self.memory_port}"

    def get_worker_url(self, worker_id: str) -> str:
        from core.runtime import resolve_runtime_base_url

        url = resolve_runtime_base_url(self, worker_id)
        if not url:
            raise ValueError(f"Unknown worker: {worker_id}")
        return url


class ModelsConfig(BaseModel):
    stt_model_path: Optional[str] = None
    tts_model_path: Optional[str] = None
    embedding_model_name: str = "text-embedding-3-small"
