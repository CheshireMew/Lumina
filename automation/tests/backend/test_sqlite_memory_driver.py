from pathlib import Path

import pytest

from provider_drivers.memory_sqlite.drivers.memory.sqlite_driver import SQLiteMemoryDriver
from memory.core import MemoryService
from services.companion.context import CompanionContext


@pytest.mark.anyio
async def test_sqlite_memory_driver_persists_crud_and_search(tmp_path: Path):
    driver = SQLiteMemoryDriver()
    driver.load_config({"data_root": str(tmp_path), "sqlite_file": "database/test.sqlite3"})
    await driver.connect()

    turn_id = await driver.create(
        "conversation_turns",
        {
            "session_id": 1,
            "user_id": "user",
            "character_id": "hiyori",
            "user_message": "记住海边",
            "assistant_message": "好",
            "narrative": "user: 记住海边\nhiyori: 好",
            "metadata": {"source": "test"},
        },
    )
    memory_id = await driver.create(
        "memory_items",
        {
            "character_id": "hiyori",
            "content": "用户喜欢海边",
            "embedding": [1.0, 0.0],
            "source_turn_ids": [turn_id],
            "metadata": {},
        },
    )

    rows = await driver.query(
        "SELECT * FROM conversation_turns WHERE character_id = $cid",
        {"cid": "hiyori"},
    )
    text_results = await driver.search_fulltext(
        "memory_items",
        "海边",
        5,
        ["content"],
        {"character_id": "hiyori", "status": "active"},
    )
    vector_results = await driver.search_vector(
        "memory_items",
        [1.0, 0.0],
        5,
        0.9,
        {"character_id": "hiyori", "status": "active"},
    )

    assert rows[0]["id"] == turn_id
    assert rows[0]["metadata"] == {"source": "test"}
    assert text_results[0]["id"] == memory_id
    assert vector_results[0]["score"] == pytest.approx(1.0)
    assert (tmp_path / "database" / "test.sqlite3").exists()

    assert await driver.update(
        "conversation_turns",
        turn_id,
        {"processed_at": "2026-08-23T00:00:00+00:00"},
    )
    await driver.mark_memories_hit([memory_id])
    updated = await driver.query(
        "SELECT hit_count FROM memory_items WHERE id = $id",
        {"id": memory_id},
    )
    assert updated[0]["hit_count"] == 1

    await driver.close()


@pytest.mark.anyio
async def test_sqlite_memory_path_cannot_escape_data_root(tmp_path: Path):
    driver = SQLiteMemoryDriver()
    driver.load_config({"data_root": str(tmp_path), "sqlite_file": "../outside.sqlite3"})

    with pytest.raises(ValueError, match="inside the Lumina data root"):
        await driver.connect()


@pytest.mark.anyio
async def test_empty_memory_search_does_not_load_the_embedding_model(tmp_path: Path):
    driver = SQLiteMemoryDriver()
    driver.load_config({"data_root": str(tmp_path), "sqlite_file": "database/empty.sqlite3"})
    service = MemoryService(driver)
    encoder_calls = []
    service.set_encoder(lambda text: encoder_calls.append(text) or [1.0, 0.0])
    await service.connect()

    result = await service.retrieve_context(
        "请记住这件事情",
        CompanionContext(session_id=1, user_id="user", character_id="hiyori"),
    )

    assert result == ""
    assert encoder_calls == []
    await service.close()
