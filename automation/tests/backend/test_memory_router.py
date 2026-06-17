from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock

import pytest

from routers.memory import (
    ClearContextRequest,
    add_memory,
    clear_context,
    get_all_memories,
    get_inspiration,
    search_memory,
    search_memory_hybrid,
)
from schemas.requests import AddMemoryRequest, MessageModel, SearchRequest
from services.companion.context import CompanionContext, CompanionContextResolver
from services.companion.identity import DEFAULT_USER_ID
from services.companion.interaction import CompanionInteractionRecorder

pytestmark = pytest.mark.anyio


class MemoryServiceStub:
    driver_id = "test-memory"

    def __init__(self):
        self.encoder = MagicMock(return_value=[0.1, 0.2])
        self.search_episodic = AsyncMock(return_value=[])
        self.search_episodic_hybrid = AsyncMock(return_value=[])
        self.log_conversation = AsyncMock(return_value="log-1")
        self.get_all_conversations = AsyncMock(return_value=[])
        self.get_inspiration = AsyncMock(return_value=[])


class SoulServiceStub:
    def __init__(self, character_id: str = "sakura"):
        self.character_id = character_id
        self.update_last_interaction = MagicMock()
        self.on_interaction = AsyncMock()

    def get_active_character_id(self) -> str:
        return self.character_id


async def test_memory_search_always_targets_episodic_memory():
    memory_service = MemoryServiceStub()
    context_resolver = CompanionContextResolver(SoulServiceStub("sakura"))
    request = SearchRequest(user_id="user", query="hello", limit=7)

    await search_memory(request, memory_service=memory_service, context_resolver=context_resolver)

    memory_service.search_episodic.assert_awaited_once()
    args, kwargs = memory_service.search_episodic.call_args
    assert args[1] == CompanionContext(session_id=0, user_id="user", character_id="sakura")
    assert kwargs["limit"] == 7


async def test_memory_hybrid_search_always_targets_episodic_memory():
    memory_service = MemoryServiceStub()
    context_resolver = CompanionContextResolver(SoulServiceStub("sakura"))
    request = SearchRequest(user_id="user", query="hello", limit=7)

    await search_memory_hybrid(request, memory_service=memory_service, context_resolver=context_resolver)

    memory_service.search_episodic_hybrid.assert_awaited_once()
    _, kwargs = memory_service.search_episodic_hybrid.call_args
    assert kwargs["context"] == CompanionContext(session_id=0, user_id="user", character_id="sakura")
    assert kwargs["limit"] == 7


async def test_add_memory_uses_soul_character_and_updates_interaction():
    memory_service = MemoryServiceStub()
    soul_service = SoulServiceStub("sakura")
    context_resolver = CompanionContextResolver(soul_service)
    interaction_recorder = CompanionInteractionRecorder(
        memory_service=memory_service,
        session_manager=SimpleNamespace(add_turn=AsyncMock()),
        soul_service=soul_service,
    )
    request = AddMemoryRequest(
        user_name="Ada",
        companion_name="Lumina",
        messages=[
            MessageModel(role="user", content="hello"),
            MessageModel(role="assistant", content="hi"),
        ],
    )

    response = await add_memory(
        request,
        memory_service=memory_service,
        context_resolver=context_resolver,
        interaction_recorder=interaction_recorder,
    )

    assert response == {"status": "success", "id": "log-1", "storage": "test-memory"}
    memory_service.log_conversation.assert_awaited_once_with(
        CompanionContext(session_id=0, user_id=DEFAULT_USER_ID, character_id="sakura"),
        "Ada: hello\nLumina: hi",
    )
    soul_service.update_last_interaction.assert_called_once_with()
    soul_service.on_interaction.assert_not_awaited()


async def test_get_all_memories_uses_soul_character_when_query_omits_character():
    memory_service = MemoryServiceStub()
    context_resolver = CompanionContextResolver(SoulServiceStub("sakura"))

    await get_all_memories(memory_service=memory_service, context_resolver=context_resolver)

    memory_service.get_all_conversations.assert_awaited_once_with(
        CompanionContext(session_id=0, user_id=DEFAULT_USER_ID, character_id="sakura")
    )


async def test_clear_context_uses_default_companion_user_when_request_omits_user(monkeypatch):
    session_manager = MagicMock()
    session_manager.clear_history = AsyncMock()
    context_resolver = CompanionContextResolver(SoulServiceStub("sakura"))

    class GatewayStub:
        publish_session_reset = AsyncMock()

    import routers.gateway as gateway_module

    monkeypatch.setattr(gateway_module, "gateway_service", GatewayStub())

    response = await clear_context(
        ClearContextRequest(),
        session_manager=session_manager,
        context_resolver=context_resolver,
    )

    assert response == {"status": "success", "message": "Short-term context cleared"}
    session_manager.clear_history.assert_awaited_once_with(
        CompanionContext(
            session_id=0,
            user_id=DEFAULT_USER_ID,
            character_id="sakura",
        )
    )


async def test_get_inspiration_uses_explicit_character_when_query_provides_character():
    memory_service = MemoryServiceStub()
    context_resolver = CompanionContextResolver(SoulServiceStub("sakura"))

    await get_inspiration(
        character_id="lillian",
        limit=2,
        memory_service=memory_service,
        context_resolver=context_resolver,
    )

    memory_service.get_inspiration.assert_awaited_once_with(
        CompanionContext(session_id=0, user_id=DEFAULT_USER_ID, character_id="lillian"),
        limit=2,
    )
