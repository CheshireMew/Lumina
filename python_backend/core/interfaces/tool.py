
from abc import ABC, abstractmethod
from typing import Dict, Any

class ToolProvider(ABC):
    """
    Interface for plugins that provide tools to the LLM.
    """
    
    @property
    @abstractmethod
    def name(self) -> str:
        """Unique identifier for the tool (e.g., 'web_search')."""
        pass
    
    @abstractmethod
    def get_definition(self) -> Dict[str, Any]:
        """
        Return the OpenAI-compatible tool definition.
        
        Example:
        {
            "type": "function",
            "function": {
                "name": "web_search",
                "description": "...",
                "parameters": { ... }
            }
        }
        """
        pass
        
    @abstractmethod
    async def execute(self, args: Dict[str, Any]) -> str:
        """
        Execute the tool with the given arguments.
        Returns a string representation of the result.
        """
        pass
