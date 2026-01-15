
from abc import ABC, abstractmethod
import logging
from typing import Any

logger = logging.getLogger("Bootstrap")

class Bootstrapper(ABC):
    """
    Interface for a startup phase.
    """
    
    @property
    @abstractmethod
    def name(self) -> str:
        pass

    @abstractmethod
    async def bootstrap(self, container: Any):
        """
        Execute the bootstrap logic.
        :param container: ServiceContainer instance
        """
        pass
