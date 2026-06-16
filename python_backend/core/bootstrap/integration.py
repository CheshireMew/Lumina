"""
Integration Bootstrappers.
Handles components that require FastAPI app instance or cross-cutting concerns.
"""

import logging
from typing import Any
from fastapi import FastAPI
from .interface import Bootstrapper

logger = logging.getLogger("Bootstrap.Integration")


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
