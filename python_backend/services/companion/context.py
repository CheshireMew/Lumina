from dataclasses import dataclass
from typing import Any, Optional

from core.protocol import EventPacket
from services.companion.identity import DEFAULT_SESSION_ID, DEFAULT_USER_ID


@dataclass(frozen=True)
class CompanionContext:
    session_id: int
    user_id: str
    character_id: str
    user_name: Optional[str] = None


class CompanionContextResolver:
    """Single request boundary for user/session/active companion identity."""

    def __init__(self, soul_service: Any, default_user_id: str = DEFAULT_USER_ID):
        if soul_service is None:
            raise ValueError("CompanionContextResolver requires SoulService")
        self.soul_service = soul_service
        self.default_user_id = default_user_id

    def active_character_id(self) -> str:
        character_id = str(self.soul_service.get_active_character_id() or "").strip()
        if not character_id:
            raise ValueError("Active companion character_id is not configured")
        return character_id

    def resolve(
        self,
        *,
        session_id: Any = DEFAULT_SESSION_ID,
        user_id: Optional[Any] = None,
        character_id: Optional[Any] = None,
        user_name: Optional[str] = None,
    ) -> CompanionContext:
        resolved_user_id = str(user_id or self.default_user_id).strip() or self.default_user_id
        resolved_character_id = str(character_id or self.active_character_id()).strip()
        if not resolved_character_id:
            raise ValueError("character_id must be configured")

        return CompanionContext(
            session_id=int(session_id or DEFAULT_SESSION_ID),
            user_id=resolved_user_id,
            character_id=resolved_character_id,
            user_name=user_name,
        )

    def from_packet(self, packet: EventPacket) -> CompanionContext:
        payload = packet.payload or {}
        return self.resolve(
            session_id=packet.session_id,
            user_id=payload.get("user_id"),
            character_id=payload.get("character_id"),
            user_name=payload.get("user_name"),
        )
