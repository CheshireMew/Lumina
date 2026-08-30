from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field

from config.defaults import (
    DEFAULT_TTS_PITCH,
    DEFAULT_TTS_PROVIDER_ID,
    DEFAULT_TTS_RATE,
    DEFAULT_TTS_VOICE,
)


class SttSwitchModelRequest(BaseModel):
    model_name: str


class UnifiedAudioConfig(BaseModel):
    device_name: str | None = None
    enable_voiceprint_filter: bool | None = None
    voiceprint_threshold: float | None = None
    voiceprint_profile: str | None = None
    vad_aggressiveness: int | None = None
    speech_start_threshold: float | None = None
    speech_end_threshold: float | None = None
    min_speech_frames: int | None = None


class TtsSynthesisRequest(BaseModel):
    text: str
    voice: str = DEFAULT_TTS_VOICE
    emotion: str | None = None
    engine: str = DEFAULT_TTS_PROVIDER_ID
    rate: str = DEFAULT_TTS_RATE
    pitch: str = DEFAULT_TTS_PITCH


class TtsSwitchRequest(BaseModel):
    driver_id: str | None = None
    model_name: str | None = None


class RuntimeCapabilitySnapshot(BaseModel):
    model_config = ConfigDict(extra="allow")

    capability: str
    contract_version: str = "1.0"
    runtime_id: str | None = None
    supported_operations: list[str] = Field(default_factory=list)
    selected_provider: str | None = None
    current_provider: str | None = None
    runtime_target: str
    worker_id: str
    worker_online: bool
    control_base_url: str
    direct_base_url: str | None = None
    stream_url: str | None = None
    token: str | None = None
    last_error: str | None = None
    load_time_ms: float | None = None
    status: Literal["starting", "ready", "offline", "unavailable", "failed"]
    provider_state: dict[str, Any] = Field(default_factory=dict)


class RuntimeCapabilitiesResponse(BaseModel):
    capabilities: list[RuntimeCapabilitySnapshot]


class SttModelInfo(BaseModel):
    id: str
    name: str
    type: str | None = None
    description: str = ""
    active: bool = False
    download_status: Literal["idle", "downloading", "completed", "failed"] | None = None


class SttModelListResponse(BaseModel):
    model_config = ConfigDict(extra="allow")

    current_model: str | None = None
    active_model: str | None = None
    engine_type: str | None = None
    engine: str | None = None
    loading_status: str = "idle"
    models: list[SttModelInfo] = Field(default_factory=list)
    vad_status: str | None = None


class AudioDeviceInfo(BaseModel):
    index: int
    name: str
    channels: int | None = None
    host_api: str | None = None


class AudioDeviceListResponse(BaseModel):
    devices: list[AudioDeviceInfo] = Field(default_factory=list)
    current: str | None = None


class OperationStatusResponse(BaseModel):
    model_config = ConfigDict(extra="allow")

    status: str
    detail: str | None = None


class VoiceprintStatusResponse(BaseModel):
    enabled: bool
    loaded: bool
    threshold: float
    profile: str | None = None
    profile_loaded: bool


class AudioStatusResponse(BaseModel):
    model_config = ConfigDict(extra="allow")

    device_name: str | None = None
    vad_aggressiveness: int | None = None
    speech_start_threshold: float
    speech_end_threshold: float
    min_speech_frames: int


class TtsEngineInfo(BaseModel):
    id: str
    name: str
    desc: str = ""
    enabled: bool = True
    type: str = "provider"
    config_schema: dict[str, Any] = Field(default_factory=dict)


class TtsModelListResponse(BaseModel):
    active: str | None = None
    engines: list[TtsEngineInfo] = Field(default_factory=list)


class TtsVoiceInfo(BaseModel):
    model_config = ConfigDict(extra="allow")

    name: str
    gender: str = "Unknown"


class CharacterAvatarModel(BaseModel):
    name: str
    path: str
    type: str
    thumbnail: str | None = None
    availability: str | None = None


class CharacterModelListResponse(BaseModel):
    models: list[CharacterAvatarModel]


class CompanionHistoryMessage(BaseModel):
    id: str
    turn_id: str
    role: Literal["user", "assistant", "system"]
    content: str
    reasoning: str = ""
    created_at: str


class CompanionHistoryResponse(BaseModel):
    session_id: int
    messages: list[CompanionHistoryMessage]
