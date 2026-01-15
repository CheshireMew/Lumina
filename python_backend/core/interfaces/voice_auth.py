from abc import ABC, abstractmethod
from typing import Any

class IVoiceAuth(ABC):
    @abstractmethod
    async def ensure_driver_loaded(self):
        pass

    @property
    @abstractmethod
    def profiles(self) -> dict:
        pass
        
    @property
    @abstractmethod
    def user_embedding(self) -> Any:
        pass
