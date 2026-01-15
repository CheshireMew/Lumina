import json
import os
from datetime import datetime
from typing import Dict, Any
from pathlib import Path
from pathlib import Path
from services.soul.persistence import SoulPersistence
from services.soul.renderer import SoulRenderer


class SoulManager:
    """
    Manages the 'Soul' of the AI (Core Profile).
    Handles loading/saving profile, interpreting personality traits,
    and rendering the dynamic system prompt.
    Soul Manager - Refactored
    Supports multiple characters, separates User Config, AI Personality, GalGame State
    """
    def __init__(self, character_id: str = "hiyori", auto_create: bool = False):
        self.character_id = character_id
        # ⚠️ Fix: Use absolute path based on file location
        self.base_dir = Path(__file__).parent / "characters" / character_id
        
        # Three independent file paths
        # [Refactor] Services
        self.persistence = SoulPersistence(self.base_dir)
        self.renderer = SoulRenderer()

        # Auto Scaffold
        if not self.base_dir.exists():
            if auto_create:
                self._scaffold_character()
            else:
                 print(f"[SoulManager] ⚠️ Character '{self.character_id}' not found.")

        # Load data
        self.config = self.persistence.load_config()
        self.soul = self._load_soul() 
        self.state = self._load_state()
        
        # Legacy Compatibility
        self.profile = self._merge_profile()
        self._context_helper = None


    # ================= End Generic Persistence API =================
    
    def get_system_prompt(self, user_context: Dict = {}) -> str:
        """
        Delegates to SoulRenderer.
        """
        return self.renderer.render(
            config_prompt=self.config.get("system_prompt", "You are a helpful AI."),
            identity={"name": self.config.get("name"), "description": self.config.get("description")},
            personality=self.soul.get("personality", {}),
            state=self.state.get("galgame", {}),
            user_context=user_context
        )

    def set_context_helper(self, helper):
        """Injects external logic helper (e.g. SoulMath from GalgamePlugin)"""
        self._context_helper = helper
        print(f"[SoulManager] Context helper injected: {helper.__name__}")
        
    def get_module_data_dir(self, module_id: str) -> Path:
        """
        Get or create data directory for a specific module.
        Base dir is usually python_backend/data/modules/{module_id}
        """
        # Define root data directory. 
        # Using self.base_dir.parent.parent would go to python_backend/characters/.. -> python_backend
        # Ideally, we should have a dedicated data_root.
        # Let's map it to python_backend/data/modules/{module_id}
        
        # Path(__file__).parent is python_backend/
        root = Path(__file__).parent / "data" / "modules" / module_id
        root.mkdir(parents=True, exist_ok=True)
        return root

    def load_module_data(self, module_id: str) -> Dict[str, Any]:
        """Load JSON data for a specific module."""
        path = self.get_module_data_dir(module_id) / "data.json"
        if path.exists():
            try:
                with open(path, "r", encoding="utf-8") as f:
                    return json.load(f)
            except Exception as e:
                print(f"[SoulManager] Failed to load data for {module_id}: {e}")
        return {}

    def save_module_data(self, module_id: str, data: Dict[str, Any]):
        """Save JSON data for a specific module."""
        path = self.get_module_data_dir(module_id) / "data.json"
        try:
            with open(path, "w", encoding="utf-8") as f:
                json.dump(data, f, indent=4, ensure_ascii=False)
        except Exception as e:
            print(f"[SoulManager] Failed to save data for {module_id}: {e}")
    
    def _load_config(self) -> Dict[str, Any]:
        return self.persistence.load_config()
    
    def _load_soul(self) -> Dict[str, Any]:
        """Load AI evolved personality data"""
        if not self.soul_path.exists():
            return {"error": "Soul not found"}
        try:
            with open(self.soul_path, 'r', encoding='utf-8') as f:
                return json.load(f)
        except Exception as e:
            print(f"[SoulManager] Error loading soul: {e}")
            return {}
    
    def _load_state(self) -> Dict[str, Any]:
        """Load GalGame State (STRICT: Only support module data)"""
        # Load from Module Data
        module_data = self.persistence.load_module_data("galgame-manager")
        if module_data:
            return {"galgame": module_data, "character_id": self.character_id}

        # New character default (empty)
        return {"character_id": self.character_id, "galgame": {}}

    def _merge_profile(self) -> Dict[str, Any]:
        """Merge Data for Legacy Compatibility"""
        galgame_state = self.state.get("galgame", {})
        return {
            "identity": {
                "name": self.config.get("name", self.character_id),
                "age": self.config.get("age"),  # Optional
                "description": self.config.get("description", "")
            },
            "personality": self.soul.get("personality", {}),
            "state": {
                "current_mood": galgame_state.get("current_mood", "neutral"),
                "energy_level": galgame_state.get("energy_level", 100),
                "last_interaction": galgame_state.get("last_interaction"),
                "pending_interaction": galgame_state.get("pending_interaction")
            },
            "relationship": galgame_state.get("relationship", {}),
            "custom_prompt": self.config.get("system_prompt", "")  # User-defined identity override
        }

    def _scaffold_character(self):
        """Initialize new character file structure"""
        print(f"[SoulManager] Scaffolding new character: {self.character_id}")
        self.base_dir.mkdir(parents=True, exist_ok=True)
        
        # 1. Config Template
        default_config = {
            "character_id": self.character_id,
            "name": self.character_id,
            "display_name": "New Character",
            "description": "A new digital soul.",
            "system_prompt": "You are a helpful AI assistant.",
            "live2d_model": "Hiyori (Default)",
            "voice_config": {"service": "gpt-sovits", "voiceId": "default"}
        }
        self.persistence.save_config(default_config)
            
        # 2. Soul Template (Evolution Engine Module)
        default_soul = {
            "character_id": self.character_id,
            "personality": {
                "traits": ["friendly"],
                "big_five": {"openness": 0.5, "conscientiousness": 0.5, "extraversion": 0.5, "agreeableness": 0.5, "neuroticism": 0.5},
                "pad_model": {"pleasure": 0.5, "arousal": 0.5, "dominance": 0.5}
            },
            "state": {"current_mood": "neutral"},
            "last_updated": datetime.now().isoformat()
        }
        self.persistence.save_module_data("evolution_engine", default_soul)
            
        # 3. State Template (GalGame Module)
        default_galgame = {
            "relationship": {"level": 0, "progress": 0, "current_stage_label": "Stranger", "user_name": "Master"},
            "energy_level": 100,
            "last_interaction": datetime.now().isoformat()
        }
        self.persistence.save_module_data("galgame-manager", default_galgame)

    def _load_profile(self) -> Dict[str, Any]:
        """
        Reloads all components from disk and returns the merged profile.
        Used by mutation methods to ensure they are working on the latest data.
        """
        self.config = self._load_config()
        self.soul = self._load_soul()
        self.state = self._load_state()
        self.profile = self._merge_profile()
        return self.profile
    
    def _load_soul(self) -> Dict[str, Any]:
        """Load AI Personality (STRICT: Only support module data)"""
        # Load from Module Data
        module_data = self.persistence.load_module_data("evolution_engine")
        if module_data:
             return module_data

        return {}

    def save_soul(self):
        """Save AI evolved personality data (STRICT)"""
        self.persistence.save_module_data("evolution_engine", self.soul)
    
    def save_state(self):
        """Save GalGame State (STRICT)"""
        data = self.state.get("galgame", {})
        self.persistence.save_module_data("galgame-manager", data)
    
    def save_config(self):
        self.persistence.save_config(self.config)
    
    def save_profile(self):
        """
        Backward compatibility: Sync profile data to soul and state files
        Called when legacy code modifies self.profile
        """
        try:
            # Sync personality and current_mood to soul
            if "personality" in self.profile:
                self.soul["personality"] = self.profile["personality"]
            if "state" in self.profile and "current_mood" in self.profile["state"]:
                self.soul.setdefault("state", {})["current_mood"] = self.profile["state"]["current_mood"]
            self.soul["last_updated"] = datetime.now().isoformat()
            self.save_soul()
            
            # Sync relationship and energy_level to state
            if "relationship" in self.profile:
                self.state.setdefault("galgame", {})["relationship"] = self.profile["relationship"]
            if "state" in self.profile:
                if "energy_level" in self.profile["state"]:
                    self.state.setdefault("galgame", {})["energy_level"] = self.profile["state"]["energy_level"]
                if "last_interaction" in self.profile["state"]:
                    self.state.setdefault("galgame", {})["last_interaction"] = self.profile["state"]["last_interaction"]
            self.save_state()
            
            # 閲嶆柊鍚堝苟浠ヤ繚鎸?self.profile 鍚屾
            self.profile = self._merge_profile()
            
        except Exception as e:
            print(f"[SoulManager] Error in save_profile: {e}")

    def get_pad_mood_description(self) -> str:
        """
        Converts PAD (Pleasure, Arousal, Dominance) values to a descriptive adjective.
        Simplified logic.
        """
        pad = self.profile.get("personality", {}).get("pad_model", {})
        p = pad.get("pleasure", 0.5)
        a = pad.get("arousal", 0.5)
        d = pad.get("dominance", 0.5)

        if self._context_helper and hasattr(self._context_helper, "get_pad_description"):
            return self._context_helper.get_pad_description(p, a)

        # Fallback (Simpler)
        if p > 0.6: return "Positive"
        elif p < 0.4: return "Negative"
        return "Neutral"

    def get_extraversion_desc(self) -> str:
        e = self.profile.get("personality", {}).get("big_five", {}).get("extraversion", 0.5)
        if e > 0.7: return "Initiate conversation often, be expressive"
        if e < 0.3: return "Be reserved, listen more than talk"
        return "Balance listening and talking"

    def get_energy_instruction(self) -> str:
        """
        Maps Energy Level to Tone and Length instructions (Galgame Style).
        """
        energy = self.profile.get("state", {}).get("energy_level", 50)
        
        if self._context_helper and hasattr(self._context_helper, "get_energy_instruction"):
            return self._context_helper.get_energy_instruction(energy)
            
        return "Speak normally."

    def get_relationship_stage(self) -> dict:
        """
        Determines current relationship based on LEVEL.
        Returns label and desc.
        """
        rel = self.profile.get("relationship", {})
        # Default to 0 (Stranger) if missing
        level = rel.get("level", 0) 
        
        if self._context_helper and hasattr(self._context_helper, "get_relationship_stage"):
            return self._context_helper.get_relationship_stage(level)

        # Fallback
        return {"stage": "Stranger", "label": "Stranger", "desc": "Standard interaction."}

    def render_dynamic_instruction(self) -> str:
        """
        Renders the dynamic part of the system prompt.
        Includes: Mood, Energy, Relationship Stage
        """
        # ... logic
        
    # [REMOVED] update_intimacy - Logic moved to GalgamePlugin (GalgameManager)

    def render_static_prompt(self) -> str:
        """
        Legacy: Used by DeepSeek Context Caching.
        Delegate to Renderer.
        """
        return self.get_system_prompt()

    def render_dynamic_instruction(self) -> str:
        """
        Delegate to Renderer for dynamic context.
        """
        if not self.config.get("galgame_mode_enabled", True):
             return ""
             
        # Prepare params
        rel = self.profile.get("relationship", {})
        state = self.profile.get("state", {})
        personality = self.profile.get("personality", {})
        
        return self.renderer.render_dynamic_context(
            state={
                "energy_level": state.get('energy_level', 100),
                "energy_instruction": self.get_energy_instruction(),
                "mood_desc": self.get_pad_mood_description(),
                "user_name": rel.get('user_name', 'master'),
                "rel_label": self.get_relationship_stage()['label'],
                "rel_desc": self.get_relationship_stage()['desc'],
                "shared_memories": rel.get('shared_memories_summary', 'None')
            },
            personality=personality,
            time_str=datetime.now().strftime('%Y-%m-%d %H:%M')
        )

    # [REMOVED] update_last_interaction (Duplicate)
    # [REMOVED] set_pending_interaction (Duplicate)
    # [REMOVED] update_energy (Duplicate)


    def render_system_prompt(self, relevant_memories: str = "") -> str:
        """
        Legacy / Backward Compatibility Method.
        """
        return self.render_static_prompt() + "\n\n" + self.render_dynamic_instruction()

    # [DEPRECATED] Logic moved to GalgameManager
    pass

    # [DEPRECATED] Logic moved to GalgameManager
    pass

    # [DEPRECATED] Logic moved to GalgameManager
    pass

    def update_last_interaction(self):
        """Updates the timestamp of the last interaction."""
        # ⚠️ Fix: Load State directly to update the Source of Truth
        self.state = self._load_state()
        galgame = self.state.setdefault("galgame", {})
        
        galgame["last_interaction"] = datetime.now().isoformat()
        
        # Interaction happened, clear pending
        if "pending_interaction" in galgame:
             del galgame["pending_interaction"]
             
        self.save_state()
        
        # Update local profile view
        self.profile = self._merge_profile()

    def set_pending_interaction(self, pending: bool, reason: str = "", data: Dict[str, Any] = None):
        """Sets a flag indicating the AI wants to initiate conversation."""
        # ⚠️ Fix: Load State directly to ensure persistence
        self.state = self._load_state() 
        galgame = self.state.setdefault("galgame", {})
        
        if pending:
            payload = {
                "timestamp": datetime.now().isoformat(), 
                "reason": reason
            }
            if data:
                payload["data"] = data
                
            galgame["pending_interaction"] = payload
            print(f"[SoulManager] 🔔 Pending Interaction SET: {reason}")
        elif "pending_interaction" in galgame:
            del galgame["pending_interaction"]
            print(f"[SoulManager] ❌ Pending Interaction CLEARED -> Resetting Idle Timer")
            # ⚠️ Fix: Reset idle timer when AI takes action to stop duplicate triggers
            galgame["last_interaction"] = datetime.now().isoformat()
            
        self.save_state()
        # Update local profile to reflect change
        self.profile = self._merge_profile()

    # [REMOVED] update_traits - Logic moved to EvolutionPlugin
    # [REMOVED] update_current_mood - Logic moved to EvolutionPlugin
    # [REMOVED] update_big_five - Logic moved to EvolutionPlugin

    def bulk_update_user_name(self, new_name: str) -> int:
        """
        Iterate over all character directories and update user_name in galgame-manager.json.
        """
        import json
        updated_count = 0
        try:
            # Assume characters dir is sibling to soul_manager.py
            chars_dir = self.base_dir.parent 
            if not chars_dir.exists():
                return 0
                
            for char_dir in chars_dir.iterdir():
                if not char_dir.is_dir(): continue
                
                # Preferred: galgame-manager.json
                galgame_path = char_dir / "galgame-manager.json"
                legacy_path = char_dir / "state.json"
                
                target_files = []
                if galgame_path.exists(): target_files.append(galgame_path)
                if legacy_path.exists(): target_files.append(legacy_path)
                
                char_updated = False
                for fpath in target_files:
                    try:
                        with open(fpath, 'r', encoding='utf-8') as f:
                            data = json.load(f)
                            
                        # Update relationship.user_name
                        rel = data.get("relationship", {})
                        if rel.get("user_name") != new_name:
                            if "relationship" not in data: data["relationship"] = {}
                            data["relationship"]["user_name"] = new_name
                            
                            with open(fpath, 'w', encoding='utf-8') as f:
                                json.dump(data, f, ensure_ascii=False, indent=2)
                            char_updated = True
                    except Exception as ie:
                        print(f"[SoulManager] Error updating {fpath}: {ie}")
                        
                if char_updated:
                    updated_count += 1

        except Exception as e:
            print(f"[SoulManager] Bulk Update Error: {e}")
            raise
            
        return updated_count

    # [REMOVED] update_pad - Logic moved to EvolutionPlugin
    # [REMOVED] set_pending_interaction (Duplicate)
    # [REMOVED] update_energy (Duplicate)

if __name__ == "__main__":
    # Test
    mgr = SoulManager()
    print(mgr.render_system_prompt("Checking database..."))
    # mgr.mutate_mood(d_p=-0.1) # Test mood shift
