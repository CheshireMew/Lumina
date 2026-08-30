import sys
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock

import pytest

PROJECT_ROOT = Path(__file__).parents[3]
sys.path.append(str(PROJECT_ROOT / "python_backend"))
sys.path.append(str(PROJECT_ROOT))

from services.companion.context import CompanionContext
from services.companion.context_pack import CompanionContextPackBuilder


def context() -> CompanionContext:
    return CompanionContext(
        session_id=1,
        user_id="user",
        character_id="hiyori",
    )


@pytest.mark.anyio
async def test_context_pack_builder_collects_session_memory_soul_and_runtime_state():
    session_manager = SimpleNamespace(
        load_session=AsyncMock(
            return_value=SimpleNamespace(
                short_term_history=[
                    {"role": "user", "content": "old"},
                    {"role": "assistant", "content": "reply"},
                ]
            )
        )
    )
    memory_service = SimpleNamespace(
        retrieve_context=AsyncMock(return_value="remembered fact")
    )
    soul_service = SimpleNamespace(
        get_system_prompt=AsyncMock(return_value="You are Hiyori."),
        get_active_character_id=MagicMock(return_value="hiyori"),
    )
    config = SimpleNamespace(
        capabilities=SimpleNamespace(
            selected_providers={"memory": "driver.memory.postgres"}
        )
    )

    builder = CompanionContextPackBuilder(
        session_manager=session_manager,
        memory_service=memory_service,
        soul_service=soul_service,
        config=config,
    )

    pack = await builder.build(
        companion_context=context(),
        user_message="what do I like?",
        history_limit=10,
    )

    assert pack.system_prompt == "You are Hiyori."
    assert pack.recent_session_history[0]["content"] == "old"
    assert pack.relevant_memories == "remembered fact"
    assert pack.current_soul_state == {"active_character_id": "hiyori"}
    assert pack.runtime_capabilities == {
        "selected_providers": {"memory": "driver.memory.postgres"}
    }
    memory_service.retrieve_context.assert_awaited_once()


@pytest.mark.anyio
async def test_context_pack_builder_retrieves_memory_for_fresh_session():
    session_manager = SimpleNamespace(
        load_session=AsyncMock(return_value=SimpleNamespace(short_term_history=[]))
    )
    memory_service = SimpleNamespace(
        retrieve_context=AsyncMock(return_value="fresh remembered fact")
    )
    soul_service = SimpleNamespace(
        get_system_prompt=AsyncMock(return_value="System"),
        get_active_character_id=MagicMock(return_value="hiyori"),
    )

    builder = CompanionContextPackBuilder(
        session_manager=session_manager,
        memory_service=memory_service,
        soul_service=soul_service,
    )

    pack = await builder.build(
        companion_context=context(),
        user_message="hello",
        history_limit=10,
    )

    assert pack.relevant_memories == "fresh remembered fact"
    memory_service.retrieve_context.assert_awaited_once()


def test_context_pack_builder_requires_dependencies():
    session_manager = SimpleNamespace()
    memory_service = SimpleNamespace()
    soul_service = SimpleNamespace()

    with pytest.raises(ValueError, match="SessionManager"):
        CompanionContextPackBuilder(
            session_manager=None,
            memory_service=memory_service,
            soul_service=soul_service,
        )

    with pytest.raises(ValueError, match="MemoryService"):
        CompanionContextPackBuilder(
            session_manager=session_manager,
            memory_service=None,
            soul_service=soul_service,
        )

    with pytest.raises(ValueError, match="SoulService"):
        CompanionContextPackBuilder(
            session_manager=session_manager,
            memory_service=memory_service,
            soul_service=None,
        )
