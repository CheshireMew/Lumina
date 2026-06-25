import sys
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

PROJECT_ROOT = Path(__file__).parents[2]
sys.path.insert(0, str(PROJECT_ROOT / "python_backend"))

from memory.core import MemoryService
from memory.factory import MemoryDriverFactory
from services.companion.context import CompanionContext


MEMORY_CONFIG = {
    "provider": "driver.memory.postgres",
    "postgres": {
        "host": "127.0.0.1",
        "port": 5432,
        "user": "lumina",
        "password": "",
        "database": "lumina",
    },
}


def companion_context(character_id: str = "test_char") -> CompanionContext:
    return CompanionContext(session_id=0, user_id="test_user", character_id=character_id)


@pytest.fixture
def memory_service():
    with patch("memory.factory.MemoryDriverFactory.create_driver") as mock_factory:
        driver = MagicMock()
        driver.id = "driver.memory.test"
        driver.connect = AsyncMock()
        driver.close = AsyncMock()
        driver.create = AsyncMock(return_value="msg_123")
        driver.query = AsyncMock(return_value=[])
        mock_factory.return_value = driver

        svc = MemoryService(driver=driver)
        return svc, driver


@pytest.mark.anyio
async def test_memory_service_init(memory_service):
    svc, driver = memory_service

    assert svc.driver is driver
    assert svc.driver_id == "driver.memory.test"
    assert svc.memory_items.driver is driver


@pytest.mark.anyio
async def test_memory_service_connect_delegates_to_driver(memory_service):
    svc, driver = memory_service

    await svc.connect()

    driver.connect.assert_awaited_once()


@pytest.mark.anyio
async def test_replace_driver_closes_existing_and_syncs_memory_store(memory_service):
    svc, old_driver = memory_service
    next_driver = MagicMock()
    next_driver.id = "driver.memory.next"
    next_driver.close = AsyncMock()

    await svc.replace_driver(next_driver)

    old_driver.close.assert_awaited_once()
    assert svc.driver is next_driver
    assert svc.driver_id == "driver.memory.next"
    assert svc.memory_items.driver is next_driver


@pytest.mark.anyio
async def test_record_turn_delegation(memory_service):
    svc, driver = memory_service
    svc.encoder = None

    result = await svc.record_turn(
        companion_context("test_char"),
        user_message="hello",
        assistant_message="world",
    )

    assert result == "msg_123"
    driver.create.assert_awaited_once()
    args, _ = driver.create.call_args
    assert args[0] == "conversation_turns"
    assert args[1]["character_id"] == "test_char"
    assert args[1]["user_message"] == "hello"
    assert args[1]["assistant_message"] == "world"


@pytest.mark.anyio
async def test_retrieve_context_flow(memory_service):
    svc, _ = memory_service
    mock_encoder = MagicMock(return_value=[0.1, 0.2])
    svc.set_encoder(mock_encoder)
    svc.search_memory_items_hybrid = AsyncMock(return_value=[{"content": "memory 1"}, {"content": "memory 2"}])

    context = await svc.retrieve_context("query test", companion_context("test_char"))

    assert "memory 1" in context
    assert "memory 2" in context
    svc.search_memory_items_hybrid.assert_awaited_once()


@pytest.mark.anyio
async def test_retrieve_context_fulltext_fallback_uses_companion_context(memory_service):
    svc, _ = memory_service
    svc.encoder = None
    svc._search_memory_items_fulltext = AsyncMock(return_value=[{"content": "fallback memory"}])

    context = await svc.retrieve_context("query test", companion_context("test_char"))

    assert context == "fallback memory"
    svc._search_memory_items_fulltext.assert_awaited_once_with(
        query="query test",
        context=companion_context("test_char"),
        limit=3,
        memory_types=None,
    )


def test_memory_service_does_not_expose_old_memory_api(memory_service):
    svc, _ = memory_service

    assert hasattr(svc, "record_turn")
    assert hasattr(svc, "create_memory_item")
    assert hasattr(svc, "search_memory_items")
    assert not hasattr(svc, "search")
    assert not hasattr(svc, "search_fulltext")
    assert not hasattr(svc, "search_hybrid")


@pytest.mark.anyio
async def test_memory_stats_require_companion_context(memory_service):
    svc, driver = memory_service
    driver.query = AsyncMock(
        side_effect=[
            [{"count": 3}],
            [{"count": 5}],
        ]
    )

    stats = await svc.get_stats(companion_context("test_char"))

    assert stats == {"memories": 3, "turns": 5}
    assert driver.query.await_args_list[0].args[1] == {"cid": "test_char"}
    assert driver.query.await_args_list[1].args[1] == {"cid": "test_char"}


@pytest.mark.anyio
async def test_memory_stats_query_failure_propagates(memory_service):
    svc, driver = memory_service
    driver.query = AsyncMock(side_effect=RuntimeError("stats query failed"))

    with pytest.raises(RuntimeError, match="stats query failed"):
        await svc.get_stats(companion_context("test_char"))


@pytest.mark.anyio
async def test_unprocessed_turns_require_companion_context(memory_service):
    svc, driver = memory_service
    driver.query = AsyncMock(return_value=[{"id": "log-1", "narrative": "hello"}])

    results = await svc.get_unprocessed_turns(
        companion_context("test_char"),
        limit=7,
    )

    assert results == [{"id": "log-1", "narrative": "hello"}]
    driver.query.assert_awaited_once()
    _, params = driver.query.await_args.args
    assert params == {"cid": "test_char", "limit": 7}


@pytest.mark.anyio
async def test_unprocessed_turn_query_failure_propagates(memory_service):
    svc, driver = memory_service
    driver.query = AsyncMock(side_effect=RuntimeError("unprocessed query failed"))

    with pytest.raises(RuntimeError, match="unprocessed query failed"):
        await svc.get_unprocessed_turns(companion_context("test_char"))


@pytest.mark.anyio
async def test_mark_turns_processed_failure_propagates(memory_service):
    svc, driver = memory_service
    driver.query = AsyncMock(side_effect=RuntimeError("mark processed failed"))

    with pytest.raises(RuntimeError, match="mark processed failed"):
        await svc.mark_turns_processed(["log-1", "log-2"])

    driver.query.assert_awaited_once()


@pytest.mark.anyio
async def test_conversation_queries_parse_driver_rows(memory_service):
    svc, driver = memory_service
    driver.query = AsyncMock(return_value=[{"id": "log-1", "narrative": "hello"}])

    all_items = await svc.get_all_turns(companion_context("test_char"))
    recent_items = await svc.get_recent_turns(
        companion_context("test_char"),
        limit=3,
    )

    assert all_items == [{"id": "log-1", "narrative": "hello"}]
    assert recent_items == [{"id": "log-1", "narrative": "hello"}]
    assert driver.query.await_count == 2


@pytest.mark.anyio
async def test_all_conversations_query_failure_propagates(memory_service):
    svc, driver = memory_service
    driver.query = AsyncMock(side_effect=RuntimeError("conversation query failed"))

    with pytest.raises(RuntimeError, match="conversation query failed"):
        await svc.get_all_turns(companion_context("test_char"))


@pytest.mark.anyio
async def test_inspiration_parses_driver_rows(memory_service):
    svc, driver = memory_service
    driver.query = AsyncMock(
        return_value=[
            {"id": "mem-1", "content": "one"},
            {"id": "mem-2", "content": "two"},
        ]
    )

    items = await svc.get_inspiration(companion_context("test_char"), limit=1)

    assert len(items) == 1
    assert items[0]["id"] in {"mem-1", "mem-2"}


@pytest.mark.anyio
async def test_inspiration_query_failure_propagates(memory_service):
    svc, driver = memory_service
    driver.query = AsyncMock(side_effect=RuntimeError("inspiration query failed"))

    with pytest.raises(RuntimeError, match="inspiration query failed"):
        await svc.get_inspiration(companion_context("test_char"), limit=1)


@pytest.mark.anyio
async def test_retrieve_context_search_failure_propagates(memory_service):
    svc, _ = memory_service
    svc.encoder = None
    svc._search_memory_items_fulltext = AsyncMock(side_effect=RuntimeError("search failed"))

    with pytest.raises(RuntimeError, match="search failed"):
        await svc.retrieve_context("query test", companion_context("test_char"))


def test_memory_driver_factory_returns_configured_driver_only(monkeypatch):
    from core.interfaces.driver import BaseMemoryDriver

    class FakeMemoryDriver(BaseMemoryDriver):
        async def connect(self): pass
        async def close(self): pass
        async def initialize_schema(self): pass
        async def create(self, table, data): return "id"
        async def update(self, table, id, data): return True
        async def delete(self, table, id): return True
        def get_query_builder(self): return None
        async def query(self, sql, params=None): return []
        async def mark_memories_hit(self, memory_ids): pass
        async def search_vector(self, table, vector, limit, threshold, filter_criteria=None): return []
        async def search_fulltext(self, table, query, limit, fields, filter_criteria=None): return []
        async def search_hybrid(self, query, vector, table, limit, threshold, vector_weight=0.5, filter_criteria=None): return []

    postgres_driver = FakeMemoryDriver("driver.memory.postgres", "Postgres")
    postgres_driver.load_config = MagicMock()

    monkeypatch.setitem(
        MemoryDriverFactory._drivers,
        "driver.memory.postgres",
        lambda: postgres_driver,
    )
    driver = MemoryDriverFactory.create_driver(
        "driver.memory.postgres",
        driver_config=MEMORY_CONFIG,
    )

    assert driver is postgres_driver
    postgres_driver.load_config.assert_called_once_with(MEMORY_CONFIG)


def test_memory_driver_factory_rejects_missing_configured_driver():
    with pytest.raises(ImportError, match="driver.memory.missing"):
        MemoryDriverFactory.create_driver("driver.memory.missing")


def test_memory_service_requires_explicit_driver():
    with pytest.raises(ValueError, match="explicit memory driver"):
        MemoryService(driver=None)
