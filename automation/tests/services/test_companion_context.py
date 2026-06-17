from types import SimpleNamespace

import pytest

from core.protocol import EventPacket, EventType
from services.companion.context import CompanionContextResolver
from services.companion.identity import DEFAULT_USER_ID


class FakeSoulService:
    def __init__(self, character_id: str = "sakura"):
        self.character_id = character_id

    def get_active_character_id(self) -> str:
        return self.character_id


def test_resolver_uses_active_companion_when_request_omits_character():
    resolver = CompanionContextResolver(FakeSoulService("sakura"))

    context = resolver.resolve(user_id=None, character_id=None)

    assert context.user_id == DEFAULT_USER_ID
    assert context.character_id == "sakura"
    assert context.session_id == 0


def test_resolver_preserves_explicit_request_identity():
    resolver = CompanionContextResolver(FakeSoulService("sakura"))

    context = resolver.resolve(
        session_id=7,
        user_id="ada",
        character_id="lillian",
        user_name="Ada",
    )

    assert context.session_id == 7
    assert context.user_id == "ada"
    assert context.character_id == "lillian"
    assert context.user_name == "Ada"


def test_resolver_builds_context_from_event_packet():
    resolver = CompanionContextResolver(FakeSoulService("sakura"))
    packet = EventPacket(
        session_id=3,
        type=EventType.INPUT_TEXT,
        source="frontend",
        payload={"user_id": "ada", "character_id": "lillian", "user_name": "Ada"},
    )

    context = resolver.from_packet(packet)

    assert context.session_id == 3
    assert context.user_id == "ada"
    assert context.character_id == "lillian"
    assert context.user_name == "Ada"


def test_resolver_rejects_missing_soul_service():
    with pytest.raises(ValueError, match="requires SoulService"):
        CompanionContextResolver(None)


def test_resolver_rejects_empty_active_character():
    resolver = CompanionContextResolver(SimpleNamespace(get_active_character_id=lambda: ""))

    with pytest.raises(ValueError, match="not configured"):
        resolver.resolve()
