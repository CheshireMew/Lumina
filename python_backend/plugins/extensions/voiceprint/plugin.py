import asyncio
import base64
import logging
import time
from typing import Any, Dict, Optional, Tuple

import numpy as np

from core.interfaces.audio_filter import IAudioFilter
from core.interfaces.plugin import Plugin as BasePlugin
from services.audio_filter_chain import AudioFilterChain
from .store import VoiceprintStoreUnavailable, list_profiles

logger = logging.getLogger("VoiceprintPlugin")


class Plugin(BasePlugin, IAudioFilter):
    CACHE_TTL_SECONDS = 5.0

    def __init__(self):
        super().__init__()
        self.driver = None
        self.default_threshold = 0.45
        self.profiles: Dict[str, np.ndarray] = {}
        self.profile_status: Dict[str, bool] = {}
        self.current_profile: Optional[str] = None
        self.loaded_count = 0
        self._last_sync_at = 0.0
        self._driver_loaded = False

    @property
    def priority(self) -> int:
        return 10

    async def load(self, context):
        await super().load(context)

    async def enable(self):
        await super().enable()
        await self.refresh_profiles(force=True)
        await AudioFilterChain.instance().register(self)

        from capabilities.stt import globals as stt_globals

        stt_globals.voiceprint_manager = self

    async def disable(self):
        from capabilities.stt import globals as stt_globals

        if getattr(stt_globals, "voiceprint_manager", None) is self:
            stt_globals.voiceprint_manager = None

        await AudioFilterChain.instance().unregister(self.id)
        await super().disable()

    async def unload(self):
        self.profiles.clear()
        self.profile_status.clear()
        self.current_profile = None
        self.loaded_count = 0
        self._driver_loaded = False
        await super().unload()

    async def health(self) -> dict[str, Any]:
        return {
            "status": "ready" if self.enabled else "disabled",
            "loaded_profiles": self.loaded_count,
            "current_profile": self.current_profile,
        }

    async def ensure_driver_loaded(self):
        if self._driver_loaded and self.driver is not None:
            return
        if self.driver is None:
            from plugins.extensions.voiceauth_sherpa.drivers.voiceauth.sherpa_cam_driver import (
                SherpaCAMDriver,
            )

            self.driver = SherpaCAMDriver()
        await self.driver.load()
        self._driver_loaded = True

    async def filter(
        self,
        audio_data: np.ndarray,
        sample_rate: int,
        metadata: dict,
    ) -> Tuple[bool, Optional[str]]:
        audio_config = getattr(self.context.config, "audio", None)
        if audio_config and not getattr(audio_config, "enable_voiceprint_filter", True):
            return True, None

        await self.refresh_profiles()
        active_profiles = self._get_active_profiles()
        if not active_profiles:
            return True, None
        await self.ensure_driver_loaded()

        threshold = getattr(audio_config, "voiceprint_threshold", self.default_threshold) if audio_config else self.default_threshold
        loop = asyncio.get_running_loop()
        is_match, name, score = await loop.run_in_executor(
            None,
            self.driver.verify,
            audio_data,
            active_profiles,
            threshold,
            sample_rate,
        )

        if is_match:
            logger.info("Voiceprint verified: %s (%.4f)", name, score)
            return True, None
        return False, f"Voiceprint mismatch ({score:.4f} < {threshold:.4f})"

    async def refresh_profiles(self, force: bool = False):
        now = time.monotonic()
        if not force and now - self._last_sync_at < self.CACHE_TTL_SECONDS:
            return

        try:
            results = await list_profiles()
        except VoiceprintStoreUnavailable as exc:
            self.profiles = {}
            self.profile_status = {}
            self.loaded_count = 0
            self._last_sync_at = now
            logger.info("Voiceprint profiles unavailable: %s", exc)
            return
        except Exception as exc:
            self._last_sync_at = now
            logger.error("Failed to refresh voiceprint profiles: %s", exc)
            return

        profiles: Dict[str, np.ndarray] = {}
        profile_status: Dict[str, bool] = {}

        for row in results if isinstance(results, list) else []:
            name = row.get("name")
            embedding_b64 = row.get("embedding")
            if not name or not embedding_b64:
                continue
            try:
                embedding = np.frombuffer(base64.b64decode(embedding_b64), dtype=np.float32).copy()
            except Exception:
                logger.warning("Skipping invalid voiceprint row: %s", name)
                continue

            profiles[name] = embedding
            profile_status[name] = row.get("enabled", True)

        self.profiles = profiles
        self.profile_status = profile_status
        self.loaded_count = len(profiles)
        audio_config = getattr(self.context.config, "audio", None)
        self.current_profile = getattr(audio_config, "voiceprint_profile", "default") if audio_config else "default"
        self._last_sync_at = now

    def _get_active_profiles(self) -> Dict[str, np.ndarray]:
        enabled_profiles = {
            name: embedding
            for name, embedding in self.profiles.items()
            if self.profile_status.get(name, True)
        }
        if not enabled_profiles:
            return {}

        if self.current_profile and self.current_profile in enabled_profiles:
            return {self.current_profile: enabled_profiles[self.current_profile]}
        return enabled_profiles

    def get_metadata(self) -> dict[str, Any]:
        metadata = super().get_metadata()
        metadata.update(
            {
                "name": "Voiceprint Filter",
                "description": "Applies speaker verification before STT using the shared voiceprint database.",
                "func_tag": "Security",
            }
        )
        return metadata
