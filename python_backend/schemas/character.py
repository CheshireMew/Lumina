from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field


class CharacterVoiceConfig(BaseModel):
    service: str = "edge-tts"
    voiceId: str = ""
    rate: str = "+0%"
    pitch: str = "+0Hz"


class CharacterBilibiliConfig(BaseModel):
    enabled: bool = False
    roomId: int = 0

    @classmethod
    def from_storage(cls, payload: Any) -> "CharacterBilibiliConfig":
        raw = payload if isinstance(payload, dict) else {}
        return cls(
            enabled=bool(raw.get("enabled", False)),
            roomId=int(raw.get("room_id", raw.get("roomId", 0)) or 0),
        )

    def to_storage(self) -> dict[str, Any]:
        return {
            "enabled": self.enabled,
            "room_id": self.roomId,
        }


class CharacterConfig(BaseModel):
    id: str
    name: str
    displayName: str | None = None
    description: str = ""
    systemPrompt: str = ""
    modelPath: str = ""
    voiceConfig: CharacterVoiceConfig = Field(default_factory=CharacterVoiceConfig)
    heartbeatEnabled: bool = True
    proactiveChatEnabled: bool = True
    galgameModeEnabled: bool = True
    soulEvolutionEnabled: bool = True
    proactiveThresholdMinutes: int = 15
    bilibili: CharacterBilibiliConfig = Field(default_factory=CharacterBilibiliConfig)
    metadata: dict[str, Any] = Field(default_factory=dict)

    @classmethod
    def from_storage(cls, character_id: str, payload: dict[str, Any] | None) -> "CharacterConfig":
        raw = dict(payload or {})
        voice_config = raw.get("voice_config") if isinstance(raw.get("voice_config"), dict) else {}
        return cls(
            id=raw.get("character_id") or raw.get("id") or character_id,
            name=raw.get("name") or character_id,
            displayName=raw.get("display_name") or raw.get("displayName") or raw.get("name") or character_id,
            description=raw.get("description", ""),
            systemPrompt=raw.get("system_prompt") or raw.get("systemPrompt", ""),
            modelPath=raw.get("model_path") or "",
            voiceConfig=CharacterVoiceConfig(
                service=voice_config.get("service", "edge-tts"),
                voiceId=voice_config.get("voiceId") or voice_config.get("voice_id", ""),
                rate=voice_config.get("rate", "+0%"),
                pitch=voice_config.get("pitch", "+0Hz"),
            ),
            heartbeatEnabled=raw.get("heartbeat_enabled", raw.get("heartbeatEnabled", True)) is not False,
            proactiveChatEnabled=raw.get("proactive_chat_enabled", raw.get("proactiveChatEnabled", True)) is not False,
            galgameModeEnabled=raw.get("galgame_mode_enabled", raw.get("galgameModeEnabled", True)) is not False,
            soulEvolutionEnabled=raw.get("soul_evolution_enabled", raw.get("soulEvolutionEnabled", True)) is not False,
            proactiveThresholdMinutes=int(raw.get("proactive_threshold_minutes", raw.get("proactiveThresholdMinutes", 15)) or 15),
            bilibili=CharacterBilibiliConfig.from_storage(raw.get("bilibili")),
            metadata=raw.get("metadata") if isinstance(raw.get("metadata"), dict) else {},
        )

    def to_storage(self) -> dict[str, Any]:
        return {
            "character_id": self.id,
            "name": self.name,
            "display_name": self.displayName or self.name,
            "description": self.description,
            "system_prompt": self.systemPrompt,
            "model_path": self.modelPath,
            "voice_config": self.voiceConfig.model_dump(),
            "heartbeat_enabled": self.heartbeatEnabled,
            "proactive_chat_enabled": self.proactiveChatEnabled,
            "galgame_mode_enabled": self.galgameModeEnabled,
            "soul_evolution_enabled": self.soulEvolutionEnabled,
            "proactive_threshold_minutes": self.proactiveThresholdMinutes,
            "bilibili": self.bilibili.to_storage(),
            "metadata": self.metadata,
        }


class CharacterListResponse(BaseModel):
    characters: list[CharacterConfig]
