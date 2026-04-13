from typing import Optional
from core.interfaces.lifecycle_bus import AbstractLifecycleBus
from services.infra.postgres_lifecycle_bus import PostgresLifecycleBus

_bus_instance: Optional[AbstractLifecycleBus] = None

def get_lifecycle_bus() -> AbstractLifecycleBus:
    """
    Singleton Factory for Lifecycle Bus.
    Lumina now persists lifecycle state in PostgreSQL only.
    """
    global _bus_instance
    if _bus_instance is None:
        _bus_instance = PostgresLifecycleBus()
    return _bus_instance
