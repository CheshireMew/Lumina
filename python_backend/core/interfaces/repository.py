"""
Repository Interfaces
=====================
Defines the contract for data access, decoupling business logic from storage implementation.
"""

from abc import ABC, abstractmethod
from typing import TypeVar, Generic, Optional, List, Dict, Any

T = TypeVar("T")

class IRepository(Generic[T], ABC):
    """Generic Repository Interface for CRUD operations."""
    
    @abstractmethod
    async def get(self, id: str) -> Optional[T]:
        """Retrieve an entity by ID."""
        pass
    
    @abstractmethod
    async def save(self, entity: T) -> bool:
        """Save or update an entity."""
        pass

    @abstractmethod
    async def delete(self, id: str) -> bool:
        """Delete an entity by ID."""
        pass

class ISoulRepository(ABC):
    """
    Repository for Soul (Character) Configuration and State.
    Not strictly a generic repository since 'Soul' is a complex aggregate.
    """
    
    @abstractmethod
    def set_character_id(self, character_id: str):
        """Switch the context of the repository to a specific character."""
        pass

    @abstractmethod
    def get_character_id(self) -> str:
        """Get currently active character ID."""
        pass

    @abstractmethod
    def load_config(self) -> Dict[str, Any]:
        """Load the character's core configuration (config.json)."""
        pass

    @abstractmethod
    def save_config(self, data: Dict[str, Any]):
        """Save the character's core configuration."""
        pass

    @abstractmethod
    def load_module_data(self, module_id: str) -> Dict[str, Any]:
        """Load data for a specific module (e.g., 'memory', 'emotion')."""
        pass

    @abstractmethod
    def save_module_data(self, module_id: str, data: Dict[str, Any]):
        """Save data for a specific module."""
        pass
    
    @abstractmethod
    def get_data_dir(self, module_id: str = None) -> Any:
        """
        Get the raw path/identifier for a data directory.
        Used for binary assets or plugins that manage their own files.
        Returns Path object for FileRepo, or a connection string/key for DBRepo.
        """
        pass

class ISessionRepository(IRepository[Dict]):
    """Repository for chat session state, keyed by user and character."""

    @abstractmethod
    async def get_session(self, user_id: str, char_id: str) -> Optional[Dict]:
        """Retrieve a session by user and character."""
        pass

    @abstractmethod
    async def save_session(self, user_id: str, char_id: str, data: Dict) -> bool:
        """Persist a session by user and character."""
        pass

    @abstractmethod
    async def delete_session(self, user_id: str, char_id: str) -> bool:
        """Delete a session by user and character."""
        pass
    
    @abstractmethod
    async def get_recent(self, limit: int = 10) -> List[Dict]:
        """Get recent sessions."""
        pass
