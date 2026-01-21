"""
REAL pytest tests for SessionManager - Testing actual session management
"""
import sys
from pathlib import Path
import pytest
import os
import shutil

# Add python_backend to path
PROJECT_ROOT = Path(__file__).parents[2]
sys.path.insert(0, str(PROJECT_ROOT / "python_backend"))

from services.session_manager import SessionManager, SessionState

@pytest.fixture
def temp_dir(tmp_path):
    d = tmp_path / "sessions"
    d.mkdir()
    return d

def test_session_lifecycle(temp_dir):
    manager = SessionManager(data_dir=str(temp_dir))
    user_id = "user1"
    char_id = "char1"
    
    # 1. Load (Creates new)
    session = manager.load_session(user_id, char_id)
    assert isinstance(session, SessionState)
    assert len(session.short_term_history) == 0
    
    # 2. Modify & Save
    session.short_term_history.append({"role": "user", "content": "hello"})
    manager.save_session(user_id, char_id, session)
    
    # 3. Reload
    manager._cache.clear() # Force disk read
    session2 = manager.load_session(user_id, char_id)
    assert len(session2.short_term_history) == 1
    assert session2.short_term_history[0]["content"] == "hello"
    
    # 4. Clear History
    manager.clear_history(user_id, char_id)
    session3 = manager.load_session(user_id, char_id)
    assert len(session3.short_term_history) == 0
    
    # 5. Clear Session (Delete file)
    manager.clear_session(user_id, char_id)
    assert not (temp_dir / "char1_user1.json").exists()
