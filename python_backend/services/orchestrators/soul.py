
import logging
import re
from typing import Dict, Any, Optional
from pathlib import Path
from core.interfaces.soul import BaseSoulDriver
from core.interfaces.repository import ISoulRepository
from services.repositories.file_soul_repository import FileSoulRepository

logger = logging.getLogger("SoulService")
SOUL_DRIVER_CONFIG_KEY = "soul_driver_id"


def _read_prompt_sections(path: Path) -> Dict[str, str]:
    sections: Dict[str, str] = {}
    current_key: Optional[str] = None
    current_lines: list[str] = []

    def flush_current():
        if current_key is not None:
            sections[current_key] = "\n".join(current_lines).strip()

    for raw_line in path.read_text(encoding="utf-8").splitlines():
        if not raw_line.strip():
            if current_key is not None:
                current_lines.append("")
            continue

        if not raw_line.startswith((" ", "\t")) and ":" in raw_line:
            flush_current()
            key, value = raw_line.split(":", 1)
            current_key = key.strip()
            current_lines = []
            value = value.strip()
            if value and value != "|":
                current_lines.append(value)
            continue

        if current_key is not None:
            current_lines.append(raw_line[2:] if raw_line.startswith("  ") else raw_line.strip())

    flush_current()
    return sections


def _render_template(text: str, values: Dict[str, Any]) -> str:
    def replace(match: re.Match[str]) -> str:
        expression = match.group(1).strip()
        if "|" in expression:
            name, filter_expr = [part.strip() for part in expression.split("|", 1)]
            value = str(values.get(name, ""))
            if filter_expr.startswith("indent(") and filter_expr.endswith(")"):
                width = int(filter_expr[7:-1] or "0")
                prefix = " " * width
                return "\n".join(f"{prefix}{line}" if line else line for line in value.splitlines())
            return value
        return str(values.get(expression, ""))

    return re.sub(r"\{\{\s*(.*?)\s*\}\}", replace, text)

class SoulService:
    """
    Core Service for managing the AI's "Soul" (Generic Personality/State Engine).
    
    Responsibilities:
    1. Hold the active Soul Driver.
    2. Delegate Prompt Rendering to the Driver.
    3. Delegate interaction behavior to the Driver.
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
        
        if repo is None:
            if system_config is None:
                raise ValueError("SoulService requires system_config or repo")
            repo = FileSoulRepository(character_id=system_config.memory.character_id)
        elif system_config is not None:
            repo.set_character_id(system_config.memory.character_id)

        self.repo = repo

    def get_active_character_id(self) -> str:
        """Return the current character from the repository boundary."""
        return self.repo.get_character_id()

    def _selected_driver_id(self) -> Optional[str]:
        value = self.load_character_config().get(SOUL_DRIVER_CONFIG_KEY)
        return value if isinstance(value, str) and value.strip() else None
        
    def register_driver(self, driver: BaseSoulDriver):
        """Register a Soul driver without changing the selected runtime driver."""
        self._drivers[driver.id] = driver
        logger.info(f"Registered Soul Driver: {driver.id} ({driver.metadata.get('name')})")

        if self._selected_driver_id() == driver.id:
            self._active_driver = driver
            logger.info(f"Active Soul restored from character config: {driver.id}")

    def set_active_driver(self, driver_id: str):
        if driver_id not in self._drivers:
            raise ValueError(f"Unknown Soul driver: {driver_id}")

        self._active_driver = self._drivers[driver_id]
        config = self.load_character_config()
        config[SOUL_DRIVER_CONFIG_KEY] = driver_id
        self.save_character_config(config)
        logger.info(f"Active Soul switched to: {driver_id}")

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
            from app_config import BASE_DIR
            
            # Load Template
            template_path = BASE_DIR / "prompts" / "chat" / "system.yaml"
            if not template_path.exists():
                logger.warning(f"System template not found at {template_path}")
                return "You are a helpful AI assistant."

            prompt_sections = _read_prompt_sections(template_path)
            
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
            for key, value in prompt_sections.items():
                if isinstance(value, str):
                    parts.append(_render_template(value, render_vars))
            
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
