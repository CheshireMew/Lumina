"""Pydantic models for Lumina backend configuration."""

from typing import Any, Dict, Optional

from pydantic import BaseModel, Field


DEFAULT_SELECTED_PROVIDERS: Dict[str, str] = {
    "memory": "driver.memory.postgres",
    "stt": "driver.stt.sensevoice",
    "tts": "driver.tts.edge",
    "tool.search": "driver.tool.search.brave",
    "vision": "driver.vision.moondream",
}


class PostgresConfig(BaseModel):
    host: str = Field(default="localhost")
    port: int = Field(default=5432)
    user: str = Field(default="lumina_user")
    password: str = Field(default="lumina_password")
    database: str = Field(default="lumina_db")


class MemoryConfig(BaseModel):
    postgres: PostgresConfig = Field(default_factory=PostgresConfig)
    namespace: str = Field(default="lumina")
    database: str = Field(default="memory")
    character_id: str = Field(default="hiyori")
    history_limit: int = Field(default=20, ge=0, le=200)
    overflow_strategy: str = Field(default="slide", pattern="^(slide|reset)$")


class LLMProviderConfig(BaseModel):
    id: str
    type: str = "openai"
    base_url: str = ""
    api_key: str = ""
    models: list[str] = Field(default_factory=list)
    enabled: bool = True


class LLMFeatureRoute(BaseModel):
    feature: str
    provider_id: str
    model: str
    temperature: float = 0.7
    top_p: float = 1.0
    presence_penalty: float = 0.0
    frequency_penalty: float = 0.0


DEFAULT_LLM_PROVIDER_DATA: Dict[str, Dict[str, Any]] = {
    "free_tier": {
        "id": "free_tier",
        "type": "pollinations",
        "base_url": "",
        "api_key": "none",
        "models": ["gpt-4o-mini", "claude-3-haiku"],
        "enabled": True,
    },
    "custom_provider": {
        "id": "custom_provider",
        "type": "openai",
        "base_url": "http://localhost:11434/v1",
        "api_key": "",
        "models": [],
        "enabled": True,
    },
}


DEFAULT_LLM_ROUTE_DATA: Dict[str, Dict[str, Any]] = {
    "chat": {"feature": "chat", "provider_id": "free_tier", "model": "gpt-4o-mini"},
    "memory": {"feature": "memory", "provider_id": "free_tier", "model": "gpt-4o-mini"},
    "dreaming": {"feature": "dreaming", "provider_id": "free_tier", "model": "gpt-4o-mini"},
    "evolution": {"feature": "evolution", "provider_id": "free_tier", "model": "gpt-4o-mini"},
    "proactive": {"feature": "proactive", "provider_id": "free_tier", "model": "gpt-4o-mini"},
    "vision": {"feature": "vision", "provider_id": "free_tier", "model": "gpt-4o"},
}


def _default_llm_providers() -> Dict[str, LLMProviderConfig]:
    return {
        provider_id: LLMProviderConfig(**provider_data)
        for provider_id, provider_data in DEFAULT_LLM_PROVIDER_DATA.items()
    }


def _default_llm_routes() -> Dict[str, LLMFeatureRoute]:
    return {
        route_id: LLMFeatureRoute(**route_data)
        for route_id, route_data in DEFAULT_LLM_ROUTE_DATA.items()
    }


class LLMConfig(BaseModel):
    providers: Dict[str, LLMProviderConfig] = Field(default_factory=_default_llm_providers)
    routes: Dict[str, LLMFeatureRoute] = Field(default_factory=_default_llm_routes)


class STTConfig(BaseModel):
    model: str = "base"
    device: str = "cuda"
    compute_type: str = "float16"
    language: str = "zh"


class TTSConfig(BaseModel):
    voice: str = "zh-CN-XiaoxiaoNeural"


class AudioConfig(BaseModel):
    device_name: Optional[str] = None
    speech_start_threshold: float = 0.6
    speech_end_threshold: float = 0.05
    min_speech_frames: int = 15
    enable_voiceprint_filter: bool = True
    voiceprint_threshold: float = 0.45
    voiceprint_profile: str = "default"


class SearchConfig(BaseModel):
    enabled: bool = True


class CapabilitiesConfig(BaseModel):
    desired_state: Dict[str, bool] = Field(default_factory=dict)
    selected_providers: Dict[str, str] = Field(default_factory=lambda: dict(DEFAULT_SELECTED_PROVIDERS))
    prewarm_core: bool = Field(default=True)
    supervise_workers: bool = Field(default=False)
    settings: Dict[str, Dict[str, Any]] = Field(default_factory=dict)

    def is_enabled(self, provider_id: str) -> bool:
        return self.desired_state.get(provider_id, True)

    def is_disabled(self, provider_id: str) -> bool:
        return not self.is_enabled(provider_id)

    def set_enabled(self, provider_id: str, enabled: bool):
        self.desired_state[provider_id] = enabled

    def set_disabled(self, provider_id: str, disabled: bool):
        self.set_enabled(provider_id, not disabled)

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

    def runtime_host(self, runtime_target: str) -> str:
        from core.runtime import MAIN_RUNTIME_TARGET, normalize_runtime_target

        normalized = normalize_runtime_target(runtime_target)
        if normalized == MAIN_RUNTIME_TARGET:
            return self.host
        worker = self.workers.get(normalized)
        return worker.host if worker else self.host

    def runtime_port(self, runtime_target: str) -> Optional[int]:
        from core.runtime import MAIN_RUNTIME_TARGET, normalize_runtime_target, runtime_target_to_capability

        normalized = normalize_runtime_target(runtime_target)
        if normalized == MAIN_RUNTIME_TARGET:
            return self.memory_port

        capability = runtime_target_to_capability(normalized)
        if capability == "stt":
            return self.stt_port
        if capability == "tts":
            return self.tts_port

        worker = self.workers.get(normalized)
        if worker:
            return worker.port
        if capability == "vision":
            return 8005
        return None

    def runtime_base_url(self, runtime_target: str) -> Optional[str]:
        port = self.runtime_port(runtime_target)
        if not port:
            return None
        return f"http://{self.runtime_host(runtime_target)}:{port}"

    def get_worker_url(self, worker_id: str) -> str:
        url = self.runtime_base_url(worker_id)
        if not url:
            raise ValueError(f"Unknown worker: {worker_id}")
        return url


class ModelsConfig(BaseModel):
    stt_model_path: Optional[str] = None
    tts_model_path: Optional[str] = None
    embedding_model_name: str = "text-embedding-3-small"
