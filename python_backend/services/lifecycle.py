import os
import sys
import logging
from contextlib import asynccontextmanager
from fastapi import FastAPI
from services.container import services as service_instance

@asynccontextmanager
async def lifespan(app: FastAPI):
    """应用生命周期管理 (Refactored to use Bootstrappers)"""
    logger = logging.getLogger("Lifecycle")
    
    from core.bootstrap.manager import BootstrapManager
    from core.bootstrap.infrastructure import ConfigBootstrapper, DatabaseBootstrapper, EventBusBootstrapper, ProtocolBootstrapper
    from core.bootstrap.services import CoreServicesBootstrapper, PluginServicesBootstrapper, MiddlewareBootstrapper, SystemPluginsBootstrapper
    
    # 1. Initialize Bootstrap Manager
    manager = BootstrapManager()
    
    # Inline Bootstrapper for RouterManager (needs access to 'app')
    from core.bootstrap.interface import Bootstrapper
    class RouterBootstrapper(Bootstrapper):
        def __init__(self, _app: FastAPI):
            self._app = _app
        @property
        def name(self) -> str: return "RouterManager"
        async def bootstrap(self, container):
            from services.router_manager import RouterManager
            # EventBus should be ready by now (Level 1)
            # Inject explicit bus from container
            rm = RouterManager(self._app, bus=container.event_bus) 
            container.router_manager = rm
            logger.info("✅ RouterManager Bootstrapped & Subscribed")

    # 2. Define Startup Phase Order
    manager.add(ConfigBootstrapper())       # Level 0: Config
    manager.add(DatabaseBootstrapper())     # Level 1: Persistence
    manager.add(EventBusBootstrapper())     # Level 1: Messaging
    manager.add(ProtocolBootstrapper())     # Level 1.2: Hardening
    manager.add(RouterBootstrapper(app))    # Level 1.5: Dynamic Routing (Must be before Plugins)
    manager.add(CoreServicesBootstrapper()) # Level 2: Core Logic (LLM/Soul)
    manager.add(PluginServicesBootstrapper()) # Level 3: I/O (Vision/TTS/STT)
    manager.add(MiddlewareBootstrapper())   # Level 3: Chat Pipeline Components
    manager.add(SystemPluginsBootstrapper())# Level 4: External Plugins
    
    # 3. Execute
    try:
        await manager.start(service_instance)
    except Exception as e:
        logger.critical(f"Startup Failed: {e}", exc_info=True)
        sys.exit(1)

    # 4. Post-Bootstrap wiring (Router Mounting)
    # Ideally this moves to a RouteBootstrapper, but requires app instance access
    # Keeping it here for now to avoid passing 'app' deep into bootstrappers
    if service_instance.event_bus:
        def on_router_registered(event):
            router = event.data.get("router")
            prefix = event.data.get("prefix", "")
            if router:
                app.include_router(router, prefix=prefix)
                logger.info(f"🔗 Mounted Router via EventBus: {prefix}")
                
        service_instance.event_bus.subscribe("core.register_router", on_router_registered)
        
        # Start ChatBridge (Legacy/MVP helper)
        try:
             from services.chat_bridge import BasicChatBridge
             service_instance.chat_bridge = BasicChatBridge()
             service_instance.chat_bridge.start()
        except: pass

    # Mount System Plugin Routers
    if service_instance.system_plugin_manager:
        for pid, plugin in service_instance.system_plugin_manager.plugins.items():
            if getattr(plugin, 'router', None) and not getattr(plugin, '_router_registered', False):
                 app.include_router(plugin.router)

    # MCP Host
    try:
        from services.mcp_host import MCPHost
        if service_instance.soul:
            # [Architecture 5.0] Inject ProcessManager for Governance
            pm = service_instance.get_process_manager() 
            service_instance.mcp_host = MCPHost(service_instance.soul, process_manager=pm)
            logger.info("🔌 MCP Host Initialized (Start Disabled)")
    except Exception as e:
        logger.warning(f"Failed to init MCP Host: {e}")

    # [Architecture 7.0] Network Discovery via API
    # Frontend should use GET /network endpoint instead of file-based discovery.
    # Removed: connection.json file writing (was single-machine only, not multi-client friendly)

    # [Pre-warm] Start TTS worker if configured
    try:
        from app_config import config
        if config.plugins.prewarm_core and service_instance.get_process_manager():
            logger.info("🔥 Pre-warming Core Services (STT/TTS)...")
            from services.plugin_service import PluginService
            # We don't have direct access to PluginService instance here via container...
            # Wait, SystemPluginManager is Level 4.
            # But PluginService is NOT explicitly in container! 
            # It's usually instantiated inside Routers or Managers.
            # However, ProcessManager is in container. We can just use it directly.
            pm = service_instance.get_process_manager()
            # pm.start_worker("stt_server") # [Refactor] STT Integrated into Main
            pm.start_worker("tts_server")
    except Exception as e:
        logger.warning(f"Pre-warm failed: {e}")

    # [Architecture 6.0] Start Reconciliation Service (Main Process Only)
    try:
        from services.reconciliation_service import ReconciliationService
        reconciler = ReconciliationService(service_instance)
        service_instance.register_reconciliation_service(reconciler)
        reconciler.start()
        logger.info("⚖️ Reconciliation Service linked to Lifecycle.")
    except Exception as e:
        logger.error(f"Failed to start ReconciliationService: {e}")

    yield

    
    # [SHUTDOWN]
    logger.info("Lifecycle: Shutting down...")
    
    if service_instance.mcp_host:
        logger.info("MCPHost: Stopping all MCP Servers...")
        await service_instance.mcp_host.stop()

    if service_instance.surreal_system:
        logger.info("Lifecycle: Closing SurrealDB connection...")
        await service_instance.surreal_system.close()
        
    if service_instance.system_plugin_manager:
        logger.info("Lifecycle: Stopping System Plugins...")
        for pid, plugin in service_instance.system_plugin_manager.plugins.items():
            try:
                plugin.terminate()
            except Exception as e:
                logger.error(f"Error terminating {pid}: {e}")

    if service_instance.ticker:
        service_instance.ticker.stop()

    if service_instance.get_reconciliation_service():
         await service_instance.get_reconciliation_service().stop()
        
    # [Arch 4.0] Output Process Shutdown
    pm = service_instance.get_process_manager()
    if pm:
        await pm.shutdown_all()

    logger.info("Lifecycle: Shutdown complete.")

