
import os
import logging
from typing import Any

from core.interfaces.driver import BaseMemoryDriver
from services.managers.driver_loader import DriverLoader

logger = logging.getLogger("memory.factory")


class MemoryDriverFactory:
    """
    Factory to create and verify Memory Drivers.
    Encapsulates dynamic loading logic to separate it from Business Logic.
    """
    
    @staticmethod
    def create_driver(provider_id: str, driver_config: dict[str, Any] | None = None) -> BaseMemoryDriver:
        """
        Create the explicitly selected memory driver instance.
        
        Args:
            provider_id: Selected provider ID.
            driver_config: Runtime configuration passed to the driver.
            
        Returns:
            Authorized BaseMemoryDriver instance.
            
            Raises:
            ImportError: If no drivers are found.
        """
        try:
            if not provider_id:
                raise ValueError("Memory provider id is required.")
            target_provider = provider_id
            
            current_dir = os.path.dirname(os.path.abspath(__file__))
            modules_dir = os.path.abspath(os.path.join(current_dir, "..", "capability_modules"))

            drivers_dirs = []

            if os.path.exists(modules_dir):
                for module_name in os.listdir(modules_dir):
                    mem_driver_path = os.path.join(modules_dir, module_name, "drivers", "memory")
                    if os.path.isdir(mem_driver_path):
                        drivers_dirs.append(mem_driver_path)

            loaded_drivers = []
            for d_dir in drivers_dirs:
                loaded_drivers.extend(DriverLoader.load_plugins(d_dir, BaseMemoryDriver))
            
            if not loaded_drivers:
                logger.error("No valid memory drivers found in capability modules.")
                raise ImportError("No memory drivers available.")

            for d in loaded_drivers:
                if d.id == target_provider:
                    if driver_config is not None:
                        d.load_config(driver_config)
                    logger.info(f"[MemoryFactory] Selected Driver: {d.name} ({d.id})")
                    return d

            available = ", ".join(sorted(d.id for d in loaded_drivers))
            raise ImportError(
                f"Configured memory provider '{target_provider}' is not available. "
                f"Available providers: {available}"
            )

        except Exception as e:
            logger.critical(f"[MemoryFactory] Driver Creation Failed: {e}")
            raise e
