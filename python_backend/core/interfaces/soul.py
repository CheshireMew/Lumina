from abc import ABC, abstractmethod
from typing import Dict, Any, Optional

class BaseSoulDriver(ABC):
    """
    Interface for the 'Soul' of the AI.
    A Soul Driver is responsible for:
    1. Defining the Persona (System Prompt).
    2. Managing Emotional/Memory State.
    3. Evolving over time based on interactions.
    """
    
    @property
    @abstractmethod
    def id(self) -> str:
        """Unique identifier for this driver (e.g., 'system.galgame')."""
        pass

    @property
    @abstractmethod
    def metadata(self) -> Dict[str, Any]:
        """Return static metadata (name, description, version)."""
        pass

    @abstractmethod
    async def init(self, config: Dict[str, Any] = None):
        """Initialize the driver with user configuration."""
        pass

    @abstractmethod
    async def get_system_prompt(self, context: Dict[str, Any] = {}) -> str:
        """
        Render the current system prompt.
        The Core calls this before every LLM interaction.
        """
        pass

    @abstractmethod
    async def on_interaction(self, user_input: str, ai_response: str, context: Dict[str, Any] = {}):
        """
        Hook called after a successful interaction.
        Use this to update mood, intimacy, XP, etc.
        """
        pass
    
    @abstractmethod
    def get_state(self) -> Dict[str, Any]:
        """
        Return serializable state for persistence (saved by Core).
        """
        pass
        
    @abstractmethod
    async def load_state(self, state: Dict[str, Any]):
        """
        Restore state from persistence.
        """
        pass
