from typing import Optional
from core.interfaces.lifecycle_bus import AbstractLifecycleBus

_bus_instance: Optional[AbstractLifecycleBus] = None

def get_lifecycle_bus() -> AbstractLifecycleBus:
    """
    Singleton Factory for Lifecycle Bus.
    Lifecycle state is stored in Lumina's managed local database.
    """
    global _bus_instance
    if _bus_instance is None:
        from services.infra.sqlite_lifecycle_bus import SQLiteLifecycleBus

        _bus_instance = SQLiteLifecycleBus()
    return _bus_instance
