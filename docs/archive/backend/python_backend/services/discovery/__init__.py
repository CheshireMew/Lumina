"""
Service Discovery Package.
Provides lightweight service registry and load balancing for workers.
"""

from .registry import ServiceRegistry, get_service_registry
from .load_balancer import LoadBalancer, LoadBalanceStrategy

__all__ = [
    'ServiceRegistry',
    'get_service_registry',
    'LoadBalancer',
    'LoadBalanceStrategy',
]
