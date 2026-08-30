from .service_container import ServiceContainer, ServiceNotInitializedError


def create_service_container() -> ServiceContainer:
    """Create one explicit service graph for an application runtime."""
    return ServiceContainer()


__all__ = [
    "ServiceContainer",
    "ServiceNotInitializedError",
    "create_service_container",
]
