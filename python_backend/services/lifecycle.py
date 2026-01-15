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
    from core.bootstrap.infrastructure import ConfigBootstrapper, DatabaseBootstrapper, EventBusBootstrapper
    from core.bootstrap.services import CoreServicesBootstrapper, PluginServicesBootstrapper, MiddlewareBootstrapper, SystemPluginsBootstrapper
    
    # 1. Initialize Bootstrap Manager
    manager = BootstrapManager()
    
    # 2. Define Startup Phase Order
    manager.add(ConfigBootstrapper())       # Level 0: Config
    manager.add(DatabaseBootstrapper())     # Level 1: Persistence
    manager.add(EventBusBootstrapper())     # Level 1: Messaging
    manager.add(CoreServicesBootstrapper()) # Level 2: Core Logic (LLM/Soul)
    manager.add(PluginServicesBootstrapper()) # Level 3: I/O (Vision/TTS/STT)
    manager.add(MiddlewareBootstrapper())   # Level 3: Chat Pipeline Components
    manager.add(SystemPluginsBootstrapper())# Level 4: External Plugins
    
    # 3. Execute
    try:
        await manager.start(service_instance)
    except Exception as e:
        logger.critical(f"Startup Failed: {e}")
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
        if service_instance.soul_client:
            service_instance.mcp_host = MCPHost(service_instance.soul_client)
            logger.info("🔌 MCP Host Initialized (Start Disabled)")
    except: pass

    yield
    
    # [SHUTDOWN]
    logger.info("Lifecycle: Shutting down...")
    
    if service_instance.mcp_host:
        logger.info("MCPHost: Stopping all MCP Servers...")
        await service_instance.mcp_host.stop()

    if service_instance.surreal_system:
        logger.info("Lifecycle: Closing SurrealDB connection...")
        await service_instance.surreal_system.close()
        
    if service_instance.ticker:
        service_instance.ticker.stop()
        
    logger.info("Lifecycle: Shutdown complete.")

