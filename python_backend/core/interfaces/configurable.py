from abc import ABC, abstractmethod
from typing import Dict, Any

class IConfigurable(ABC):
    """
    Interface for services that support reactive configuration updates.
    """
    
    @abstractmethod
    def on_config_update(self, config_data: Dict[str, Any]) -> None:
        """
        Called when the configuration watcher detects changes.
        
        Args:
            config_data: The full updated configuration dictionary (or specific section)
        """
        pass
