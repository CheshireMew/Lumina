"""Pydantic models for Lumina backend configuration."""

from typing import Any, Dict, Optional
import json
import os
from pathlib import Path

from pydantic import BaseModel, Field


def _load_configured_ports() -> Dict[str, int]:
    candidates = []
    app_root = os.environ.get("LUMINA_APP_ROOT")
    if app_root:
        candidates.append(Path(app_root) / "config" / "ports.json")
    candidates.append(Path(__file__).resolve().parents[2] / "config" / "ports.json")

    path = next((candidate for candidate in candidates if candidate.exists()), None)
    if path is None:
        searched = ", ".join(str(candidate) for candidate in candidates)
        raise FileNotFoundError(f"config/ports.json not found. Searched: {searched}")

    with open(path, "r", encoding="utf-8-sig") as handle:
        data = json.load(handle)
    return {
        "memory_port": int(data["memory_port"]),
        "stt_port": int(data["stt_port"]),
        "tts_port": int(data["tts_port"]),
        "vision_port": int(data["vision_port"]),
    }


CONFIGURED_PORTS = _load_configured_ports()


DEFAULT_SELECTED_PROVIDERS: Dict[str, str] = {
    "memory": "driver.memory.postgres",
    "stt": "driver.stt.sensevoice",
    "tts": "driver.tts.edge",
    "tool.search": "driver.tool.search.brave",
    "vision": "driver.vision.moondream",
}

FREE_LLM_PROVIDER_ID = "free_tier"
CUSTOM_LLM_PROVIDER_ID = "custom_provider"
POLLINATIONS_BASE_URL = "https://gen.pollinations.ai/v1"
POLLINATIONS_ANONYMOUS_CHAT_URL = "https://text.pollinations.ai/openai"
POLLINATIONS_ANONYMOUS_MODELS_URL = "https://text.pollinations.ai/models"
POLLINATIONS_DEFAULT_MODEL = "openai-fast"


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
    FREE_LLM_PROVIDER_ID: {
        "id": FREE_LLM_PROVIDER_ID,
        "type": "pollinations",
        "base_url": POLLINATIONS_BASE_URL,
        "api_key": "",
        "models": [POLLINATIONS_DEFAULT_MODEL],
        "enabled": True,
    },
    CUSTOM_LLM_PROVIDER_ID: {
        "id": CUSTOM_LLM_PROVIDER_ID,
        "type": "openai",
        "base_url": "http://localhost:11434/v1",
        "api_key": "",
        "models": [],
        "enabled": True,
    },
}


DEFAULT_LLM_ROUTE_DATA: Dict[str, Dict[str, Any]] = {
    "chat": {"feature": "chat", "provider_id": FREE_LLM_PROVIDER_ID, "model": POLLINATIONS_DEFAULT_MODEL},
    "memory": {"feature": "memory", "provider_id": FREE_LLM_PROVIDER_ID, "model": POLLINATIONS_DEFAULT_MODEL},
    "dreaming": {"feature": "dreaming", "provider_id": FREE_LLM_PROVIDER_ID, "model": POLLINATIONS_DEFAULT_MODEL},
    "evolution": {"feature": "evolution", "provider_id": FREE_LLM_PROVIDER_ID, "model": POLLINATIONS_DEFAULT_MODEL},
    "proactive": {"feature": "proactive", "provider_id": FREE_LLM_PROVIDER_ID, "model": POLLINATIONS_DEFAULT_MODEL},
    "vision": {"feature": "vision", "provider_id": FREE_LLM_PROVIDER_ID, "model": POLLINATIONS_DEFAULT_MODEL},
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
    vad_aggressiveness: int = Field(default=3, ge=0, le=3)
    speech_start_threshold: float = 0.6
    speech_end_threshold: float = 0.15
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
    memory_port: int = Field(default_factory=lambda: CONFIGURED_PORTS["memory_port"])
    stt_port: int = Field(default_factory=lambda: CONFIGURED_PORTS["stt_port"])
    tts_port: int = Field(default_factory=lambda: CONFIGURED_PORTS["tts_port"])
    vision_port: int = Field(default_factory=lambda: CONFIGURED_PORTS["vision_port"])
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
        if capability == "vision":
            return self.vision_port

        worker = self.workers.get(normalized)
        if worker:
            return worker.port
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
