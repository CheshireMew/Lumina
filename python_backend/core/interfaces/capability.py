from abc import ABC, abstractmethod
from typing import Callable, List, Dict, Any
from fastapi import FastAPI
from pydantic import BaseModel, Field

class CapabilityContract(BaseModel):
    """
    Defines a capability provided or consumed by a plugin.
    Used in PluginManifest.
    """
    type: str
    version: str = "1.0.0"
    attributes: Dict[str, Any] = Field(default_factory=dict)
    
    class Config:
        extra = "allow"

class IWorkerCapability(ABC):
    """
    Interface for Worker Capabilities (Plugins for the Generic Worker Kernel).
    Examples: STT, TTS, OCR, RAG.
    """

    @property
    @abstractmethod
    def name(self) -> str:
        """Service name, e.g. 'stt', 'tts'. Used for logging and identification."""
        pass

    @property
    def config_key(self) -> str:
        """Configuration key in default.yaml, e.g. 'stt' matches config.stt"""
        return self.name

    @abstractmethod
    def register_routes(self, app: FastAPI):
        """
        Mount routers to the FastAPI app.
        Caller (Kernel) will handle the prefix if necessary, but usually 
        Capabilities mount their own top-level routers.
        """
        pass

    @abstractmethod
    async def on_startup(self, app: FastAPI):
        """
        Initialize Resources (Managers, Models, Database connections).
        Called during FastAPI startup event.
        """
        pass

    @abstractmethod
    async def on_shutdown(self):
        """
        Cleanup Resources.
        Called during FastAPI shutdown event.
        """
        pass

    @abstractmethod
    def get_state_provider(self) -> Callable[[], List[Dict[str, Any]]]:
        """
        Return the function used by WorkerReporter to gather state.
        This function should return a list of plugin states.
        """
        pass
