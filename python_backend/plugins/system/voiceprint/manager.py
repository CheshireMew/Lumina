"""
Modular Voiceprint Manager using Driver Architecture
"""
import logging
import numpy as np
import json
import asyncio
from pathlib import Path
from typing import Dict, Tuple, Optional, Any

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

    def initialize(self, context: Any):
        """
        Auto-register with container and router.
        """
        # LuminaContext Standard API
        self.context = context

        # [NEW] Attach Router for Auto-Mounting
        from plugins.system.voiceprint.router import router
        self._router = router

        # Resolve Data Directory
        new_dir = self.get_data_dir() # Uses self.context via BaseSystemPlugin
        if new_dir:
            if not any(new_dir.iterdir()):
                 self._migrate_profiles(self.profiles_dir, new_dir)
            
            self.profiles_dir = new_dir
            logger.info(f"馃帳 Voiceprint profiles path: {self.profiles_dir}")
        
        self.reload_profiles()

        # Register as 'voiceprint_manager' via explicit API
        context.register_service("voiceprint_manager", self)
        
        # Inject into Plugins Router (Legacy Shim - Removed)
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
        
        from plugins.drivers.voiceauth.sherpa_cam_driver import SherpaCAMDriver
        # Ideally: driver = services.get_driver_factory().create_voice_auth_driver(driver_name)
        # For now, local dynamic import is better than top-level hardcode
        self.driver: BaseVoiceAuthDriver = SherpaCAMDriver()
        
        # State
        self.profiles: Dict[str, np.ndarray] = {}
        self.profile_status: Dict[str, bool] = {} # Enabled status
        self.loaded_count = 0
        self._router = None # Backing field for router property

    @property
    def router(self):
        return self._router
        
        # Config
        self.default_threshold = 0.6 
        
        # Defer Loading to initialize()

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

    async def verify(self, audio: np.ndarray, threshold: float = None) -> Tuple[bool, str, float]:
        """
        Verify if audio matches ANY enrolled user (Async Wrapper).
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

        # Async Defense: Offload CPU-bound numpy work to thread pool
        # driver.verify is synchronous
        loop = asyncio.get_running_loop()
        try:
            is_match, matched_name, score = await loop.run_in_executor(
                None, 
                self.driver.verify, 
                audio, 
                # Filter enabled profiles only
                {k:v for k,v in self.profiles.items() if self.profile_status.get(k, True)}, 
                threshold
            )
            
            if is_match:
                logger.info(f"Voice Verified: {matched_name} (Score: {score:.2f})")
                
            return is_match, matched_name, score
        except Exception as e:
            logger.error(f"Async Verification Failed: {e}")
            return False, "", 0.0

    async def register_voiceprint(self, audio: np.ndarray, profile_name: str = "default") -> bool:
        """
        Register a new user profile (Async Wrapper).
        """
        try:
            # Async Defense: Offload CPU-bound embedding extraction
            loop = asyncio.get_running_loop()
            
            embedding = await loop.run_in_executor(
                None,
                self.driver.extract_embedding,
                audio
            )

            if embedding.size == 0:
                raise ValueError("Failed to extract embedding from audio")
                
            # Save file
            save_path = self.profiles_dir / f"{profile_name}.npy"
            np.save(save_path, embedding)
            
            # Update Memory
            self.profiles[profile_name] = embedding
            
            # Update Metadata json (optional)
            self._update_metadata(profile_name, enabled=True)
            
            logger.info(f"Registered new voice profile: {profile_name}")
            return True
        except Exception as e:
            logger.error(f"Registration failed: {e}")
            return False

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
        if name not in data: data[name] = {}
        data[name]["created_at"] = str(Path(self.profiles_dir / f"{name}.npy").stat().st_mtime)
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
