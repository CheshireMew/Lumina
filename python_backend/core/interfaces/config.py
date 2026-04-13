"""
Config Provider Interface
=========================

Abstract interface for configuration access.
Allows dependency injection and easier testing.

Usage:
    class MyService:
        def __init__(self, config: IConfigProvider):
            self._config = config
            voice = self._config.tts.voice
"""

from abc import ABC, abstractmethod
from typing import Any, Protocol, runtime_checkable


@runtime_checkable
class IConfigSection(Protocol):
    """Protocol for config sections (tts, stt, memory, etc.)"""
    pass


class IConfigProvider(ABC):
    """
    Abstract interface for configuration access.
    
    Implementations:
        - ConfigManager (app_config.py) - Production
        - MockConfigProvider - Testing
    
    Example:
        def __init__(self, config: IConfigProvider):
            self._config = config
            provider = self._config.get_selected_provider("tts")
    """
    
    @abstractmethod
    def get(self, section: str, key: str, default: Any = None) -> Any:
        """
        Get config value by section.key path.
        
        Args:
            section: Config section name (e.g., "tts", "memory")
            key: Key within section (e.g., "provider", "voice")
            default: Default value if not found
        
        Returns:
            Config value or default
        
        Example:
            voice = config.get("tts", "voice", "default")
        """
        pass

    @abstractmethod
    def get_selected_provider(self, capability: str, default: Any = None) -> Any:
        """Get the selected provider for a capability from the unified plugin config."""
        pass
    
    @abstractmethod
    def save(self) -> None:
        """Persist configuration to storage."""
        pass
        
    @property
    @abstractmethod
    def memory(self) -> Any:
        """Memory configuration section."""
        pass
    
    @property
    @abstractmethod
    def llm(self) -> Any:
        """LLM configuration section."""
        pass
    
    @property
    @abstractmethod
    def tts(self) -> Any:
        """TTS configuration section."""
        pass
    
    @property
    @abstractmethod
    def stt(self) -> Any:
        """STT configuration section."""
        pass
    
    @property
    @abstractmethod
    def network(self) -> Any:
        """Network configuration section."""
        pass
    
    @property
    @abstractmethod
    def plugins(self) -> Any:
        """Plugins configuration section."""
        pass
    
    @property
    @abstractmethod
    def audio(self) -> Any:
        """Audio configuration section."""
        pass


class MockConfigProvider(IConfigProvider):
    """
    Mock config provider for testing.
    
    Usage:
        mock_config = MockConfigProvider({
            "tts": {"provider": "edge-tts", "voice": "test"},
            "memory": {"provider": "mock"}
        })
        service = MyService(config=mock_config)
    """
    
    def __init__(self, data: dict = None):
        self._data = data or {}
        # Create mock sections
        for section_name in ["memory", "llm", "tts", "stt", "network", "plugins", "audio"]:
            setattr(self, f"_{section_name}", 
                    type(f"Mock{section_name.title()}", (), self._data.get(section_name, {}))())
    
    def get(self, section: str, key: str, default: Any = None) -> Any:
        section_data = self._data.get(section, {})
        return section_data.get(key, default)
    
    def save(self) -> None:
        """Mock save (no-op)"""
        pass

    def get_selected_provider(self, capability: str, default: Any = None) -> Any:
        providers = self._data.get("plugins", {}).get("selected_providers", {})
        return providers.get(capability, default)
    
    @property
    def memory(self): return self._memory
    
    @property
    def llm(self): return self._llm
    
    @property
    def tts(self): return self._tts
    
    @property
    def stt(self): return self._stt
    
    @property
    def network(self): return self._network
    
    @property
    def plugins(self): return self._plugins
    
    @property
    def audio(self): return self._audio
