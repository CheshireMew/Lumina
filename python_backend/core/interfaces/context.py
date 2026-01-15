
from abc import ABC, abstractmethod
from typing import Any, Dict, Optional, TYPE_CHECKING

if TYPE_CHECKING:
    from services.chat.pipeline import PipelineContext

class ContextProvider(ABC):
    """
    Interface for plugins that inject context into the system prompt.
    """
    
    @abstractmethod
    async def provide(self, ctx: Any) -> Optional[str]:
        """
        Return a string to be appended to the system prompt.
        Return None or empty string if no context should be added.
        
        Args:
            ctx: PipelineContext object containing current request state.
        """
        pass
