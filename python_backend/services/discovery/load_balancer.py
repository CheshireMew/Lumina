"""
Load Balancer.
Provides strategies for selecting service instances.
"""

import random
import logging
from typing import List, Optional, Iterator
from enum import Enum
from dataclasses import dataclass

from .registry import ServiceInstance, ServiceStatus

logger = logging.getLogger("LoadBalancer")


class LoadBalanceStrategy(Enum):
    """Available load balancing strategies."""
    ROUND_ROBIN = "round_robin"
    LEAST_LOAD = "least_load"
    RANDOM = "random"
    FIRST_AVAILABLE = "first_available"


@dataclass
class _RoundRobinState:
    """State for round-robin balancing."""
    index: int = 0


class LoadBalancer:
    """
    Selects service instances based on configurable strategy.
    """
    
    def __init__(self, strategy: LoadBalanceStrategy = LoadBalanceStrategy.LEAST_LOAD):
        self.strategy = strategy
        self._rr_states: dict[str, _RoundRobinState] = {}  # key -> state
    
    def select(
        self,
        instances: List[ServiceInstance],
        key: str = "default"
    ) -> Optional[ServiceInstance]:
        """
        Select a single instance from the list.
        
        Args:
            instances: List of available instances
            key: Key for round-robin state tracking
            
        Returns:
            Selected instance or None if no healthy instances
        """
        # Filter to healthy instances only
        healthy = [
            i for i in instances 
            if i.status in (ServiceStatus.HEALTHY, ServiceStatus.DEGRADED)
        ]
        
        if not healthy:
            logger.warning(f"No healthy instances available for selection")
            return None
        
        if len(healthy) == 1:
            return healthy[0]
        
        if self.strategy == LoadBalanceStrategy.ROUND_ROBIN:
            return self._select_round_robin(healthy, key)
        elif self.strategy == LoadBalanceStrategy.LEAST_LOAD:
            return self._select_least_load(healthy)
        elif self.strategy == LoadBalanceStrategy.RANDOM:
            return self._select_random(healthy)
        elif self.strategy == LoadBalanceStrategy.FIRST_AVAILABLE:
            return healthy[0]
        else:
            return healthy[0]
    
    def _select_round_robin(
        self, 
        instances: List[ServiceInstance],
        key: str
    ) -> ServiceInstance:
        """Round-robin selection."""
        if key not in self._rr_states:
            self._rr_states[key] = _RoundRobinState()
        
        state = self._rr_states[key]
        idx = state.index % len(instances)
        state.index += 1
        
        return instances[idx]
    
    def _select_least_load(
        self,
        instances: List[ServiceInstance]
    ) -> ServiceInstance:
        """Select instance with lowest load."""
        # Prefer HEALTHY over DEGRADED
        healthy_only = [i for i in instances if i.status == ServiceStatus.HEALTHY]
        candidates = healthy_only if healthy_only else instances
        
        return min(candidates, key=lambda i: i.load)
    
    def _select_random(
        self,
        instances: List[ServiceInstance]
    ) -> ServiceInstance:
        """Random selection."""
        return random.choice(instances)
    
    def select_for_capability(
        self,
        capability: str,
        key: str = None
    ) -> Optional[ServiceInstance]:
        """
        Select an instance that supports the given capability.
        Uses the service registry to find candidates.
        
        Args:
            capability: Required capability (e.g., "stt.whisper")
            key: Optional key for round-robin state
            
        Returns:
            Selected instance or None
        """
        from .registry import get_service_registry
        
        registry = get_service_registry()
        instances = registry.get_instances_by_capability(capability)
        
        return self.select(instances, key=key or capability)
    
    def get_all_for_capability(self, capability: str) -> List[ServiceInstance]:
        """Get all healthy instances for a capability."""
        from .registry import get_service_registry
        
        registry = get_service_registry()
        return registry.get_instances_by_capability(capability)


# Convenience function
def select_worker(
    capability: str,
    strategy: LoadBalanceStrategy = LoadBalanceStrategy.LEAST_LOAD
) -> Optional[ServiceInstance]:
    """
    Select a worker instance for the given capability.
    
    Args:
        capability: Required capability (e.g., "stt", "tts.edge")
        strategy: Load balancing strategy
        
    Returns:
        Selected ServiceInstance or None
    """
    balancer = LoadBalancer(strategy=strategy)
    return balancer.select_for_capability(capability)
