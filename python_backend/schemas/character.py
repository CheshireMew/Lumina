from __future__ import annotations

from pydantic import BaseModel, Field
from typing import Any

from config.defaults import (
    DEFAULT_LIVE2D_FIT_SCALE,
    DEFAULT_LIVE2D_IDLE_MOTION_GROUP,
    DEFAULT_LIVE2D_IDLE_THRESHOLD_MS,
    DEFAULT_LIVE2D_PARAMETER_IDS,
    DEFAULT_LIVE2D_TAP_HIT_AREA,
    DEFAULT_LIVE2D_TAP_MOTION_GROUP,
    DEFAULT_LIVE2D_TIME_SCALE,
    DEFAULT_LIVE2D_VERTICAL_POSITION_RATIO,
    DEFAULT_TTS_PITCH,
    DEFAULT_TTS_PROVIDER_ID,
    DEFAULT_TTS_RATE,
)


class CharacterVoiceConfig(BaseModel):
    service: str = DEFAULT_TTS_PROVIDER_ID
    voiceId: str = ""
    rate: str = DEFAULT_TTS_RATE
    pitch: str = DEFAULT_TTS_PITCH


class Live2DParameterBindings(BaseModel):
    eyeBlinkLeft: str = DEFAULT_LIVE2D_PARAMETER_IDS["eyeBlinkLeft"]
    eyeBlinkRight: str = DEFAULT_LIVE2D_PARAMETER_IDS["eyeBlinkRight"]
    mouthOpen: str = DEFAULT_LIVE2D_PARAMETER_IDS["mouthOpen"]
    headPan: str = DEFAULT_LIVE2D_PARAMETER_IDS["headPan"]
    headTilt: str = DEFAULT_LIVE2D_PARAMETER_IDS["headTilt"]
    headRoll: str = DEFAULT_LIVE2D_PARAMETER_IDS["headRoll"]
    bodyPan: str = DEFAULT_LIVE2D_PARAMETER_IDS["bodyPan"]


class Live2DBehaviorConfig(BaseModel):
    idleMotionGroup: str = DEFAULT_LIVE2D_IDLE_MOTION_GROUP
    tapMotionGroup: str = DEFAULT_LIVE2D_TAP_MOTION_GROUP
    tapHitArea: str = DEFAULT_LIVE2D_TAP_HIT_AREA
    idleThresholdMs: int = Field(default=DEFAULT_LIVE2D_IDLE_THRESHOLD_MS, ge=1_000)
    fitScale: float = Field(default=DEFAULT_LIVE2D_FIT_SCALE, gt=0)
    verticalPositionRatio: float = Field(
        default=DEFAULT_LIVE2D_VERTICAL_POSITION_RATIO,
        ge=0,
        le=1,
    )
    timeScale: float = Field(default=DEFAULT_LIVE2D_TIME_SCALE, gt=0)
    parameters: Live2DParameterBindings = Field(default_factory=Live2DParameterBindings)


class CharacterAvatarConfig(BaseModel):
    type: str = "live2d"
    model: str = ""
    modelUrl: str = ""
    cubismCoreUrl: str = ""
    rendererRuntimeUrl: str = ""
    behavior: Live2DBehaviorConfig = Field(default_factory=Live2DBehaviorConfig)


class CharacterConfig(BaseModel):
    id: str
    name: str
    displayName: str | None = None
    description: str = ""
    systemPrompt: str = ""
    avatar: CharacterAvatarConfig = Field(default_factory=CharacterAvatarConfig)
    voiceConfig: CharacterVoiceConfig = Field(default_factory=CharacterVoiceConfig)
    heartbeatEnabled: bool = True
    proactiveChatEnabled: bool = True
    soulEvolutionEnabled: bool = True
    proactiveThresholdMinutes: int = 15
    metadata: dict[str, Any] = Field(default_factory=dict)

    @classmethod
    def from_storage(cls, character_id: str, payload: dict[str, Any] | None) -> "CharacterConfig":
        raw = dict(payload or {})
        voice_config = raw.get("voice_config") if isinstance(raw.get("voice_config"), dict) else {}
        avatar = raw.get("avatar") if isinstance(raw.get("avatar"), dict) else {}
        service = str(voice_config.get("service") or DEFAULT_TTS_PROVIDER_ID)
        if service == "edge-tts":
            service = DEFAULT_TTS_PROVIDER_ID
        return cls(
            id=raw.get("character_id") or raw.get("id") or character_id,
            name=raw.get("name") or character_id,
            displayName=raw.get("display_name") or raw.get("displayName") or raw.get("name") or character_id,
            description=raw.get("description", ""),
            systemPrompt=raw.get("system_prompt") or raw.get("systemPrompt", ""),
            avatar=CharacterAvatarConfig(
                type=avatar.get("type", "live2d"),
                model=avatar.get("model", ""),
                behavior=avatar.get("behavior") or {},
            ),
            voiceConfig=CharacterVoiceConfig(
                service=service,
                voiceId=voice_config.get("voiceId") or voice_config.get("voice_id", ""),
                rate=voice_config.get("rate", DEFAULT_TTS_RATE),
                pitch=voice_config.get("pitch", DEFAULT_TTS_PITCH),
            ),
            heartbeatEnabled=raw.get("heartbeat_enabled", raw.get("heartbeatEnabled", True)) is not False,
            proactiveChatEnabled=raw.get("proactive_chat_enabled", raw.get("proactiveChatEnabled", True)) is not False,
            soulEvolutionEnabled=raw.get("soul_evolution_enabled", raw.get("soulEvolutionEnabled", True)) is not False,
            proactiveThresholdMinutes=int(raw.get("proactive_threshold_minutes", raw.get("proactiveThresholdMinutes", 15)) or 15),
            metadata=raw.get("metadata") if isinstance(raw.get("metadata"), dict) else {},
        )

    def to_storage(self) -> dict[str, Any]:
        return {
            "character_id": self.id,
            "name": self.name,
            "display_name": self.displayName or self.name,
            "description": self.description,
            "system_prompt": self.systemPrompt,
            "avatar": {
                "type": self.avatar.type,
                "model": self.avatar.model,
                "behavior": self.avatar.behavior.model_dump(),
            },
            "voice_config": self.voiceConfig.model_dump(),
            "heartbeat_enabled": self.heartbeatEnabled,
            "proactive_chat_enabled": self.proactiveChatEnabled,
            "soul_evolution_enabled": self.soulEvolutionEnabled,
            "proactive_threshold_minutes": self.proactiveThresholdMinutes,
            "metadata": self.metadata,
        }
