from abc import ABC, abstractmethod
from typing import Any, Dict, List, Optional

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
    async def send_heartbeat(self, worker_id: str, data: Optional[Dict] = None):
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
