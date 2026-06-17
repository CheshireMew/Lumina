from pathlib import Path
from types import SimpleNamespace

import pytest

from services.orchestrators.session import SessionManager, SessionState
from services.companion.context import CompanionContext
from services.companion.identity import DEFAULT_USER_ID
from services.repositories.file_session_repository import FileSessionRepository

pytestmark = pytest.mark.anyio


@pytest.fixture
def session_repo(tmp_path: Path) -> FileSessionRepository:
    return FileSessionRepository(tmp_path / "sessions")


@pytest.fixture
def manager(session_repo: FileSessionRepository) -> SessionManager:
    return SessionManager(repo=session_repo)


def companion_context(user_id: str = "test_user", character_id: str = "test_char") -> CompanionContext:
    return CompanionContext(session_id=0, user_id=user_id, character_id=character_id)


async def test_load_nonexistent_session_returns_default(manager: SessionManager):
    state = await manager.load_session(companion_context("nonexistent_user", "nonexistent_char"))

    assert isinstance(state, SessionState)
    assert state.session_id == 0
    assert state.short_term_history == []


async def test_save_and_load_session(manager: SessionManager):
    original = SessionState(
        session_id=123,
        short_term_history=[
            {"role": "user", "content": "Hello"},
            {"role": "assistant", "content": "Hi there!"},
        ],
        metadata={"test_key": "test_value"},
    )

    context = companion_context()
    await manager.save_session(context, original)
    manager._cache.clear()

    loaded = await manager.load_session(context)

    assert loaded.session_id == 123
    assert loaded.short_term_history[0]["content"] == "Hello"
    assert loaded.metadata["test_key"] == "test_value"


async def test_repository_sanitizes_session_paths(session_repo: FileSessionRepository):
    manager = SessionManager(repo=session_repo)

    await manager.save_session(
        companion_context("../../../etc/user", "char:with|special*chars?"),
        SessionState(session_id=1),
    )

    files = list(session_repo.root.glob("*.json"))
    assert files
    assert ".." not in files[0].name
    assert "/" not in files[0].name
    assert ":" not in files[0].name


async def test_repository_uses_companion_default_for_empty_user(session_repo: FileSessionRepository):
    manager = SessionManager(repo=session_repo)

    await manager.save_session(companion_context("", "char"), SessionState(session_id=1))

    path = session_repo.root / f"char_{DEFAULT_USER_ID}.json"
    assert path.exists()


async def test_repository_rejects_empty_character_id(session_repo: FileSessionRepository):
    manager = SessionManager(repo=session_repo)

    with pytest.raises(ValueError, match="char_id must be non-empty"):
        await manager.save_session(companion_context("test_user", ""), SessionState(session_id=1))


async def test_clear_history_preserves_metadata(manager: SessionManager):
    state = SessionState(
        session_id=1,
        short_term_history=[
            {"role": "user", "content": "Message 1"},
            {"role": "assistant", "content": "Response 1"},
        ],
        metadata={"important": "data"},
    )
    context = companion_context()
    await manager.save_session(context, state)

    await manager.clear_history(context)

    reloaded = await manager.load_session(context)
    assert reloaded.short_term_history == []
    assert reloaded.metadata["important"] == "data"


async def test_clear_session_deletes_file(session_repo: FileSessionRepository):
    manager = SessionManager(repo=session_repo)
    context = companion_context()
    await manager.save_session(context, SessionState(session_id=1))

    path = session_repo.root / "test_char_test_user.json"
    assert path.exists()

    await manager.clear_session(context)

    assert not path.exists()


async def test_add_turn_with_history_limit(session_repo: FileSessionRepository):
    config = SimpleNamespace(memory=SimpleNamespace(history_limit=6, overflow_strategy="slide"))
    manager = SessionManager(repo=session_repo, config=config)
    context = companion_context()

    for index in range(5):
        await manager.add_turn(context, f"User {index}", f"AI {index}")

    state = await manager.load_session(context)
    assert len(state.short_term_history) == 6
    assert state.short_term_history[0]["content"] == "User 2"


async def test_add_turn_reset_strategy(session_repo: FileSessionRepository):
    config = SimpleNamespace(memory=SimpleNamespace(history_limit=2, overflow_strategy="reset"))
    manager = SessionManager(repo=session_repo, config=config)
    context = companion_context()

    for index in range(3):
        await manager.add_turn(context, f"User {index}", f"AI {index}")

    state = await manager.load_session(context)
    assert len(state.short_term_history) == 2
    assert state.short_term_history[0]["content"] == "User 2"


async def test_get_and_update_history(manager: SessionManager):
    context = companion_context()
    await manager.save_session(context, SessionState(short_term_history=[{"role": "user", "content": "Old"}]))

    new_history = [
        {"role": "user", "content": "New Q1"},
        {"role": "assistant", "content": "New A1"},
    ]
    await manager.update_history(context, new_history)

    assert await manager.get_history(context) == new_history


async def test_multiple_users_are_isolated(manager: SessionManager):
    context1 = companion_context("user1", "char")
    context2 = companion_context("user2", "char")
    await manager.save_session(context1, SessionState(session_id=1, metadata={"user": 1}))
    await manager.save_session(context2, SessionState(session_id=2, metadata={"user": 2}))

    loaded1 = await manager.load_session(context1)
    loaded2 = await manager.load_session(context2)

    assert loaded1.session_id == 1
    assert loaded2.session_id == 2
