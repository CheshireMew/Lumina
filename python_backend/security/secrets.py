"""
Lumina Secret Manager - Lightweight Credential Management

Provides a unified interface to access secrets from multiple backends:
1. Environment Variables (highest priority)
2. System Keyring (Windows Credential Manager / macOS Keychain)
3. Config File (fallback, lowest priority)

Usage:
    from security.secrets import SecretManager, SecretKey
    
    api_key = SecretManager.instance().get(SecretKey.OPENAI_API_KEY)
"""

import os
import logging
from abc import ABC, abstractmethod
from enum import Enum
from typing import Optional, List, Dict

logger = logging.getLogger("SecretManager")


class SecretKey(Enum):
    """
    Unified secret identifiers.
    Maps to environment variable names and keyring service keys.
    """
    # LLM API Keys
    OPENAI_API_KEY = "OPENAI_API_KEY"
    
    # Search API Keys
    BRAVE_API_KEY = "BRAVE_API_KEY"
    
    # Database Credentials
    POSTGRES_PASSWORD = "LUMINA_PG_PASSWORD"
    
    # Audio Service Keys
    FISH_AUDIO_API_KEY = "FISH_AUDIO_API_KEY"


class SecretBackend(ABC):
    """Abstract base class for secret storage backends."""
    
    @abstractmethod
    def get(self, key: SecretKey) -> Optional[str]:
        """Retrieve a secret value. Returns None if not found."""
        pass
    
    @abstractmethod
    def set(self, key: SecretKey, value: str) -> bool:
        """Store a secret value. Returns True on success."""
        pass
    
    @abstractmethod
    def delete(self, key: SecretKey) -> bool:
        """Remove a secret. Returns True on success."""
        pass
    
    @property
    @abstractmethod
    def name(self) -> str:
        """Human-readable backend name for logging."""
        pass


class EnvSecretBackend(SecretBackend):
    """
    Reads secrets from environment variables.
    Write operations are no-ops (env vars are read-only at runtime).
    """
    
    @property
    def name(self) -> str:
        return "Environment"
    
    def get(self, key: SecretKey) -> Optional[str]:
        value = os.environ.get(key.value)
        if value:
            logger.debug(f"🔑 [{self.name}] Found secret: {key.name}")
        return value
    
    def set(self, key: SecretKey, value: str) -> bool:
        # Environment variables are read-only in this context
        logger.warning(f"⚠️ [{self.name}] Cannot write to environment variables at runtime")
        return False
    
    def delete(self, key: SecretKey) -> bool:
        logger.warning(f"⚠️ [{self.name}] Cannot delete environment variables at runtime")
        return False


class KeyringSecretBackend(SecretBackend):
    """
    Uses system keyring for secure credential storage.
    - Windows: Credential Manager
    - macOS: Keychain
    - Linux: SecretService (GNOME Keyring / KWallet)
    """
    
    SERVICE_NAME = "Lumina"
    _available: Optional[bool] = None
    
    @property
    def name(self) -> str:
        return "Keyring"
    
    @classmethod
    def is_available(cls) -> bool:
        """Check if keyring is available on this system."""
        if cls._available is None:
            try:
                import keyring
                # Test if backend is functional
                keyring.get_keyring()
                cls._available = True
            except Exception as e:
                logger.debug(f"Keyring not available: {e}")
                cls._available = False
        return cls._available
    
    def get(self, key: SecretKey) -> Optional[str]:
        if not self.is_available():
            return None
        try:
            import keyring
            value = keyring.get_password(self.SERVICE_NAME, key.value)
            if value:
                logger.debug(f"🔑 [{self.name}] Found secret: {key.name}")
            return value
        except Exception as e:
            logger.warning(f"⚠️ [{self.name}] Error reading {key.name}: {e}")
            return None
    
    def set(self, key: SecretKey, value: str) -> bool:
        if not self.is_available():
            return False
        try:
            import keyring
            keyring.set_password(self.SERVICE_NAME, key.value, value)
            logger.info(f"✅ [{self.name}] Stored secret: {key.name}")
            return True
        except Exception as e:
            logger.error(f"❌ [{self.name}] Error storing {key.name}: {e}")
            return False
    
    def delete(self, key: SecretKey) -> bool:
        if not self.is_available():
            return False
        try:
            import keyring
            keyring.delete_password(self.SERVICE_NAME, key.value)
            logger.info(f"🗑️ [{self.name}] Deleted secret: {key.name}")
            return True
        except Exception as e:
            logger.warning(f"⚠️ [{self.name}] Error deleting {key.name}: {e}")
            return False


class SecretManager:
    """
    Facade for accessing secrets across multiple backends.
    Implements priority-based lookup: Env > Keyring > Config
    
    Singleton pattern - use SecretManager.instance()
    """
    
    _instance: Optional["SecretManager"] = None
    
    def __init__(self):
        self._backends: List[SecretBackend] = [
            EnvSecretBackend(),
        ]
        
        # Add keyring if available
        if KeyringSecretBackend.is_available():
            self._backends.append(KeyringSecretBackend())
        else:
            logger.info("ℹ️ Keyring not available, using env-only mode")
        
        # Config fallback is handled by ConfigManager, not here
        self._config_cache: Dict[SecretKey, str] = {}
    
    @classmethod
    def instance(cls) -> "SecretManager":
        """Get singleton instance."""
        if cls._instance is None:
            cls._instance = SecretManager()
        return cls._instance
    
    @classmethod
    def reset(cls):
        """Reset singleton (for testing)."""
        cls._instance = None
    
    def get(self, key: SecretKey, default: Optional[str] = None) -> Optional[str]:
        """
        Retrieve a secret from the first backend that has it.
        Falls back to default if not found in any backend.
        """
        for backend in self._backends:
            value = backend.get(key)
            if value:
                return value
        
        # Check config cache (set by ConfigManager during initialization)
        if key in self._config_cache:
            logger.debug(f"🔑 [Config] Found secret: {key.name}")
            return self._config_cache[key]
        
        if default:
            logger.debug(f"🔑 [Default] Using default for: {key.name}")
        return default
    
    def set(self, key: SecretKey, value: str, backend_name: str = "Keyring") -> bool:
        """
        Store a secret in the specified backend.
        Default: System Keyring (most secure writable backend)
        """
        for backend in self._backends:
            if backend.name == backend_name:
                return backend.set(key, value)
        logger.error(f"❌ Backend not found: {backend_name}")
        return False
    
    def set_config_fallback(self, key: SecretKey, value: str):
        """
        Register a config-based fallback value.
        Called by ConfigManager during initialization.
        """
        if value:  # Only cache non-empty values
            self._config_cache[key] = value
    
    def has_secret(self, key: SecretKey) -> bool:
        """Check if a secret exists in any backend."""
        return self.get(key) is not None
    
    def get_source(self, key: SecretKey) -> Optional[str]:
        """Return which backend provided the secret (for debugging)."""
        for backend in self._backends:
            if backend.get(key):
                return backend.name
        if key in self._config_cache:
            return "Config"
        return None
