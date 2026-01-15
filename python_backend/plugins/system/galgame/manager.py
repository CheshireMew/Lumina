import logging
import asyncio
from typing import Any
from datetime import datetime

from core.interfaces.plugin import BaseSystemPlugin
from .computation import SoulMath

logger = logging.getLogger("GalgameManager")

class GalgameManager(BaseSystemPlugin):
    """
    Galgame State Manager.
    Role: Handles dynamic state changes like Energy Decay, Mood Timeouts, etc.
    """
    
    @property
    def id(self) -> str:
        return "galgame-manager"

    @property
    def name(self) -> str:
        return "Galgame Mode"

    @property
    def category(self) -> str:
        return "game"
        
    @property
    def description(self) -> str:
        return "Implements Energy, Mood, and Galgame mechanics."
        
    @property
    def enabled(self) -> bool:
        return getattr(self, '_enabled', True)

    @enabled.setter
    def enabled(self, value: bool):
        self._enabled = value


    def initialize(self, context: Any):
        """
        Auto-register with container and router.
        """
        # LuminaContext Standard API
        self.context = context 
        
        self.soul = context.soul 
        self.ticker = context.ticker
        
        # Inject Soul Logic into LLM Manager
        # Using context.llm_manager API
        if context.llm_manager:
            context.llm_manager.set_parameter_calculator(SoulMath.calculate_llm_params)
            logger.info("馃 Injected SoulMath calculation into LLMManager")
        else:
              logger.warning("鈿狅笍 LLMManager not found in context, parameter tuning disabled.")

        # Register Context Provider (V2)
        try:
             from services.container import services
             from .provider import GalgameContextProvider
             provider = GalgameContextProvider(self)
             services.register_context_provider(provider)
             logger.info("馃帹 Registered Galgame Context Provider")
        except Exception as e:
             logger.error(f"Failed to register context provider: {e}")

        # Register Plugin Prompts
        try:
             from prompt_manager import prompt_manager
             from pathlib import Path
             prompt_path = Path(__file__).parent / "prompts"
             prompt_manager.add_template_path(prompt_path)
             logger.info(f"馃搨 Registered prompts: {prompt_path}")
        except Exception as e:
             logger.error(f"Failed to register prompts: {e}")

        # Subscribe to Ticker (Check every minute)
        self.ticker.subscribe_minutes(self.on_minute)
        
        # Config
        self.interval_minutes = 5
        self.last_run_minute = -1
        
        # Persistence Migration
        # Persistence Migration
        # self.container = container # Removed legacy direct assignment
        self._ensure_migration()
        
        # Load Config
        self.enabled = self.load_data().get("enabled", True)
        if not self.enabled:
            logger.info("鈴革笍 Galgame Manager is DISABLED in config.")

        # Register self via EventBus
        context.register_service("galgame_manager", self)
        
        # Create and Expose Router
        try:
             from .router import create_router
             self._router = create_router(self)
             logger.info("馃攲 Galgame Router Mounted")
        except Exception as e:
             logger.error(f"Failed to mount Galgame Router: {e}")
        
        logger.info(f"馃幃 Galgame Manager Initialized (Enabled: {self.enabled})")

    def _ensure_migration(self):
        """Migrate legacy state.json to data/galgame-manager.json if needed."""
        # Check if already migrated
        data = self.load_data()
        if data:
            logger.info("鉁?Galgame data persistence verified.")
            return

        # Try load legacy
        logger.info("鈿狅笍 Migrating Galgame state from legacy...")
        legacy_state = self.soul._load_state() # Raw read from state.json
        if "galgame" in legacy_state:
            # We found legacy data!
            migrated_data = legacy_state["galgame"]
            self.save_data(migrated_data)
            logger.info("鉁?Migration complete: state.json -> data/galgame-manager.json")
        else:
            # Init fresh defaults
            default_data = {
                "relationship": {"level": 0, "progress": 0, "current_stage_label": "Stranger", "user_name": "Master"},
                "energy_level": 100,
                "last_interaction": datetime.now().isoformat()
            }
            self.save_data(default_data)
            logger.info("鉁?Initialized fresh Galgame data.")

    async def on_minute(self, now: datetime):
        """
        Energy Decay Logic or other state updates.
        """
        if not self.enabled:
            return

    # ================= Logic Migrated from SoulManager =================

    def mutate_mood(self, d_p=0.0, d_a=0.0, d_d=0.0):
        """Allows dynamic mood shifts during conversation."""
        if not self.enabled: return

        self.soul.profile = self.soul._load_profile()
        pad = self.soul.profile.setdefault("personality", {}).setdefault("pad_model", {})
        pad["pleasure"] = max(0.0, min(1.0, pad.get("pleasure", 0.5) + d_p))
        pad["arousal"] = max(0.0, min(1.0, pad.get("arousal", 0.5) + d_a))
        pad["dominance"] = max(0.0, min(1.0, pad.get("dominance", 0.5) + d_d))
        self.soul.save_profile()
        logger.info(f"[Galgame] Mood mutated: P={pad['pleasure']:.2f}, A={pad['arousal']:.2f}, D={pad['dominance']:.2f}")

    def update_energy(self, delta: float):
        """Updates energy level."""
        if not self.enabled: return

        # Use Own Persistence
        state = self.load_data()
        current = state.get("energy_level", 100)
        new_level = max(0, min(100, current + delta))
        state["energy_level"] = new_level
        self.save_data(state)
        logger.info(f"[Galgame] Energy updated: {current} -> {new_level}")

        # Sync back to Soul Profile (for Frontend Compat)
        self.soul.profile = self.soul._merge_profile()

    def update_intimacy(self, delta: int):
        """Updates Level based Progress."""
        if not self.enabled: return

        # Use Own Persistence
        data = self.load_data()
        rel = data.setdefault("relationship", {})
        
        # Init defaults if missing
        if "level" not in rel: rel["level"] = 2
        if "progress" not in rel: rel["progress"] = rel.get("intimacy_score", 50)
        
        level = rel["level"]
        progress = rel["progress"]
        
        # Apply delta
        progress += delta
        
        # Level Up/Down Logic
        if progress >= 100:
            if level < 5:
                level += 1
                progress -= 100
                logger.info(f"[Galgame] 馃帀 Level Up! Now Level {level}")
            else:
                progress = 100
        elif progress < 0:
            if level > -3:
                level -= 1
                progress += 100
                logger.info(f"[Galgame] 馃挃 Level Down... Now Level {level}")
            else:
                progress = 0
                
        rel["level"] = level
        rel["progress"] = progress
        
        # Cleanup old field
        if "intimacy_score" in rel:
            del rel["intimacy_score"]
            
        # Sync label
        from .computation import SoulMath
        stage_info = SoulMath.get_relationship_stage(level)
        rel["current_stage_label"] = stage_info["label"]

        self.save_data(data)
        
        # Sync Frontend
        self.soul.profile = self.soul._merge_profile()
