from typing import Optional
from app_config import config
from core.interfaces.lifecycle_bus import AbstractLifecycleBus
from services.infra.surreal_lifecycle_bus import SurrealLifecycleBus
from services.infra.postgres_lifecycle_bus import PostgresLifecycleBus

_bus_instance: Optional[AbstractLifecycleBus] = None

def get_lifecycle_bus() -> AbstractLifecycleBus:
    """
    Singleton Factory for Lifecycle Bus.
    Decides between SurrealDB and PostgreSQL based on memory configuration.
    """
    global _bus_instance
    if _bus_instance is None:
        provider = config.memory.provider
        if provider == "postgres":
            _bus_instance = PostgresLifecycleBus()
        else:
            # Default to SurrealDB
            _bus_instance = SurrealLifecycleBus()
    return _bus_instance
