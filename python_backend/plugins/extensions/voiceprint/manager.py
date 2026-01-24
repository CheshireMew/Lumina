"""
Modular Voiceprint Manager using Driver Architecture
"""
import logging
import numpy as np
import json
import asyncio
from pathlib import Path
from typing import Dict, Tuple, Optional, List, Any

from core.interfaces.driver import BaseVoiceAuthDriver
# from app_config import config as app_settings # Removed direct config dependency
from core.interfaces.plugin import BaseSystemPlugin

logger = logging.getLogger("VoiceprintManager")

class VoiceprintManager(BaseSystemPlugin):
    @property
    def id(self) -> str:
        return "system.voiceprint"

    @property
    def name(self) -> str:
        return "Voiceprint Security"

    @property
    def description(self) -> str:
        return "Biometric voice authentication. Only allow enrolled users to wake the system."

    @property
    def category(self) -> str:
        return "stt"



    @property
    def func_tag(self) -> str:
        return "Biometric Security"

    @property
    def config_schema(self) -> Dict[str, Any]:
        return {
            "type": "number",
            "key": "voiceprint_threshold",
            "label": "Sensitivity (0.1 - 0.9)",
            "min": 0.1,
            "max": 0.9,
            "step": 0.05,
            "default": 0.6
        }

    @property
    def current_value(self) -> float:
        if hasattr(self, 'context') and self.context:
             return getattr(self.context.config.audio, "voiceprint_threshold", 0.6)
        return 0.6

    async def initialize(self, context: Any):
        """
        Auto-register with container and router.
        """
        # LuminaContext Standard API
        self.context = context

        # [Scheme C] Routes now handled by Main Process (routers/voiceprint.py)
        # No longer need to attach router here.
        self._router = None

        # Resolve Global Data Directory (System-Wide Voiceprints)
        # Bypass default character-scoped get_data_dir()
        from app_config import DATA_ROOT
        global_vp_dir = DATA_ROOT / "system" / "plugins" / "system.voiceprint"
        global_vp_dir.mkdir(parents=True, exist_ok=True)
        
        # Migration: Check if we have data in the character-specific legacy path
        # (This handles the case where user just registered heavily in Hiyori)
        try:
            legacy_char_dir = self.get_data_dir() # Default scoped path
            if legacy_char_dir and legacy_char_dir.exists() and any(legacy_char_dir.iterdir()):
                # Only migrate if global is empty to avoid overwrite conflicts?
                # Or simplistic copy. Let's do simple copy for now.
                if not any(global_vp_dir.iterdir()):
                     logger.info(f"📦 Migrating Character-Scoped Voiceprints -> Global System Storage")
                     self._migrate_profiles(legacy_char_dir, global_vp_dir)
        except Exception as e:
            logger.warning(f"Migration check failed: {e}")

        self.profiles_dir = global_vp_dir
        logger.info(f"📁 Voiceprint Storage: {self.profiles_dir} (Global)")
        
        self.reload_profiles()

        # Register as 'voiceprint_manager' via explicit API
        context.register_service("voiceprint_manager", self)

        # Load Driver
        await self.ensure_driver_loaded()
        
        # Verify Registration
        logger.info(f"✅ VoiceprintManager initialized and registered as 'system.voiceprint'")

    def start(self):
        """Enable voiceprint security."""
        pass

    def stop(self):
        """Disable voiceprint security."""
        pass

    def _migrate_profiles(self, src: Path, dst: Path):
        """Copy existing profiles to new location."""
        if not src.exists(): return
        import shutil
        logger.info(f"鈿狅笍 Migrating Voiceprint profiles: {src} -> {dst}")
        try:
            for item in src.glob("*.npy"):
                shutil.copy2(item, dst / item.name)
            # Metadata
            if (src / "profiles.json").exists():
                shutil.copy2(src / "profiles.json", dst / "profiles.json")
        except Exception as e:
            logger.error(f"Migration failed: {e}")

    def __init__(self, profiles_dir: str = None):
        # Default fallback (Legacy location for migration source)
        self.profiles_dir = Path(__file__).parent / "profiles" 
        if profiles_dir:
             self.profiles_dir = Path(profiles_dir)
            
        # self.profiles_dir.mkdir(exist_ok=True) # Don't create legacy dir if not exists
        
        # Initialize Driver Dynamically
        # Default to SherpaCAM if not specified
        driver_name = "sherpa_cam" 
        # TODO: Get from config if needed
        # driver_name = self.context.config.audio.voice_auth_driver 
        
        try:
            # Try new extension path
            from plugins.extensions.voiceauth_sherpa.drivers.voiceauth.sherpa_cam_driver import SherpaCAMDriver
        except ImportError as e:
            logger.error(f"Failed to import SherpaCAMDriver from extension: {e}")
            raise e

        # Ideally: driver = services.get_driver_factory().create_voice_auth_driver(driver_name)
        # For now, local dynamic import is better than top-level hardcode
        self.driver: BaseVoiceAuthDriver = SherpaCAMDriver()
        
        # State
        self.profiles: Dict[str, np.ndarray] = {}
        self.profile_status: Dict[str, bool] = {} # Enabled status
        self.profiles_meta_cache: Dict[str, float] = {} # [Cache] name -> timestamp
        self.loaded_count = 0
        self._router = None # Backing field for router property
        self.default_threshold = 0.6
        self.current_profile: Optional[str] = None  # Track currently active profile

    @property
    def router(self):
        return self._router

    async def ensure_driver_loaded(self):
        await self.driver.load()

    def reload_profiles(self):
        """Loads all .npy files from profiles directory."""
        self.profiles.clear()
        files = list(self.profiles_dir.glob("*.npy"))
        
        for p in files:
            try:
                emb = np.load(p)
                name = p.stem
                if emb.ndim > 0:
                    self.profiles[name] = emb
                    # Cache Timestamp (Optimization)
                    self.profiles_meta_cache[name] = p.stat().st_mtime * 1000
                    logger.debug(f"Loaded voice profile: {name}")
            except Exception as e:
                logger.error(f"Failed to load profile {p}: {e}")
        
        # Load Enabled Status
        self.profile_status = {} # name -> bool
        meta_path = self.profiles_dir / "profiles.json"
        if meta_path.exists():
            try:
                with open(meta_path, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    for k, v in data.items():
                        # Default True if not specified
                        self.profile_status[k] = v.get("enabled", True)
            except Exception as e:
                logger.warning(f"Failed to load profile metadata: {e}")
        
        # Default all loaded profiles to True if not in metadata
        for p in self.profiles:
            if p not in self.profile_status:
                self.profile_status[p] = True
        
        self.loaded_count = len(self.profiles)
        logger.info(f"VoiceprintManager Ready. Loaded {self.loaded_count} profiles.")

    def verify(self, audio: np.ndarray, threshold: float = None, sample_rate: int = 16000) -> Tuple[bool, str, float]:
        """
        Verify if audio matches ANY enrolled user (Synchronous).
        Returns: (is_match, matched_name, score)
        """
        if not self.profiles:
            # logger.warning("No voice profiles enrolled.")
            return False, "", 0.0
            
        if threshold is None:
            # Try to read from dynamic config first if available
            # Use Context Config
            if hasattr(self, 'context') and self.context:
                threshold = getattr(self.context.config.audio, "voiceprint_threshold", self.default_threshold)
            else:
                threshold = self.default_threshold

        try:
            # Call driver directly (Blocking/Sync)
            is_match, matched_name, score = self.driver.verify(
                audio, 
                # Filter enabled profiles only
                {k:v for k,v in self.profiles.items() if self.profile_status.get(k, True)}, 
                threshold,
                sample_rate
            )
            
            if is_match:
                logger.info(f"Voice Verified: {matched_name} (Score: {score:.2f})")
                
            return is_match, matched_name, score
            return is_match, matched_name, score
        except Exception as e:
            logger.error(f"Verification Failed: {e}")
            return False, "", 0.0

    async def load_profile(self, profile_name: str) -> bool:
        """
        Ensure a specific profile is loaded/active.
        Since we load all profiles on startup, we just check existence 
        or reload if missing.
        """
        if profile_name in self.profiles:
            return True
        
        # Try reloading to see if it appeared on disk
        self.reload_profiles()
        if profile_name in self.profiles:
            self.current_profile = profile_name
            logger.info(f"📁 Loaded voiceprint profile: {profile_name}")
            return True
        return False

    async def register_voiceprint(self, audio: np.ndarray, profile_name: str = "default", sample_rate: int = 16000) -> bool:
        """
        Register a new user profile (Async Wrapper).
        """
        try:
            # Async Defense: Offload CPU-bound embedding extraction
            loop = asyncio.get_running_loop()
            
            embedding = await loop.run_in_executor(
                None,
                self.driver.extract_embedding,
                audio,
                sample_rate
            )

            if embedding.size == 0:
                raise ValueError("Failed to extract embedding from audio")
                
            # Save file
            save_path = self.profiles_dir / f"{profile_name}.npy"
            np.save(save_path, embedding)
            
            # Update Memory
            self.profiles[profile_name] = embedding
            # Update Cache
            self.profiles_meta_cache[profile_name] = save_path.stat().st_mtime * 1000
            
            # Update Metadata json (optional)
            self._update_metadata(profile_name, enabled=True)
            
            logger.info(f"Registered new voice profile: {profile_name}")
            return True
        except Exception as e:
            logger.error(f"Registration failed: {e}")
            return False

    async def get_all_profiles(self) -> List[Dict[str, Any]]:
        """
        Async accessor for router state (compatible with IPC).
        Using cached metadata to be instant.
        """
        profiles_list = []
        for name, embedding in self.profiles.items():
            enabled = self.profile_status.get(name, True)
            # Use cached timestamp if available, else 0 (High Perf)
            created_at = self.profiles_meta_cache.get(name, 0)
                
            profiles_list.append({
                "name": name,
                "enabled": enabled,
                "created_at": created_at
            })
        return profiles_list

    def toggle_profile(self, name: str, enabled: bool):
        if name in self.profiles:
             self.profile_status[name] = enabled
             self._update_metadata(name, enabled=enabled)
             logger.info(f"Toggled voiceprint '{name}' to {enabled}")
             return True
        return False

    def _update_metadata(self, name: str, enabled: bool = True):
        meta_path = self.profiles_dir / "profiles.json"
        data = {}
        if meta_path.exists():
            try:
                with open(meta_path, 'r', encoding='utf-8') as f:
                    data = json.load(f)
            except Exception as e:
                logger.warning(f"Failed to load profile metadata, starting fresh: {e}")
            
        # Merge existing metadata with updates
        # Merge existing metadata with updates
        if name not in data: data[name] = {}
        
        npy_path = self.profiles_dir / f"{name}.npy"
        if npy_path.exists():
            data[name]["created_at"] = str(npy_path.stat().st_mtime)
            
        data[name]["enabled"] = enabled
        
        with open(meta_path, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=2)

    # Legacy Compatibility Property
    @property
    def user_embedding(self):
        """Compatibility for old code that checks voiceprint_manager.user_embedding"""
        # Return the 'default' profile if it exists, else use the first one
        if "default" in self.profiles:
            return self.profiles["default"]
        if self.profiles:
            return next(iter(self.profiles.values()))
        return None
