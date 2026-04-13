from abc import ABC, abstractmethod
from typing import Any, List, Optional, Dict

class IMemoryService(ABC):
    """Abstract Interface for Memory Service"""
    @abstractmethod
    async def add_message(self, *args, **kwargs): pass
    
    @abstractmethod
    async def get_history(self, *args, **kwargs): pass
    
    @abstractmethod
    async def search_vectors(self, *args, **kwargs): pass

class ILLMManager(ABC):
    """Abstract Interface for LLM Manager"""
    @abstractmethod
    async def chat_completion(self, *args, **kwargs): pass
    
    @abstractmethod
    def get_client(self, *args, **kwargs): pass

class ISTTManager(ABC):
    """Abstract Interface for STT Manager / Drivers"""
    @abstractmethod
    async def transcribe(self, audio_data: Any, **kwargs) -> str: pass

class ITTSManager(ABC):
    """Abstract Interface for TTS Manager"""
    @abstractmethod
    async def synthesize(self, text: str, **kwargs) -> Any: pass
