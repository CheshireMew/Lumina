import logging
import asyncio
from typing import Any
from datetime import datetime

from core.interfaces.plugin import BaseSystemPlugin
from .legacy_dreaming import Dreaming

logger = logging.getLogger("DreamingManager")

class DreamingManager(BaseSystemPlugin):
    """
    Dreaming System Plugin.
    Role: Long-term Memory Consolidation & Soul Evolution.
    """
    
    @property
    def id(self) -> str:
        return "dreaming-manager"

    @property
    def name(self) -> str:
        return "Dreaming System"

    @property
    def description(self) -> str:
        return "Manages long-term memory consolidation and evolution during idle times."

    @property
    def llm_routes(self) -> list[str]:
        return ["dreaming"]

    @property
    def router(self) -> Any:
        return getattr(self, "_router", None)

    def initialize(self, context: Any):
        # LuminaContext Standard API
        self.context = context
        self.ticker = context.ticker
        
        # Initialize Legacy Dreaming Instance
        # Requires memory_client. 
        # Note: context.memory maps to SurrealMemory
        try:
             # Assuming context has 'memory' (SurrealDB)
             # And getting character_id from Soul or Config
             char_id = "default"
             if context.soul and hasattr(context.soul, "character_id"):
                 char_id = context.soul.character_id
             
             self.legacy_dreaming = Dreaming(
                 memory_client=context.memory,
                 character_id=char_id
             )
        except Exception as e:
            logger.error(f"Failed to init legacy dreaming: {e}")
            return

        # Register self
        context.register_service("dreaming_service", self.legacy_dreaming)
        
        # Create and Expose Router
        from .router import create_router
        self._router = create_router(self.legacy_dreaming)
        logger.info("馃攲 Dreaming Router Mounted")
        
        # Subscribe to Ticker (Check every minute)
        self.ticker.subscribe_minutes(self.on_minute)
        
        # Config
        self.interval_minutes = 5
        self.last_run_minute = -1
        if not hasattr(self, '_enabled'):
             self._enabled = True # Default
        
        logger.info("📡 Dreaming Manager Initialized (subscribed to Global Ticker)")

    @property
    def enabled(self) -> bool:
        return getattr(self, '_enabled', True)

    @enabled.setter
    def enabled(self, value: bool):
        self._enabled = value

    async def on_minute(self, now: datetime):
        """
        Called every minute.
        """
        if now.minute % self.interval_minutes == 0 and now.minute != self.last_run_minute:
            self.last_run_minute = now.minute
            
            # Use lock from legacy dreaming?
            # It has internal lock `_digest_in_progress`.
            # We just trigger it.
            try:
                # Late Injection of Evolution Engine (via EventBus service discovery)
                if not self.legacy_dreaming.evolution_engine:
                    evolution_engine = self.context.bus.get_service("evolution_engine")
                    if evolution_engine:
                        self.legacy_dreaming.evolution_engine = evolution_engine
                        logger.debug("馃К EvolutionEngine injected into Dreaming via EventBus")

                # logger.debug("Triggering Dreaming Cycle...")
                await self.legacy_dreaming.process_memories()
            except Exception as e:
                logger.error(f"Dreaming cycle error: {e}")
