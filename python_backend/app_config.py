"""Public configuration entrypoint for the Lumina backend."""

import logging
import copy
from enum import Enum
from pathlib import Path
from typing import Any

from config.env_overrides import apply_env_overrides, load_environment

logger = logging.getLogger("ConfigManager")
load_environment(logger)

from config.loader import (  # noqa: E402
    ConfigBundle,
    apply_ports_override,
    load_config,
    save_config,
)
from config.paths import (  # noqa: E402
    APP_ROOT,
    BASE_DIR,
    CONFIG_ROOT,
    DATA_ROOT,
    IS_DEV,
    IS_FROZEN,
    MODELS_DIR,
    get_model_path,
    get_paths_config,
)
from config.secrets_bridge import apply_secret_bridge  # noqa: E402


class ConfigMode(Enum):
    MUTABLE = "mutable"
    FROZEN = "frozen"
    READ_ONLY = "read_only"


class ConfigManager:
    def __init__(self):
        self._mode = ConfigMode.MUTABLE
        self._bundle = ConfigBundle()
        self._bind_bundle(self._bundle)
        self.load_configs()

    @property
    def is_dev(self) -> bool:
        return IS_DEV

    def freeze(self):
        self._mode = ConfigMode.FROZEN
        logger.info("Configuration Frozen")

    def set_read_only(self, value: bool = True):
        self._mode = ConfigMode.READ_ONLY if value else ConfigMode.MUTABLE
        logger.info(f"Configuration Mode: {self._mode.value}")

    def unfreeze(self):
        if self._mode == ConfigMode.READ_ONLY:
            logger.warning("Cannot unfreeze Read-Only configuration")
            return
        self._mode = ConfigMode.MUTABLE
        logger.debug("Configuration Unfrozen")

    @property
    def is_frozen(self) -> bool:
        return self._mode in (ConfigMode.FROZEN, ConfigMode.READ_ONLY)

    @property
    def is_read_only(self) -> bool:
        return self._mode == ConfigMode.READ_ONLY

    def __setattr__(self, key, value):
        if hasattr(self, "_mode") and self._mode in (ConfigMode.FROZEN, ConfigMode.READ_ONLY):
            if not key.startswith("_"):
                raise TypeError(f"Configuration is {self._mode.value}. Cannot modify '{key}'")
        super().__setattr__(key, value)

    def reload(self):
        self.unfreeze()
        self.load_configs()

    def load_configs(self):
        result = load_config(CONFIG_ROOT, BASE_DIR, logger)
        bundle = result.bundle

        apply_ports_override(bundle, BASE_DIR, CONFIG_ROOT, logger)

        if result.should_save:
            save_config(bundle, CONFIG_ROOT, logger)

        apply_secret_bridge(bundle, logger)
        apply_env_overrides(bundle)

        self._bind_bundle(bundle)
        self.freeze()
        logger.info("Configuration Loaded & Applied")

    def save(self):
        if self.is_read_only:
            raise PermissionError("Configuration is read-only")

        try:
            save_config(self._bundle, CONFIG_ROOT, logger)
        except Exception as exc:
            logger.error(f"Failed to save configuration: {exc}")
            raise

    def replace_sections(self, *, persist: bool = True, **sections: Any) -> None:
        """Validate and replace complete config sections as one transaction."""
        if self.is_read_only:
            raise PermissionError("Configuration is read-only")
        known_sections = self._bundle.section_map()
        unknown = set(sections).difference(known_sections)
        if unknown:
            raise KeyError(f"Unknown configuration sections: {sorted(unknown)}")

        candidate = copy.deepcopy(self._bundle)
        for name, value in sections.items():
            expected_type = type(known_sections[name])
            if not isinstance(value, expected_type):
                raise TypeError(
                    f"Configuration section '{name}' must be {expected_type.__name__}"
                )
            setattr(candidate, name, copy.deepcopy(value))

        if persist:
            save_config(candidate, CONFIG_ROOT, logger)
        self._bind_bundle(candidate)

    def _bind_bundle(self, bundle: ConfigBundle) -> None:
        self._bundle = bundle
        self._memory_config = bundle.memory
        self._llm_config = bundle.llm
        self._stt_config = bundle.stt
        self._tts_config = bundle.tts
        self._audio_config = bundle.audio
        self._network_config = bundle.network
        self._models_config = bundle.models
        self._search_config = bundle.search
        self._capabilities_config = bundle.capabilities

    def is_provider_desired_enabled(self, provider_id: str) -> bool:
        return self._capabilities_config.desired_state.get(provider_id, True)

    def set_provider_desired_state(self, provider_id: str, enabled: bool):
        self._capabilities_config.desired_state[provider_id] = enabled

    def get_provider_settings(self, provider_id: str) -> dict[str, Any]:
        return dict(self._capabilities_config.settings.get(provider_id, {}))

    def get_selected_provider(self, capability: str) -> str | None:
        return self._capabilities_config.selected_providers.get(capability)

    def set_selected_provider(self, capability: str, provider_id: str):
        if not provider_id:
            raise ValueError("Selected provider id is required")
        self._capabilities_config.selected_providers[capability] = provider_id
        self._capabilities_config.desired_state.setdefault(provider_id, True)

    @property
    def memory(self):
        return self._memory_config

    @property
    def llm(self):
        return self._llm_config

    @property
    def stt(self):
        return self._stt_config

    @property
    def tts(self):
        return self._tts_config

    @property
    def audio(self):
        return self._audio_config

    @property
    def search(self):
        return self._search_config

    @property
    def capabilities(self):
        return self._capabilities_config

    @property
    def network(self):
        return self._network_config

    @property
    def models(self):
        return self._models_config

    @property
    def paths(self):
        return get_paths_config()

    @property
    def app_root(self) -> Path:
        return APP_ROOT

    @property
    def base_dir(self) -> Path:
        return BASE_DIR

    @property
    def data_root(self) -> Path:
        return DATA_ROOT

    @property
    def config_root(self) -> Path:
        return CONFIG_ROOT


config = ConfigManager()
