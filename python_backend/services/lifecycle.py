"""
Application Lifecycle Management.
Orchestrates startup and shutdown using modular Bootstrapper pattern.

Refactored from 180 lines to ~50 lines by extracting logic to:
- core/bootstrap/integration.py
- core/bootstrap/post_startup.py
- services/utilities/shutdown.py
"""
import logging
from contextlib import asynccontextmanager
from fastapi import FastAPI
from services.container import services as service_instance

logger = logging.getLogger("Lifecycle")


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifecycle context manager."""
    
    from core.bootstrap.manager import BootstrapManager
    
    # Infrastructure Bootstrappers
    from core.bootstrap.infrastructure import (
        WorkerRuntimeRegistryBootstrapper,
        ConfigBootstrapper, 
        DatabaseBootstrapper, 
        EventBusBootstrapper, 
        ProtocolBootstrapper
    )
    
    # Service Bootstrappers
    from core.bootstrap.services import (
        CoreServicesBootstrapper, 
        MiddlewareBootstrapper, 
        ProviderConfigBootstrapper,
    )
    
    # Integration Bootstrappers
    from core.bootstrap.integration import (
        ChatTurnEventAdapterBootstrapper,
    )
    
    # Post-Startup Bootstrappers
    from core.bootstrap.post_startup import (
        PrewarmBootstrapper,
        ConfigWatcherBootstrapper,
        WorkerControlHubBootstrapper,
        ProcessSupervisorBootstrapper,
        AutomationBootstrapper
    )
    
    # Build Bootstrap Pipeline
    manager = BootstrapManager()
    
    # Level 0: Configuration
    manager.add(ConfigBootstrapper())
    manager.add(WorkerRuntimeRegistryBootstrapper())
    
    # Level 1: Infrastructure
    manager.add(DatabaseBootstrapper())
    manager.add(EventBusBootstrapper())
    manager.add(ProtocolBootstrapper())
    
    # Level 2: Core Services
    manager.add(CoreServicesBootstrapper())
    
    # Level 3: Provider and built-in middleware services
    manager.add(ProviderConfigBootstrapper())
    manager.add(MiddlewareBootstrapper())
    
    # Level 4: Integration
    manager.add(ChatTurnEventAdapterBootstrapper())
    
    # Level 5: Post-Startup
    manager.add(WorkerControlHubBootstrapper())
    manager.add(PrewarmBootstrapper())
    manager.add(ConfigWatcherBootstrapper(app))
    manager.add(ProcessSupervisorBootstrapper())
    manager.add(AutomationBootstrapper())
    
    # Execute Startup
    try:
        await manager.start(service_instance)
        logger.info("🚀 Startup complete")
    except Exception as e:
        logger.critical(f"Startup Failed: {e}", exc_info=True)
        raise RuntimeError("Application startup failed") from e
    
    yield
    
    # Execute Shutdown
    from services.utilities.shutdown import ShutdownManager
    shutdown_mgr = ShutdownManager()
    await shutdown_mgr.shutdown(service_instance, app)
