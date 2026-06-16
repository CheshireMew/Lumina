from abc import ABC, abstractmethod
from typing import Any, Callable, Awaitable, Dict, List

class AbstractLifecycleBus(ABC):
    """
    Abstract Interface for the Distributed Lifecycle Bus.
    Decouples the business logic (Main/Worker) from the underlying transport layer.
    """

    @property
    @abstractmethod
    def is_connected(self) -> bool:
        """Whether the transport is currently connected."""
        pass

    @abstractmethod
    async def connect(self):
        """Establish connection to the transport layer."""
        pass

    @abstractmethod
    async def disconnect(self):
        """Close connection."""
        pass

    @abstractmethod
    async def publish_state(self, plugin_id: str, state: Dict[str, Any]):
        """
        Publish a state change for a specific plugin.
        
        Args:
            plugin_id: The unique ID of the plugin (e.g., "system.voiceprint")
            state: The new state dictionary (e.g., {"enabled": True, "config": {...}})
        """
        pass

    @abstractmethod
    async def subscribe_state(self, callback: Callable[[str, Dict[str, Any]], Awaitable[None]]):
        """
        Subscribe to ALL state changes.
        
        Args:
            callback: Async function(plugin_id, new_state) to be called on update.
        """
        pass

    @abstractmethod
    async def get_all_states(self) -> Dict[str, Dict[str, Any]]:
        """
        Retrieve the current full state of all plugins (Sync/Snapshot).
        Used during startup to hydrate local state.
        """
        pass

    @abstractmethod
    async def send_heartbeat(self, worker_id: str):
        """
        Pulse to indicate worker is alive.
        """
        pass

    @abstractmethod
    async def get_active_workers(self, timeout_seconds: int = 15) -> List[Dict[str, Any]]:
        """
        Retrieve list of workers that have pulsed within timeout.
        """
        pass

    @abstractmethod
    async def get_pool(self) -> Any:
        """Return the lifecycle store connection pool."""
        pass
