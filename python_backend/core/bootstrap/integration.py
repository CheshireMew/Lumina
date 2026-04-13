"""
Integration Bootstrappers.
Handles components that require FastAPI app instance or cross-cutting concerns.
"""

import logging
from typing import Any
from fastapi import FastAPI
from .interface import Bootstrapper

logger = logging.getLogger("Bootstrap.Integration")


class RouterBootstrapper(Bootstrapper):
    """
    Initialize RouterManager with EventBus subscription.
    Requires FastAPI app instance for dynamic route mounting.
    """
    
    def __init__(self, app: FastAPI):
        self._app = app
    
    @property
    def name(self) -> str:
        return "RouterManager"
    
    async def bootstrap(self, container: Any):
        from services.router_manager import RouterManager
        
        # EventBus should be ready by now (Level 1)
        rm = RouterManager(self._app, bus=container.event_bus)
        container.router_manager = rm
        logger.info("✅ RouterManager Bootstrapped & Subscribed")


class ChatBridgeBootstrapper(Bootstrapper):
    """
    Initialize Legacy/MVP ChatBridge helper.
    Provides simple chat interface for testing.
    """
    
    @property
    def name(self) -> str:
        return "ChatBridge"
    
    async def bootstrap(self, container: Any):
        if not container.event_bus:
            logger.debug("ChatBridge skipped: No EventBus")
            return
        
        try:
            from services.chat_bridge import BasicChatBridge
            container.chat_bridge = BasicChatBridge(container.get_chat_turn_service())
            container.chat_bridge.start()
            logger.info("✅ ChatBridge Initialized")
        except Exception as e:
            logger.debug(f"ChatBridge init skipped: {e}")


class MCPHostBootstrapper(Bootstrapper):
    """
    Initialize MCP (Model Context Protocol) Host.
    Provides tool execution and context management.
    """
    
    @property
    def name(self) -> str:
        return "MCPHost"
    
    async def bootstrap(self, container: Any):
        if not container.soul:
            logger.debug("MCPHost skipped: No Soul service")
            return
        
        try:
            from services.mcp_host import MCPHost
            
            # [Architecture 5.0] Inject ProcessManager for Governance
            pm = container.get_process_manager()
            container.mcp_host = MCPHost(container.soul, process_manager=pm)
            logger.info("🔌 MCP Host Initialized (Start Disabled)")
        except Exception as e:
            logger.warning(f"Failed to init MCP Host: {e}")


class SystemPluginRouterBootstrapper(Bootstrapper):
    """
    Mount routers from System Plugins.
    Runs after SystemPluginsBootstrapper to ensure plugins are loaded.
    """
    
    def __init__(self, app: FastAPI):
        self._app = app
    
    @property
    def name(self) -> str:
        return "SystemPluginRouters"
    
    async def bootstrap(self, container: Any):
        if not container.system_plugin_manager:
            return
        
        for pid, plugin in container.system_plugin_manager.plugins.items():
            if getattr(plugin, 'router', None) and not getattr(plugin, '_router_registered', False):
                self._app.include_router(plugin.router)
                plugin._router_registered = True
                logger.debug(f"Mounted router for plugin: {pid}")
        
        logger.info("✅ System Plugin Routers Mounted")
