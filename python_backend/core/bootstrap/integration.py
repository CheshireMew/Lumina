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
        from services.chat.event_adapter import ChatTurnEventAdapter

        adapter = ChatTurnEventAdapter(
            container.get_companion_runtime(),
            container.get_event_bus(),
            container.get_gateway(),
        )
        container.set_chat_turn_event_adapter(adapter)
        adapter.start()
        logger.info("✅ Chat turn event adapter initialized")


