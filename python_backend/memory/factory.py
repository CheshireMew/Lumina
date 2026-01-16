
import os
import logging
from typing import Optional
from app_config import config
from core.interfaces.driver import BaseMemoryDriver
from services.plugin_loader import PluginLoader

logger = logging.getLogger("memory.factory")

class NoOpDriver:
    """Fallback driver when plugins are missing."""
    async def connect(self): 
        logger.warning("NoOpDriver: connect called (No DB connected)")
    async def close(self): pass
    async def initialize_schema(self): pass
    async def create(self, *args, **kwargs): return None
    async def query(self, *args, **kwargs): return []
    async def update(self, *args, **kwargs): return None
    async def delete(self, *args, **kwargs): return None
    @property
    def _db(self): return None

class MemoryDriverFactory:
    """
    Factory to create and verify Memory Drivers.
    Encapsulates dynamic loading logic to separate it from Business Logic.
    """
    
    @staticmethod
    def create_driver(config_provider: Optional[str] = None) -> BaseMemoryDriver:
        """
        Create a memory driver instance based on configuration or priority.
        
        Args:
            config_provider: Overridable provider ID. If None, uses app_config.
            
        Returns:
            Authorized BaseMemoryDriver instance.
            
        Raises:
            ImportError: If no drivers are found.
        """
        try:
            # 1. Determine Target Provider
            target_provider = config_provider or config.memory.provider
            
            # 2. Locate Drivers Directory
            # Assuming this file is in python_backend/memory/factory.py
            # Drivers are in python_backend/plugins/drivers/memory
            # 2. Locate Drivers Directories (Support Extensions)
            current_dir = os.path.dirname(os.path.abspath(__file__))
            base_plugins_dir = os.path.abspath(os.path.join(current_dir, "..", "plugins"))
            
            drivers_dirs = []
            
            # Legacy Path
            legacy_dir = os.path.join(base_plugins_dir, "drivers", "memory")
            if os.path.exists(legacy_dir):
                drivers_dirs.append(legacy_dir)
                
            # Extensions Path
            extensions_dir = os.path.join(base_plugins_dir, "extensions")
            if os.path.exists(extensions_dir):
                for ext_name in os.listdir(extensions_dir):
                    mem_driver_path = os.path.join(extensions_dir, ext_name, "drivers", "memory")
                    if os.path.isdir(mem_driver_path):
                        drivers_dirs.append(mem_driver_path)

            if not drivers_dirs:
                # logger.error(f"No memory driver directories found.")
                # Don't raise yet, list will be empty
                pass

            # 3. Load All Drivers
            loaded_drivers = []
            for d_dir in drivers_dirs:
                loaded_drivers.extend(PluginLoader.load_plugins(d_dir, BaseMemoryDriver))
            
            if not loaded_drivers:
                logger.error("No valid memory drivers found in plugins directory.")
                raise ImportError("No memory drivers available.")

            # 4. Select Driver
            selected_driver = None
            
            # 4a. Exact Match
            for d in loaded_drivers:
                if d.id == target_provider:
                    selected_driver = d
                    break
            
            # 4b. Alias Handling ("surreal" -> "surreal-db")
            if not selected_driver and target_provider == "surreal":
                for d in loaded_drivers:
                    if d.id == "surreal-db":
                        selected_driver = d
                        break
            
            # 5. Fallback Strategy
            if selected_driver:
                logger.info(f"[MemoryFactory] Selected Driver: {selected_driver.name} ({selected_driver.id})")
                return selected_driver
            else:
                logger.warning(f"[MemoryFactory] Configured provider '{target_provider}' not found or valid.")
                # Fallback to FIRST available
                fallback = loaded_drivers[0]
                logger.warning(f"[MemoryFactory] Falling back to default driver: {fallback.name}")
                return fallback

        except Exception as e:
            logger.critical(f"[MemoryFactory] Driver Creation Failed: {e}")
            raise e
