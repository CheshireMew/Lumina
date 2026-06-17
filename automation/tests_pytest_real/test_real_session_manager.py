from pathlib import Path

import pytest

from services.orchestrators.session import SessionManager, SessionState
from services.companion.context import CompanionContext
from services.repositories.file_session_repository import FileSessionRepository

pytestmark = pytest.mark.anyio


async def test_session_lifecycle(tmp_path: Path):
    repo = FileSessionRepository(tmp_path / "sessions")
    manager = SessionManager(repo=repo)
    context = CompanionContext(session_id=0, user_id="user1", character_id="char1")

    session = await manager.load_session(context)
    assert isinstance(session, SessionState)
    assert session.short_term_history == []

    session.short_term_history.append({"role": "user", "content": "hello"})
    await manager.save_session(context, session)

    manager._cache.clear()
    session2 = await manager.load_session(context)
    assert session2.short_term_history == [{"role": "user", "content": "hello"}]

    await manager.clear_history(context)
    session3 = await manager.load_session(context)
    assert session3.short_term_history == []

    await manager.clear_session(context)
    assert not (repo.root / "char1_user1.json").exists()
