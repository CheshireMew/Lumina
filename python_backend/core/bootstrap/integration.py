"""
Integration Bootstrappers.
Handles components that require FastAPI app instance or cross-cutting concerns.
"""

import logging
from typing import Any
from fastapi import FastAPI
from .interface import Bootstrapper

logger = logging.getLogger("Bootstrap.Integration")


class ChatTurnEventAdapterBootstrapper(Bootstrapper):
    """Connect EventBus text input events to the chat turn service."""
    
    @property
    def name(self) -> str:
        return "ChatTurnEventAdapter"
    
    async def bootstrap(self, container: Any):
        if not container.has_service("event_bus"):
            logger.debug("Chat turn event adapter skipped: No EventBus")
            return
        
        try:
            from services.chat.event_adapter import ChatTurnEventAdapter

            adapter = ChatTurnEventAdapter(
                container.get_chat_turn_service()
            )
            container.set_chat_turn_event_adapter(adapter)
            adapter.start()
            logger.info("✅ Chat turn event adapter initialized")
        except Exception as e:
            logger.debug(f"Chat turn event adapter init skipped: {e}")


class MCPHostBootstrapper(Bootstrapper):
    """
    Initialize MCP (Model Context Protocol) Host.
    Provides tool execution and context management.
    """
    
    @property
    def name(self) -> str:
        return "MCPHost"
    
    async def bootstrap(self, container: Any):
        try:
            from services.mcp_host import MCPHost
            
            # [Architecture 5.0] Inject ProcessManager for Governance
            pm = container.get_process_manager()
            container.set_mcp_host(MCPHost(container.get_soul(), process_manager=pm))
            logger.info("🔌 MCP Host Initialized (Start Disabled)")
        except Exception as e:
            logger.warning(f"Failed to init MCP Host: {e}")
