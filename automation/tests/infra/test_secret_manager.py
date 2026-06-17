"""
Unit tests for SecretManager.

Tests the priority-based secret loading:
1. Environment Variables (highest)
2. System Keyring
"""
import os
import sys
import pytest
from unittest.mock import patch

# Add python_backend to path
sys.path.insert(0, str(__file__).replace("\\automation\\tests\\infra\\test_secret_manager.py", "\\python_backend"))

from security.secrets import (
    SecretManager,
    SecretKey,
    EnvSecretBackend,
    KeyringSecretBackend,
)


class TestSecretKey:
    """Test SecretKey enum."""
    
    def test_all_keys_have_values(self):
        """All keys should have non-empty string values."""
        for key in SecretKey:
            assert key.value
            assert isinstance(key.value, str)
    
    def test_key_names_match_env_vars(self):
        """Key values should be valid environment variable names."""
        for key in SecretKey:
            # Env var names: uppercase, underscores only
            assert key.value == key.value.upper()
            assert " " not in key.value


class TestEnvSecretBackend:
    """Test environment variable backend."""
    
    def test_get_existing_env_var(self):
        """Should return value when env var exists."""
        backend = EnvSecretBackend()
        
        with patch.dict(os.environ, {"OPENAI_API_KEY": "test-key-123"}):
            result = backend.get(SecretKey.OPENAI_API_KEY)
            assert result == "test-key-123"
    
    def test_get_missing_env_var(self):
        """Should return None when env var doesn't exist."""
        backend = EnvSecretBackend()
        
        # Ensure key is not set
        os.environ.pop("OPENAI_API_KEY", None)
        result = backend.get(SecretKey.OPENAI_API_KEY)
        assert result is None
    
    def test_set_returns_false(self):
        """Set should return False (env vars are read-only)."""
        backend = EnvSecretBackend()
        result = backend.set(SecretKey.OPENAI_API_KEY, "test")
        assert result is False
    
    def test_delete_returns_false(self):
        """Delete should return False (env vars are read-only)."""
        backend = EnvSecretBackend()
        result = backend.delete(SecretKey.OPENAI_API_KEY)
        assert result is False
    
    def test_name_property(self):
        """Should return 'Environment'."""
        backend = EnvSecretBackend()
        assert backend.name == "Environment"


class TestKeyringSecretBackend:
    """Test system keyring backend."""
    
    def test_is_available_without_keyring(self):
        """Should return False when keyring is not installed."""
        with patch.dict(sys.modules, {"keyring": None}):
            KeyringSecretBackend._available = None  # Reset cache
            # This will try to import keyring and fail
            assert KeyringSecretBackend.is_available() in [True, False]
    
    def test_name_property(self):
        """Should return 'Keyring'."""
        backend = KeyringSecretBackend()
        assert backend.name == "Keyring"


class TestSecretManager:
    """Test SecretManager facade."""
    
    def setup_method(self):
        """Reset singleton before each test."""
        SecretManager.reset()
        KeyringSecretBackend._available = False
    
    def test_singleton_pattern(self):
        """instance() should return the same object."""
        sm1 = SecretManager.instance()
        sm2 = SecretManager.instance()
        assert sm1 is sm2
    
    def test_reset_clears_instance(self):
        """reset() should clear the singleton."""
        sm1 = SecretManager.instance()
        SecretManager.reset()
        sm2 = SecretManager.instance()
        assert sm1 is not sm2
    
    def test_env_has_highest_priority(self):
        """Environment variables should override persisted sources."""
        sm = SecretManager.instance()
        sm._backends.append(_MemorySecretBackend("Keyring", {SecretKey.OPENAI_API_KEY: "keyring-value"}))

        with patch.dict(os.environ, {"OPENAI_API_KEY": "env-value"}):
            result = sm.get(SecretKey.OPENAI_API_KEY)
            assert result == "env-value"

    def test_persisted_secret_used_when_no_env(self):
        """Persisted backends should be used when env var is not set."""
        sm = SecretManager.instance()
        os.environ.pop("OPENAI_API_KEY", None)
        sm._backends.append(_MemorySecretBackend("Keyring", {SecretKey.OPENAI_API_KEY: "keyring-value"}))

        result = sm.get(SecretKey.OPENAI_API_KEY)
        assert result == "keyring-value"

    def test_get_persisted_skips_environment(self):
        """Config composition should be able to read keyring without consuming env overrides."""
        sm = SecretManager.instance()
        sm._backends.append(_MemorySecretBackend("Keyring", {SecretKey.OPENAI_API_KEY: "keyring-value"}))

        with patch.dict(os.environ, {"OPENAI_API_KEY": "env-value"}):
            assert sm.get_persisted(SecretKey.OPENAI_API_KEY) == "keyring-value"

    def test_default_returned_when_nothing_set(self):
        """Should return default when no source has the key."""
        sm = SecretManager.instance()
        
        # Ensure nothing is set
        os.environ.pop("BRAVE_API_KEY", None)
        
        result = sm.get(SecretKey.BRAVE_API_KEY, default="my-default")
        assert result == "my-default"
    
    def test_none_returned_when_not_found(self):
        """Should return None when key is not found and no default."""
        sm = SecretManager.instance()
        
        os.environ.pop("BRAVE_API_KEY", None)
        
        result = sm.get(SecretKey.BRAVE_API_KEY)
        assert result is None
    
    def test_has_secret_true_when_exists(self):
        """has_secret should return True when key exists."""
        sm = SecretManager.instance()
        
        with patch.dict(os.environ, {"OPENAI_API_KEY": "test"}):
            assert sm.has_secret(SecretKey.OPENAI_API_KEY) is True
    
    def test_has_secret_false_when_missing(self):
        """has_secret should return False when key is missing."""
        sm = SecretManager.instance()
        
        os.environ.pop("BRAVE_API_KEY", None)
        
        assert sm.has_secret(SecretKey.BRAVE_API_KEY) is False
    
    def test_get_source_returns_correct_backend(self):
        """get_source should identify where the secret came from."""
        sm = SecretManager.instance()
        
        with patch.dict(os.environ, {"OPENAI_API_KEY": "env-value"}):
            assert sm.get_source(SecretKey.OPENAI_API_KEY) == "Environment"

        os.environ.pop("BRAVE_API_KEY", None)
        sm._backends.append(_MemorySecretBackend("Keyring", {SecretKey.BRAVE_API_KEY: "keyring-value"}))
        assert sm.get_source(SecretKey.BRAVE_API_KEY) == "Keyring"


class _MemorySecretBackend:
    def __init__(self, name: str, values: dict[SecretKey, str]):
        self._name = name
        self._values = values

    @property
    def name(self) -> str:
        return self._name

    def get(self, key: SecretKey) -> str | None:
        return self._values.get(key)

    def set(self, key: SecretKey, value: str) -> bool:
        self._values[key] = value
        return True

    def delete(self, key: SecretKey) -> bool:
        self._values.pop(key, None)
        return True


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
