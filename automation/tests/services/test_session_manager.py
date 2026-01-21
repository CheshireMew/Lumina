"""
Unit tests for SessionManager
Tests session persistence, loading, saving, and history management
"""
import sys
import os
import json
import unittest
import tempfile
import shutil
from pathlib import Path
from unittest.mock import MagicMock, patch

# Fix Windows console encoding
if sys.platform == 'win32':
    import io
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8')

# Add project root and python_backend to path
PROJECT_ROOT = Path(__file__).parents[3]
sys.path.append(str(PROJECT_ROOT / "python_backend"))
sys.path.append(str(PROJECT_ROOT))

from services.session_manager import SessionManager, SessionState


class TestSessionManager(unittest.TestCase):
    def setUp(self):
        """Create a temporary directory for each test"""
        self.temp_dir = tempfile.mkdtemp()
        self.manager = SessionManager(data_dir=self.temp_dir)

    def tearDown(self):
        """Clean up temporary directory"""
        if os.path.exists(self.temp_dir):
            shutil.rmtree(self.temp_dir)

    def test_load_nonexistent_session_returns_default(self):
        """Test that loading a non-existent session returns default state"""
        state = self.manager.load_session("nonexistent_user", "nonexistent_char")

        self.assertIsInstance(state, SessionState)
        self.assertEqual(state.session_id, 0)
        self.assertEqual(len(state.short_term_history), 0)
        print("✅ Non-existent session returns default state")

    def test_save_and_load_session(self):
        """Test basic session persistence"""
        user_id = "test_user"
        char_id = "test_char"

        # Create a session state
        original_state = SessionState(
            session_id=123,
            short_term_history=[
                {"role": "user", "content": "Hello"},
                {"role": "assistant", "content": "Hi there!"}
            ],
            metadata={"test_key": "test_value"}
        )

        # Save it
        self.manager.save_session(user_id, char_id, original_state)

        # Load it back
        loaded_state = self.manager.load_session(user_id, char_id)

        self.assertEqual(loaded_state.session_id, 123)
        self.assertEqual(len(loaded_state.short_term_history), 2)
        self.assertEqual(loaded_state.short_term_history[0]["content"], "Hello")
        self.assertEqual(loaded_state.metadata["test_key"], "test_value")
        print("✅ Session save and load verified")

    def test_path_sanitization(self):
        """Test that user and character IDs are sanitized to prevent path traversal"""
        # These IDs contain potentially dangerous characters
        dangerous_user = "../../../etc/user"
        dangerous_char = "char:with|special*chars?"

        # Create and save a session with dangerous IDs
        state = SessionState(session_id=1)
        self.manager.save_session(dangerous_user, dangerous_char, state)

        # Check that the file was created with sanitized name
        files = list(Path(self.temp_dir).glob("*.json"))
        self.assertGreater(len(files), 0)
        # Filename should only contain safe characters
        safe_filename = files[0].name
        self.assertNotIn("..", safe_filename)
        self.assertNotIn("/", safe_filename)
        self.assertNotIn(":", safe_filename)
        print("✅ Path sanitization verified")

    def test_clear_history(self):
        """Test clearing history while preserving metadata"""
        user_id = "test_user"
        char_id = "test_char"

        # Create a session with history
        state = SessionState(
            session_id=1,
            short_term_history=[
                {"role": "user", "content": "Message 1"},
                {"role": "assistant", "content": "Response 1"},
                {"role": "user", "content": "Message 2"},
                {"role": "assistant", "content": "Response 2"}
            ],
            metadata={"important": "data"}
        )
        self.manager.save_session(user_id, char_id, state)

        # Clear history
        self.manager.clear_history(user_id, char_id)

        # Reload and verify
        reloaded = self.manager.load_session(user_id, char_id)
        self.assertEqual(len(reloaded.short_term_history), 0)
        self.assertEqual(reloaded.metadata["important"], "data")
        print("✅ History clearing preserves metadata")

    def test_clear_session_deletes_file(self):
        """Test that clear_session removes the session file"""
        user_id = "test_user"
        char_id = "test_char"

        # Create and save a session
        state = SessionState(session_id=1)
        self.manager.save_session(user_id, char_id, state)

        # Verify file exists
        path = self.manager._get_path(user_id, char_id)
        self.assertTrue(path.exists())

        # Clear session
        self.manager.clear_session(user_id, char_id)

        # Verify file is deleted
        self.assertFalse(path.exists())
        print("✅ Session deletion verified")

    def test_add_turn_with_history_limit(self):
        """Test add_turn with history limit enforcement"""
        user_id = "test_user"
        char_id = "test_char"

        # Mock config with history limit (limit refers to total messages, not turns)
        mock_config = MagicMock()
        mock_config.memory.history_limit = 6  # 3 turns * 2 messages
        mock_config.memory.overflow_strategy = "slide"

        with patch('app_config.config', mock_config):
            # Add multiple turns (5 turns = 10 messages)
            for i in range(5):
                self.manager.add_turn(user_id, char_id, f"User {i}", f"AI {i}")

        # Load and check history
        state = self.manager.load_session(user_id, char_id)
        # Should have 6 messages (3 turns * 2 messages each), limited from 10
        self.assertEqual(len(state.short_term_history), 6)
        # Should keep the latest messages
        self.assertEqual(state.short_term_history[0]["content"], "User 2")
        print("✅ History limit enforcement verified")

    def test_add_turn_reset_strategy(self):
        """Test add_turn with reset overflow strategy"""
        user_id = "test_user"
        char_id = "test_char"

        # Mock config with reset strategy
        mock_config = MagicMock()
        mock_config.memory.history_limit = 2
        mock_config.memory.overflow_strategy = "reset"

        with patch('app_config.config', mock_config):
            # Add 3 turns (exceeds limit of 2)
            for i in range(3):
                self.manager.add_turn(user_id, char_id, f"User {i}", f"AI {i}")

        # Load and check
        state = self.manager.load_session(user_id, char_id)
        # With reset strategy, should keep only last turn (2 messages)
        self.assertEqual(len(state.short_term_history), 2)
        self.assertEqual(state.short_term_history[0]["content"], "User 2")
        print("✅ Reset overflow strategy verified")

    def test_get_history(self):
        """Test get_history method"""
        user_id = "test_user"
        char_id = "test_char"

        # Create session with history
        state = SessionState(
            short_term_history=[
                {"role": "user", "content": "Q1"},
                {"role": "assistant", "content": "A1"}
            ]
        )
        self.manager.save_session(user_id, char_id, state)

        # Get history
        history = self.manager.get_history(user_id, char_id)
        self.assertEqual(len(history), 2)
        self.assertEqual(history[0]["content"], "Q1")
        print("✅ get_history verified")

    def test_update_history(self):
        """Test update_history replaces entire history"""
        user_id = "test_user"
        char_id = "test_char"

        # Create initial session
        state = SessionState(
            short_term_history=[{"role": "user", "content": "Old"}]
        )
        self.manager.save_session(user_id, char_id, state)

        # Update with new history
        new_history = [
            {"role": "user", "content": "New Q1"},
            {"role": "assistant", "content": "New A1"},
            {"role": "user", "content": "New Q2"}
        ]
        self.manager.update_history(user_id, char_id, new_history)

        # Verify replacement
        reloaded = self.manager.load_session(user_id, char_id)
        self.assertEqual(len(reloaded.short_term_history), 3)
        self.assertEqual(reloaded.short_term_history[0]["content"], "New Q1")
        print("✅ update_history replacement verified")

    def test_corrupted_json_recovery(self):
        """Test that corrupted JSON file returns default state"""
        user_id = "test_user"
        char_id = "test_char"

        # Create a corrupted JSON file
        path = self.manager._get_path(user_id, char_id)
        with open(path, "w") as f:
            f.write("{invalid json content")

        # Should return default state instead of crashing
        state = self.manager.load_session(user_id, char_id)
        self.assertEqual(state.session_id, 0)
        print("✅ Corrupted JSON recovery verified")

    def test_multiple_users_isolation(self):
        """Test that different users have isolated sessions"""
        # Create sessions for different users
        state1 = SessionState(session_id=1, metadata={"user": 1})
        state2 = SessionState(session_id=2, metadata={"user": 2})

        self.manager.save_session("user1", "char", state1)
        self.manager.save_session("user2", "char", state2)

        # Verify isolation
        loaded1 = self.manager.load_session("user1", "char")
        loaded2 = self.manager.load_session("user2", "char")

        self.assertEqual(loaded1.session_id, 1)
        self.assertEqual(loaded2.session_id, 2)
        print("✅ User session isolation verified")

    def test_concurrent_same_char_different_users(self):
        """Test sessions for same character with different users"""
        # Same character, different users
        state1 = SessionState(session_id=1)
        state2 = SessionState(session_id=2)

        self.manager.save_session("user1", "hiyori", state1)
        self.manager.save_session("user2", "hiyori", state2)

        loaded1 = self.manager.load_session("user1", "hiyori")
        loaded2 = self.manager.load_session("user2", "hiyori")

        self.assertEqual(loaded1.session_id, 1)
        self.assertEqual(loaded2.session_id, 2)
        print("✅ Multi-user same-char isolation verified")


if __name__ == "__main__":
    suite = unittest.TestLoader().loadTestsFromTestCase(TestSessionManager)
    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(suite)

    print("\n" + "="*60)
    print(f"Tests run: {result.testsRun}")
    print(f"Failures: {len(result.failures)}")
    print(f"Errors: {len(result.errors)}")
    if result.wasSuccessful():
        print("✅ All SessionManager tests passed!")
    print("="*60)
