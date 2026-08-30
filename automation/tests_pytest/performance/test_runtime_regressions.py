import asyncio
import json
import sqlite3
import statistics
import time
import uuid
from pathlib import Path

import numpy as np
import pytest

from provider_drivers.memory_sqlite.drivers.memory.sqlite_driver import SQLiteMemoryDriver
from services.companion.post_turn_journal import POST_TURN_STEPS, PostTurnJournal


pytestmark = pytest.mark.performance


@pytest.mark.anyio
async def test_indexed_memory_search_stays_responsive_at_10000_records(tmp_path: Path):
    driver = SQLiteMemoryDriver()
    driver.load_config({
        "data_root": str(tmp_path),
        "sqlite_file": "database/performance.sqlite3",
    })
    await driver.connect()
    generator = np.random.default_rng(20260824)
    embeddings = generator.standard_normal((10000, 384), dtype=np.float32)
    embeddings /= np.linalg.norm(embeddings, axis=1, keepdims=True)
    target_index = len(embeddings) - 1

    def seed(connection):
        connection.executemany(
            """
            INSERT INTO memory_items(id, character_id, content, embedding)
            VALUES (?, 'hiyori', ?, ?)
            """,
            [
                (
                    f"memory-{index}",
                    (
                        "唯一目标海边旅行记忆"
                        if index == target_index
                        else f"第 {index} 条普通记录"
                    ),
                    json.dumps(vector.tolist(), separators=(",", ":")),
                )
                for index, vector in enumerate(embeddings)
            ],
        )
        driver._rebuild_search_indexes(connection)
        connection.commit()

    await driver._run(seed)

    finished = asyncio.Event()
    event_loop_gaps = []

    async def watch_event_loop():
        previous = asyncio.get_running_loop().time()
        while not finished.is_set():
            await asyncio.sleep(0.005)
            current = asyncio.get_running_loop().time()
            event_loop_gaps.append(current - previous - 0.005)
            previous = current

    watcher = asyncio.create_task(watch_event_loop())
    await asyncio.sleep(0)
    started = time.perf_counter()
    results = await driver.search_hybrid(
        "唯一目标海边旅行记忆",
        embeddings[target_index].tolist(),
        "memory_items",
        5,
        0.25,
        0.4,
        {"character_id": "hiyori", "status": "active"},
    )
    elapsed = time.perf_counter() - started
    finished.set()
    await watcher
    await driver.close()

    print(
        f"indexed_memory_search records=10000 dimensions=384 elapsed_ms={elapsed * 1000:.1f} "
        f"max_event_loop_gap_ms={max(event_loop_gaps, default=0.0) * 1000:.1f}"
    )

    assert results[0]["id"] == f"memory-{target_index}"
    assert elapsed < 0.75, f"Indexed 10k search took {elapsed:.3f}s"
    assert max(event_loop_gaps, default=0.0) < 0.08, (
        f"Search blocked the event loop for {max(event_loop_gaps):.3f}s"
    )


@pytest.mark.anyio
async def test_post_turn_journal_has_bounded_completion_cost(tmp_path: Path):
    journal = PostTurnJournal(tmp_path / "post-turn", completed_retention=25)
    turn_timings = []
    for index in range(100):
        turn_id = f"turn-{index}-{uuid.uuid4().hex[:8]}"
        started = time.perf_counter()
        await journal.begin({"turn_id": turn_id})
        for step in POST_TURN_STEPS:
            await journal.mark_step(turn_id, step)
        await journal.mark_completed(turn_id)
        turn_timings.append(time.perf_counter() - started)

    started = time.perf_counter()
    pending = await journal.pending()
    pending_elapsed = time.perf_counter() - started
    def completed_count():
        with sqlite3.connect(journal.database_path) as connection:
            return connection.execute(
                "SELECT COUNT(*) FROM post_turn_records WHERE status = 'completed'"
            ).fetchone()[0]

    retained = await asyncio.to_thread(completed_count)
    p95 = statistics.quantiles(turn_timings, n=20)[18]
    print(
        f"post_turn_journal turns=100 total_ms={sum(turn_timings) * 1000:.1f} "
        f"p95_ms={p95 * 1000:.1f} pending_ms={pending_elapsed * 1000:.1f}"
    )

    assert pending == []
    assert retained == 25
    assert sum(turn_timings) < 2.0
    assert p95 < 0.035
    assert pending_elapsed < 0.05
    await journal.close()
