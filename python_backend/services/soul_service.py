
import logging
from typing import Dict, Any, Optional
from core.interfaces.soul import BaseSoulDriver

logger = logging.getLogger("SoulService")

class SoulService:
    """
    Core Service for managing the AI's "Soul" (Generic Personality/State Engine).
    Replaces the monolithic SoulManager.
    
    Responsibilities:
    1. Hold the active Soul Driver (e.g., Galgame, Jarvis).
    2. Delegate Prompt Rendering to the Driver.
    3. Delegate Interaction Hooks to the Driver.
    """
    
    def __init__(self):
        self._drivers: Dict[str, BaseSoulDriver] = {}
        self._active_driver: Optional[BaseSoulDriver] = None
        
        # [NEW] Persistence & Multi-Character Support
        from services.soul.persistence import SoulPersistence
        from app_config import BASE_DIR
        
        # Assumption: characters dir is sibling to python_backend or inside it?
        # routers/characters.py uses: Path(__file__).parent.parent / "characters"
        # which is python_backend/characters.
        # APP_CONFIG BASE_DIR is python_backend/
        self.characters_root = BASE_DIR / "characters"
        
        self._active_character_id = "hiyori" # Default
        self._persistence: Optional[SoulPersistence] = None
        self._ensure_persistence()

    def _ensure_persistence(self):
        """Initialize persistence for active character."""
        from services.soul.persistence import SoulPersistence
        char_dir = self.characters_root / self._active_character_id
        # Ensure dir exists?
        char_dir.mkdir(parents=True, exist_ok=True)
        self._persistence = SoulPersistence(char_dir)

    def set_active_character(self, character_id: str):
        """Switch active character and reload persistence."""
        if not (self.characters_root / character_id).exists():
            raise FileNotFoundError(f"Character {character_id} not found")
            
        self._active_character_id = character_id
        self._ensure_persistence()
        logger.info(f"🎭 Active Character Switched to: {character_id}")
        
    def register_driver(self, driver: BaseSoulDriver):
        """Plugin registers itself as a potential Soul."""
        self._drivers[driver.id] = driver
        logger.info(f"Registered Soul Driver: {driver.id} ({driver.metadata.get('name')})")
        
        # Auto-activate if it's the first one (Simple logic for now)
        # TODO: persistent preference
        if self._active_driver is None:
            self.set_active_driver(driver.id)

    def set_active_driver(self, driver_id: str):
        if driver_id in self._drivers:
            self._active_driver = self._drivers[driver_id]
            logger.info(f"馃憤 Active Soul Switched to: {driver_id}")
        else:
            logger.error(f"Cannot switch to unknown driver: {driver_id}")

    async def get_system_prompt(self, context: Dict[str, Any] = {}) -> str:
        """
        Generates system prompt using standard 'system.yaml' template + Character Config.
        """
        # 1. Try Active Driver first (if it overrides prompt generation)
        if self._active_driver:
            # Note: Drivers might want to use the standard template too, 
            # but for now we give them full control if they claim it.
            # If driver returns None/Empty, fallback? Let's check.
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
            
            # Load Character Config
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
            # Order matches YAML keys naturally or we enforce specific order?
            # YAML 1.1+ preserves order usually, but safer to enforce key list if needed.
            # For now, iterate:
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

    # ================= Compatibility Layer (Facade) =================
    
    @property
    def profile(self) -> Dict[str, Any]:
        """Facade for Driver State to match legacy SoulManager.profile structure."""
        if self._active_driver:
            # The Driver should expose a property or method to get the full profile
            # For now, let's assume get_state() returns it or closes enough
            if hasattr(self._active_driver, "get_state"):
                return self._active_driver.get_state()
        return {}
        
    @property
    def config(self) -> Dict[str, Any]:
        """Facade for character config."""
        # TODO: Proper config management
        return {}

    def save_profile(self):
        """Facade for saving state."""
        if self._active_driver and hasattr(self._active_driver, "save_state"):
             # We assume modification happened in place on the dict returned by .profile
             # In a real driver, we might need explicit set_state
             pass

    def update_last_interaction(self):
        """Facade."""
        if self._active_driver and hasattr(self._active_driver, "on_interaction"):
             # We treat this as a signal, though on_interaction usually takes text
             pass
             
    def bulk_update_user_name(self, new_name: str) -> int:
        """
        Legacy feature: Update all characters on disk.
        We can move the logic here or keep it as a standalone utility.
        For now, stub it or reimplement if critical.
        """
        return 0

    # ================= Persistence Delegates =================
    
    def load_module_data(self, module_id: str) -> Dict[str, Any]:
        """Delegate to active persistence."""
        if self._persistence:
            return self._persistence.load_module_data(module_id)
        return {}

    def save_module_data(self, module_id: str, data: Dict[str, Any]):
        """Delegate to active persistence."""
        if self._persistence:
            self._persistence.save_module_data(module_id, data)

    # ================= Config Delegates =================
    
    def load_character_config(self) -> Dict[str, Any]:
        """Delegate to active persistence."""
        if self._persistence:
            return self._persistence.load_config()
        return {}

    def save_character_config(self, data: Dict[str, Any]):
        """Delegate to active persistence."""
        if self._persistence:
            self._persistence.save_config(data)

    def get_module_data_dir(self, module_id: str) -> Optional[Any]:
        # SoulPersistence._resolve_data_root returns Path
        if self._persistence:
            # We assume plugins manage their own subdirs inside data root if needed
            # But the contract typically asks for a folder.
            # SoulPersistence doesn't expose get_module_dir explicitly, it puts json files there.
            # New behavior: Return root/data/{module_id}/ for assets? 
            # Or just return root/data/ for generic?
            # Existing context.get_data_dir implementation mapped to soul_client.get_module_data_dir
            # Let's check logic in SoulPersistence... it manages JSONs.
            # Let's add a helper to SoulPersistence for binary dirs if needed, or just return data_root.
            root = self._persistence._resolve_data_root()
            # Create a subdir for the plugin to ensure isolation?
            plugin_dir = root / module_id
            plugin_dir.mkdir(parents=True, exist_ok=True)
            return plugin_dir
        return None
