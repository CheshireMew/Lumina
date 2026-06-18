import sys
from pathlib import Path
from unittest.mock import AsyncMock

import pytest

PROJECT_ROOT = Path(__file__).parents[3]
sys.path.insert(0, str(PROJECT_ROOT / "python_backend"))

from routers.memory import inspect_memory, inspect_processing_status
from services.companion.context import CompanionContextResolver


class FakeDriver:
    def __init__(self):
        self.queries = []

    async def query(self, sql: str, params: dict):
        self.queries.append({"sql": sql, "params": params})
        if "count(*)" in sql:
            return [{"count": 0}]
        return []


class FakeMemory:
    def __init__(self):
        self.driver = FakeDriver()


class FakeSoulService:
    def get_active_character_id(self) -> str:
        return "Sakura"


@pytest.mark.anyio
async def test_memory_inspection_uses_active_soul_character_when_query_omits_character():
    memory = FakeMemory()

    response = await inspect_memory(
        memory_service=memory,
        context_resolver=CompanionContextResolver(FakeSoulService()),
    )

    assert response["status"] == "success"
    assert {call["params"]["cid"] for call in memory.driver.queries} == {"sakura"}


@pytest.mark.anyio
async def test_memory_processing_status_uses_explicit_character_when_provided():
    memory = FakeMemory()

    await inspect_processing_status(
        character_id="Lillian",
        memory_service=memory,
        context_resolver=CompanionContextResolver(FakeSoulService()),
    )

    assert {call["params"]["cid"] for call in memory.driver.queries} == {"lillian"}
