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
        container.get_event_bus()

        from services.chat.event_adapter import ChatTurnEventAdapter

        adapter = ChatTurnEventAdapter(container.get_companion_runtime())
        container.set_chat_turn_event_adapter(adapter)
        adapter.start()
        logger.info("✅ Chat turn event adapter initialized")


class MCPHostBootstrapper(Bootstrapper):
    """
    Initialize MCP (Model Context Protocol) Host.
    Provides tool execution and context management.
    """
    
    @property
    def name(self) -> str:
        return "MCPHost"
    
    async def bootstrap(self, container: Any):
        from services.mcp_host import MCPHost

        # [Architecture 5.0] Inject ProcessManager for Governance
        pm = container.get_process_manager()
        container.set_mcp_host(MCPHost(container.get_soul(), process_manager=pm))
        logger.info("🔌 MCP Host Initialized (Start Disabled)")
