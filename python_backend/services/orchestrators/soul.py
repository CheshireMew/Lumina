
import logging
from typing import Dict, Any, Optional
from pathlib import Path
from core.interfaces.soul import BaseSoulDriver
from core.interfaces.repository import ISoulRepository
from services.repositories.file_soul_repository import FileSoulRepository

logger = logging.getLogger("SoulService")

class SoulService:
    """
    Core Service for managing the AI's "Soul" (Generic Personality/State Engine).
    
    Responsibilities:
    1. Hold the active Soul Driver.
    2. Delegate Prompt Rendering to the Driver.
    3. Delegate Interaction Hooks to the Driver.
    4. Manage Persistence via Repository.
    """
    
    async def initialize(self):
        """Initialize the SoulService async components."""
        # Future setup if needed
        logger.info("SoulService Initialized")

    def __init__(self, system_config=None, repo: ISoulRepository = None, memory_service=None):
        self.system_config = system_config
        self.memory_service = memory_service
        self._drivers: Dict[str, BaseSoulDriver] = {}
        self._active_driver: Optional[BaseSoulDriver] = None
        
        # [Refactor] Use Repository
        self.repo = repo or FileSoulRepository()
        
        # Sync Repo with Config if possible
        if system_config and hasattr(system_config, 'memory'):
             self.repo.set_character_id(system_config.memory.character_id)

    def get_active_character_id(self) -> str:
        """Return the current character from the repository boundary."""
        if hasattr(self.repo, "get_character_id"):
            return self.repo.get_character_id()
        if self.system_config and hasattr(self.system_config, "memory"):
            return self.system_config.memory.character_id
        return "hiyori"
        
    def register_driver(self, driver: BaseSoulDriver):
        """Plugin registers itself as a potential Soul."""
        self._drivers[driver.id] = driver
        logger.info(f"Registered Soul Driver: {driver.id} ({driver.metadata.get('name')})")
        
        # Auto-activate if it's the first one (Simple logic for now)
        if self._active_driver is None:
            self.set_active_driver(driver.id)

    def set_active_driver(self, driver_id: str):
        if driver_id in self._drivers:
            self._active_driver = self._drivers[driver_id]
            logger.info(f"👍 Active Soul Switched to: {driver_id}")
        else:
            logger.error(f"Cannot switch to unknown driver: {driver_id}")

    async def get_system_prompt(self, context: Dict[str, Any] = None) -> str:
        """
        Generates system prompt using standard 'system.yaml' template + Character Config.
        """
        if context is None:
            context = {}
        # 1. Try Active Driver first (if it overrides prompt generation)
        if self._active_driver:
            driver_prompt = await self._active_driver.get_system_prompt(context)
            if driver_prompt and len(driver_prompt) > 10:
                return driver_prompt

        # 2. Standard Logic: Load Template & Render
        try:
            import yaml
            from jinja2 import Template
            from app_config import BASE_DIR
            
            # Load Template
            template_path = BASE_DIR / "prompts" / "chat" / "system.yaml"
            if not template_path.exists():
                logger.warning(f"System template not found at {template_path}")
                return "You are a helpful AI assistant."

            with open(template_path, 'r', encoding='utf-8') as f:
                raw_yaml = yaml.safe_load(f)
            
            # Load Character Config via Repository
            char_config = self.load_character_config()
            
            # Prepare Vars
            render_vars = {
                "char_name": char_config.get("name", "AI"),
                "description": char_config.get("description", ""),
                "custom_prompt": char_config.get("system_prompt", ""), # User's custom instructions
                **context
            }
            
            # Render Sections
            parts = []
            for key, value in raw_yaml.items():
                if isinstance(value, str):
                    t = Template(value)
                    parts.append(t.render(**render_vars))
            
            return "\n\n".join(parts)
            
        except Exception as e:
            logger.error(f"Failed to render system template: {e}")
            # Fallback
            config = self.load_character_config()
            return config.get("system_prompt", "You are a helpful AI assistant.")

    async def on_interaction(self, user_input: str, ai_response: str, context: Dict[str, Any] = {}):
        """
        Delegates interaction events to the driver (for XP/Memory/Mood updates).
        """
        if self._active_driver:
            await self._active_driver.on_interaction(user_input, ai_response, context)

    # ================= Runtime State =================
    
    @property
    def profile(self) -> Dict[str, Any]:
        """Return the active driver state combined with persisted runtime state."""
        state = {}
        if self._active_driver and hasattr(self._active_driver, "get_state"):
            state.update(self._active_driver.get_state())
        state.update(self.load_module_data("soul.runtime"))
        return state
        
    @property
    def config(self) -> Dict[str, Any]:
        """Return the active character config."""
        return self.load_character_config()

    def save_profile(self):
        """Persist the active runtime state."""
        self.save_module_data("soul.runtime", self.profile)

    def update_last_interaction(self):
        """Persist the last user interaction timestamp."""
        state = self.load_module_data("soul.runtime")
        state["last_interaction_at"] = __import__("time").time()
        self.save_module_data("soul.runtime", state)

    def get_llm_adjustment_state(self) -> Dict[str, Any]:
        """Expose the small personality state needed by LLM parameter routing."""
        config = self.config
        if not config.get("soul_evolution_enabled", True):
            return {}

        profile = self.profile
        personality = profile.get("personality", {})
        return {
            "pad": personality.get(
                "pad_model",
                {"pleasure": 0.5, "arousal": 0.5, "dominance": 0.5},
            ),
            "big_five": personality.get(
                "big_five",
                {
                    "openness": 0.5,
                    "conscientiousness": 0.5,
                    "extraversion": 0.5,
                    "agreeableness": 0.5,
                    "neuroticism": 0.5,
                },
            ),
        }

    # ================= Persistence Delegates (Repository) =================
    
    def load_module_data(self, module_id: str) -> Dict[str, Any]:
        """Delegate to repository."""
        return self.repo.load_module_data(module_id)

    def save_module_data(self, module_id: str, data: Dict[str, Any]):
        """Delegate to repository."""
        self.repo.save_module_data(module_id, data)

    # ================= Config Delegates =================
    
    def load_character_config(self) -> Dict[str, Any]:
        """Delegate to repository."""
        return self.repo.load_config()

    def save_character_config(self, data: Dict[str, Any]):
        """Delegate to repository."""
        self.repo.save_config(data)

    def get_module_data_dir(self, module_id: str) -> Path:
        """Delegate to repository."""
        return self.repo.get_data_dir(module_id)
