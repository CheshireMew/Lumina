
import logging
from typing import Any

from core.interfaces.driver import BaseMemoryDriver
from provider_drivers.memory_postgres.drivers.memory.postgres_driver import PostgresDriver

logger = logging.getLogger("memory.factory")


class MemoryDriverFactory:
    """
    Factory to create and verify Memory Drivers.
    """

    _drivers = {
        "driver.memory.postgres": PostgresDriver,
    }
    
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
            factory = MemoryDriverFactory._drivers.get(provider_id)
            if factory is None:
                available = ", ".join(sorted(MemoryDriverFactory._drivers))
                raise ImportError(
                    f"Configured memory provider '{provider_id}' is not available. "
                    f"Available providers: {available}"
                )

            driver = factory()
            if not isinstance(driver, BaseMemoryDriver):
                raise TypeError(f"Memory driver '{provider_id}' is not a BaseMemoryDriver")
            if driver_config is not None:
                driver.load_config(driver_config)
            logger.info(f"[MemoryFactory] Selected Driver: {driver.name} ({driver.id})")
            return driver

        except Exception as e:
            logger.critical(f"[MemoryFactory] Driver Creation Failed: {e}")
            raise e
