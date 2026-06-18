from __future__ import annotations

from pydantic import BaseModel, Field
from typing import Any


class CharacterVoiceConfig(BaseModel):
    service: str = "edge-tts"
    voiceId: str = ""
    rate: str = "+0%"
    pitch: str = "+0Hz"


class CharacterAvatarConfig(BaseModel):
    type: str = "live2d"
    model: str = "Hiyori"
    modelUrl: str = ""
    cubismCoreUrl: str = ""
    rendererRuntimeUrl: str = ""


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
        return cls(
            id=raw.get("character_id") or raw.get("id") or character_id,
            name=raw.get("name") or character_id,
            displayName=raw.get("display_name") or raw.get("displayName") or raw.get("name") or character_id,
            description=raw.get("description", ""),
            systemPrompt=raw.get("system_prompt") or raw.get("systemPrompt", ""),
            avatar=CharacterAvatarConfig(
                type=avatar.get("type", "live2d"),
                model=avatar.get("model", "Hiyori"),
            ),
            voiceConfig=CharacterVoiceConfig(
                service=voice_config.get("service", "edge-tts"),
                voiceId=voice_config.get("voiceId") or voice_config.get("voice_id", ""),
                rate=voice_config.get("rate", "+0%"),
                pitch=voice_config.get("pitch", "+0Hz"),
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
            },
            "voice_config": self.voiceConfig.model_dump(),
            "heartbeat_enabled": self.heartbeatEnabled,
            "proactive_chat_enabled": self.proactiveChatEnabled,
            "soul_evolution_enabled": self.soulEvolutionEnabled,
            "proactive_threshold_minutes": self.proactiveThresholdMinutes,
            "metadata": self.metadata,
        }
