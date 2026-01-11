from abc import ABC, abstractmethod
from typing import Any, Dict, Optional
from PIL import Image

class VisionProvider(ABC):
    """
    Abstract Base Class for Vision Providers (MCP-style).
    All vision models (Moondream, LLaVA, etc.) must implement this interface.
    """
    
    @property
    @abstractmethod
    def provider_id(self) -> str:
        """Unique identifier for the provider (e.g., 'moondream')"""
        pass

    @abstractmethod
    def load(self):
        """Load the model into memory."""
        pass

    @abstractmethod
    def unload(self):
        """Unload the model to free memory."""
        pass

    @abstractmethod
    async def analyze(self, image: Image.Image, prompt: str = "Describe this image.") -> str:
        """
        Analyze the image and return a text description.
        
        Args:
            image: PIL Image object
            prompt: Text prompt to guide the analysis
            
        Returns:
            The textual description or answer.
        """
        pass
