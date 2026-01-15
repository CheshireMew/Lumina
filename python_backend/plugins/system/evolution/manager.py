from typing import Any
import logging
from core.interfaces.plugin import BaseSystemPlugin
from .engine import EvolutionEngine

logger = logging.getLogger("EvolutionManager")

class EvolutionManager(BaseSystemPlugin):
    """
    Plugin wrapper for Soul Evolution Engine.
    """

    @property
    def id(self) -> str:
        return "evolution_engine"

    @property
    def name(self) -> str:
        return "Soul Evolution Service"

    @property
    def category(self) -> str:
        # [User Request] Move to Game Tab
        return "game"

    @property
    def description(self) -> str:
         return "Evolve character personality over time based on interactions."

    @property
    def llm_routes(self) -> list[str]:
        return ["evolution"]

    @property
    def enabled(self) -> bool:
        return self.config.get("enabled", True)

    @property
    def config_schema(self):
        return {"type": "boolean", "key": "enabled", "label": "Enable Evolution"}

    def initialize(self, context: Any):
        # LuminaContext Standard API
        self.context = context
        
        # Persistence Migration (Phase 8)
        self._ensure_migration()

        # Load Config
        if not self.enabled:
            logger.info("鈴革笍 Soul Evolution Engine is DISABLED in config.")
            return

        # Register Prompts
        from prompt_manager import prompt_manager
        import os
        base_dir = os.path.dirname(__file__)
        prompts_dir = os.path.join(base_dir, "prompts")
        if os.path.exists(prompts_dir):
            prompt_manager.add_template_path(prompts_dir)
            logger.info(f"馃搨 Registered Evolution Prompts: {prompts_dir}")

        # Instantiate Engine
        # EvolutionEngine needs access to LLM and Soul, context provides these
        self.engine = EvolutionEngine(context)
        
        # Register to container so Dreaming can find it
        context.register_service("evolution_engine", self.engine)
        
        # Autonomous Evolution
        # Subscribe to minute ticks for daily maintenance
        if self.config.get("auto_evolve", True):
             context.bus.subscribe("system.tick.minute", self.handle_tick)
        
        logger.info(f"馃К Soul Evolution Engine Initialized (Enabled: {self.enabled})")

    async def handle_tick(self, event):
        """Check for daily maintenance window (default 4 AM)"""
        # Parse timestamp from event or use current time
        # Event payload: {"timestamp": iso_str}
        try:
            from datetime import datetime
            ts = event.data.get("timestamp")
            if ts:
                now = datetime.fromisoformat(ts)
            else:
                now = datetime.now()
                
            scheduled_hour = self.config.get("scheduled_hour", 4)
            
            # Run at XX:00
            if now.hour == scheduled_hour and now.minute == 0:
                logger.info("鈴?Triggering Daily Evolution Maintenance...")
                soul_mgr = self.context.soul
                if not soul_mgr: return
                
                # 1. Consolidate Memories (Summary)
                await self.engine.consolidate_memories(soul_mgr)
                
                # 2. Evolve Personality (Traits)
                await self.engine.analyze_and_evolve(soul_mgr)
                
        except Exception as e:
            logger.error(f"Error in Evolution Tick: {e}")

    def _ensure_migration(self):
        """Migrate legacy soul.json to data/evolution_engine.json"""
        if self.load_data():
            logger.info("鉁?Evolution data persistence verified.")
            return

        logger.info("鈿狅笍 Migrating Evolution data from legacy...")
        soul_mgr = self.context.soul
        if not soul_mgr: return

        # Load raw legacy (force read from file via internal method if possible, or just use what we have)
        # We modified _load_soul to read module data first. Since module data is empty, it reads soul.json.
        legacy_data = soul_mgr._load_soul() 
        
        if legacy_data and "personality" in legacy_data:
            self.save_data(legacy_data)
            logger.info("鉁?Migration complete: soul.json -> data/evolution_engine.json")
        else:
             # Default
             pass
        
        
        # Register to container so Dreaming can find it
        # self.container.evolution_engine = self.engine # Deprecated: use register_service
        
        logger.info("馃К Soul Evolution Engine Initialized")
