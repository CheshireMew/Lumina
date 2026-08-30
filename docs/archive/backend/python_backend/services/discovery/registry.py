"""
Service Registry.
Manages discovered services and their capabilities.
Integrates with WorkerControlHub for real-time updates.
"""

import logging
from typing import Dict, List, Optional, Set, Any
from dataclasses import dataclass, field
from enum import Enum

logger = logging.getLogger("ServiceRegistry")


class ServiceStatus(Enum):
    HEALTHY = "healthy"
    DEGRADED = "degraded"
    UNHEALTHY = "unhealthy"


@dataclass
class ServiceInstance:
    """Represents a discovered service instance."""
    worker_id: str
    worker_type: str
    host: str
    port: int
    capabilities: Set[str] = field(default_factory=set)
    metadata: Dict[str, Any] = field(default_factory=dict)
    load: float = 0.0
    status: ServiceStatus = ServiceStatus.HEALTHY
    
    @property
    def address(self) -> str:
        return f"{self.host}:{self.port}"
    
    def supports_capability(self, capability: str) -> bool:
        """Check if this instance supports a given capability."""
        # Exact match
        if capability in self.capabilities:
            return True
        # Prefix match (e.g., "stt" matches "stt.whisper")
        for cap in self.capabilities:
            if cap.startswith(f"{capability}.") or capability.startswith(f"{cap}."):
                return True
        return False


class ServiceRegistry:
    """
    Central registry for service discovery.
    Singleton pattern - integrates with WorkerControlHub.
    """
    _instance: Optional["ServiceRegistry"] = None
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._initialized = False
        return cls._instance
    
    def __init__(self):
        if self._initialized:
            return
        self._initialized = True
        
        self._services: Dict[str, ServiceInstance] = {}
        self._hub_linked = False
        logger.info("📋 ServiceRegistry initialized")
    
    # --- Registration ---
    
    def register(
        self,
        worker_id: str,
        worker_type: str,
        host: str = "127.0.0.1",
        port: int = 8000,
        capabilities: List[str] = None,
        metadata: Dict[str, Any] = None
    ) -> ServiceInstance:
        """Register a new service instance."""
        instance = ServiceInstance(
            worker_id=worker_id,
            worker_type=worker_type,
            host=host,
            port=port,
            capabilities=set(capabilities or []),
            metadata=metadata or {}
        )
        
        self._services[worker_id] = instance
        logger.info(f"📝 Registered service: {worker_id} ({worker_type}) at {instance.address}")
        
        return instance
    
    def deregister(self, worker_id: str):
        """Remove a service instance from registry."""
        if worker_id in self._services:
            del self._services[worker_id]
            logger.info(f"🗑️ Deregistered service: {worker_id}")
    
    def update_status(
        self,
        worker_id: str,
        load: float = None,
        status: ServiceStatus = None,
        capabilities: List[str] = None
    ):
        """Update status of a registered service."""
        instance = self._services.get(worker_id)
        if not instance:
            return
        
        if load is not None:
            instance.load = load
        if status is not None:
            instance.status = status
        if capabilities is not None:
            instance.capabilities = set(capabilities)
    
    # --- Query ---
    
    def get_instance(self, worker_id: str) -> Optional[ServiceInstance]:
        """Get a specific service instance by ID."""
        return self._services.get(worker_id)
    
    def get_all_instances(self) -> List[ServiceInstance]:
        """Get all registered service instances."""
        return list(self._services.values())
    
    def get_instances_by_type(self, worker_type: str) -> List[ServiceInstance]:
        """Get all instances of a specific worker type."""
        return [
            s for s in self._services.values()
            if s.worker_type == worker_type
        ]
    
    def get_instances_by_capability(self, capability: str) -> List[ServiceInstance]:
        """Get all instances that support a given capability."""
        return [
            s for s in self._services.values()
            if s.supports_capability(capability) and s.status != ServiceStatus.UNHEALTHY
        ]
    
    def get_healthy_instances(self, worker_type: str = None) -> List[ServiceInstance]:
        """Get all healthy instances, optionally filtered by type."""
        instances = self._services.values()
        if worker_type:
            instances = [s for s in instances if s.worker_type == worker_type]
        return [s for s in instances if s.status in (ServiceStatus.HEALTHY, ServiceStatus.DEGRADED)]
    
    # --- WorkerControlHub Integration ---
    
    def link_to_hub(self):
        """
        Link to WorkerControlHub for automatic updates.
        Call this after WorkerControlHub is initialized.
        """
        if self._hub_linked:
            return
        
        try:
            from services.infra.worker_control_hub import get_worker_control_hub
            from core.protocols.worker_control import WsMessageType
            
            hub = get_worker_control_hub()
            
            # Register for worker status updates
            def on_status(worker_id: str, msg, binary_body: bytes = None):
                payload = msg.payload
                self.update_status(
                    worker_id=worker_id,
                    load=payload.get("load", 0.0),
                    status=ServiceStatus.HEALTHY if payload.get("status") == "healthy" else ServiceStatus.DEGRADED
                )
            
            hub.on_message(WsMessageType.STATUS, on_status)
            hub.on_message(WsMessageType.HEARTBEAT, on_status)
            
            self._hub_linked = True
            logger.info("🔗 ServiceRegistry linked to WorkerControlHub")
            
        except Exception as e:
            logger.warning(f"Failed to link ServiceRegistry to Hub: {e}")
    
    def sync_from_hub(self):
        """Sync current worker list from WorkerControlHub."""
        try:
            from services.infra.worker_control_hub import get_worker_control_hub
            
            hub = get_worker_control_hub()
            for worker_id, conn in hub.get_all_workers().items():
                if worker_id not in self._services:
                    self.register(
                        worker_id=worker_id,
                        worker_type=conn.worker_type,
                        port=conn.port,
                        capabilities=[conn.worker_type]  # Basic capability
                    )
                self.update_status(
                    worker_id=worker_id,
                    load=conn.load,
                    status=ServiceStatus.HEALTHY if conn.status == "healthy" else ServiceStatus.DEGRADED
                )
            
            # Remove stale entries
            hub_workers = set(hub.get_all_workers().keys())
            for worker_id in list(self._services.keys()):
                if worker_id not in hub_workers:
                    self.deregister(worker_id)
                    
        except Exception as e:
            logger.debug(f"Failed to sync from hub: {e}")


# Singleton accessor
def get_service_registry() -> ServiceRegistry:
    return ServiceRegistry()
