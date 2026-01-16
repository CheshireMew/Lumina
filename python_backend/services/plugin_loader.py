import os
import sys
import importlib.util
import inspect
import logging
from typing import List, Type, Any

logger = logging.getLogger("PluginLoader")

class PluginLoader:
    """
    Generic utility to load Python classes from a directory.
    Useful for loading SttDrivers, TtsDrivers, Tickers, etc.
    """

    @staticmethod
    def load_plugins(directory: str, base_class: Type) -> List[Any]:
        """
        Scans a directory for .py files, imports them, and finds classes
        that inherit from `base_class` (but are not `base_class` itself).
        
        Returns:
            List of instantiated plugin objects.
        """
        plugins = []
        
        if not os.path.exists(directory):
            logger.warning(f"Plugin directory not found: {directory}")
            return []

        logger.info(f"Scanning for plugins in: {directory}")

        for filename in os.listdir(directory):
            if filename.endswith(".py") and not filename.startswith("__"):
                module_name = filename[:-3]
                file_path = os.path.join(directory, filename)
                
                try:
                    # Dynamic Import
                    spec = importlib.util.spec_from_file_location(module_name, file_path)
                    if spec and spec.loader:
                        module = importlib.util.module_from_spec(spec)
                        sys.modules[module_name] = module # caching
                        spec.loader.exec_module(module)
                        
                        # Inspect for subclasses
                        for name, obj in inspect.getmembers(module, inspect.isclass):
                            if issubclass(obj, base_class) and obj is not base_class:
                                try:
                                    # Create Instance
                                    # Note: We assume plugins can be init with no args
                                    # or we might need a config factory later.
                                    # For now, Drivers usually handle their own config reading or defaults.
                                    instance = obj()
                                    plugins.append(instance)
                                    logger.info(f"Loaded plugin: {name} from {filename}")
                                except Exception as init_err:
                                    logger.error(f"Failed to instantiate {name}: {init_err}", exc_info=True)

                except Exception as e:
                    logger.error(f"Failed to load module {filename}: {e}", exc_info=True)
                    
        return plugins
