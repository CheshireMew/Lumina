from unittest.mock import AsyncMock, MagicMock

import pytest

from routers.memory import add_memory, get_all_memories, get_inspiration, search_memory, search_memory_hybrid
from schemas.requests import AddMemoryRequest, MessageModel, SearchRequest

pytestmark = pytest.mark.anyio


class MemoryServiceStub:
    available = True
    degraded_reason = None
    driver_id = "test-memory"

    def __init__(self):
        self.encoder = MagicMock(return_value=[0.1, 0.2])
        self.search = AsyncMock(return_value=[])
        self.search_hybrid = AsyncMock(return_value=[])
        self.log_conversation = AsyncMock(return_value="log-1")
        self.get_all_conversations = AsyncMock(return_value=[])
        self.get_inspiration = AsyncMock(return_value=[])


class SoulServiceStub:
    def __init__(self, character_id: str = "sakura"):
        self.character_id = character_id
        self.update_last_interaction = MagicMock()

    def get_active_character_id(self) -> str:
        return self.character_id


async def test_memory_search_always_targets_episodic_memory():
    memory_service = MemoryServiceStub()
    soul_service = SoulServiceStub("sakura")
    request = SearchRequest(user_id="user", query="hello", limit=7)

    await search_memory(request, memory_service=memory_service, soul_service=soul_service)

    memory_service.search.assert_awaited_once()
    args, kwargs = memory_service.search.call_args
    assert args[1] == "sakura"
    assert kwargs["target_table"] == "episodic_memory"
    assert kwargs["limit"] == 7


async def test_memory_hybrid_search_always_targets_episodic_memory():
    memory_service = MemoryServiceStub()
    soul_service = SoulServiceStub("sakura")
    request = SearchRequest(user_id="user", query="hello", limit=7)

    await search_memory_hybrid(request, memory_service=memory_service, soul_service=soul_service)

    memory_service.search_hybrid.assert_awaited_once()
    _, kwargs = memory_service.search_hybrid.call_args
    assert kwargs["character_id"] == "sakura"
    assert kwargs["target_table"] == "episodic_memory"
    assert kwargs["limit"] == 7


async def test_add_memory_uses_soul_character_and_updates_interaction():
    memory_service = MemoryServiceStub()
    soul_service = SoulServiceStub("sakura")
    request = AddMemoryRequest(
        user_name="Ada",
        char_name="Lumina",
        messages=[
            MessageModel(role="user", content="hello"),
            MessageModel(role="assistant", content="hi"),
        ],
    )

    response = await add_memory(request, memory_service=memory_service, soul_service=soul_service)

    assert response == {"status": "success", "id": "log-1", "storage": "test-memory"}
    memory_service.log_conversation.assert_awaited_once_with(
        character_id="sakura",
        narrative="Ada: hello\nLumina: hi",
    )
    soul_service.update_last_interaction.assert_called_once_with()


async def test_get_all_memories_uses_soul_character_when_query_omits_character():
    memory_service = MemoryServiceStub()
    soul_service = SoulServiceStub("sakura")

    await get_all_memories(memory_service=memory_service, soul_service=soul_service)

    memory_service.get_all_conversations.assert_awaited_once_with(character_id="sakura")


async def test_get_inspiration_uses_explicit_character_when_query_provides_character():
    memory_service = MemoryServiceStub()
    soul_service = SoulServiceStub("sakura")

    await get_inspiration(
        character_id="lillian",
        limit=2,
        memory_service=memory_service,
        soul_service=soul_service,
    )

    memory_service.get_inspiration.assert_awaited_once_with(character_id="lillian", limit=2)
