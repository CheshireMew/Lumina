"""Config file loading, saving, and port overrides."""

import json
import logging
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, Optional

from .models import (
    AudioConfig,
    CapabilitiesConfig,
    FREE_LLM_PROVIDER_ID,
    LLMConfig,
    MemoryConfig,
    ModelsConfig,
    NetworkConfig,
    POLLINATIONS_BASE_URL,
    POLLINATIONS_DEFAULT_MODEL,
    SearchConfig,
    STTConfig,
    TTSConfig,
)

try:
    import yaml
except ImportError:
    yaml = None


@dataclass
class ConfigBundle:
    memory: MemoryConfig = field(default_factory=MemoryConfig)
    llm: LLMConfig = field(default_factory=LLMConfig)
    stt: STTConfig = field(default_factory=STTConfig)
    tts: TTSConfig = field(default_factory=TTSConfig)
    audio: AudioConfig = field(default_factory=AudioConfig)
    network: NetworkConfig = field(default_factory=NetworkConfig)
    models: ModelsConfig = field(default_factory=ModelsConfig)
    search: SearchConfig = field(default_factory=SearchConfig)
    capabilities: CapabilitiesConfig = field(default_factory=CapabilitiesConfig)

    def section_map(self) -> Dict[str, Any]:
        return {
            "memory": self.memory,
            "llm": self.llm,
            "tts": self.tts,
            "stt": self.stt,
            "audio": self.audio,
            "network": self.network,
            "search": self.search,
            "capabilities": self.capabilities,
            "models": self.models,
        }

    def to_dict(self) -> Dict[str, Any]:
        return {
            "network": self.network.model_dump(),
            "memory": self.memory.model_dump(),
            "llm": self.llm.model_dump(),
            "stt": self.stt.model_dump(),
            "tts": self.tts.model_dump(),
            "audio": self.audio.model_dump(),
            "search": self.search.model_dump(),
            "models": self.models.model_dump(),
            "capabilities": self.capabilities.model_dump(),
        }


@dataclass(frozen=True)
class ConfigLoadResult:
    bundle: ConfigBundle
    source_path: Optional[Path]
    should_save: bool = False


def load_config(config_root: Path, base_dir: Path, logger: logging.Logger) -> ConfigLoadResult:
    yaml_path = config_root / "config.yaml"
    if yaml_path.exists():
        data = _read_yaml(yaml_path, logger)
        bundle = hydrate_config(data, logger)
        logger.info(f"Loaded unified config from {yaml_path}")
        return ConfigLoadResult(bundle=bundle, source_path=yaml_path)

    logger.info("config.yaml not found. Using default configuration.")
    bundle = ConfigBundle()
    return ConfigLoadResult(
        bundle=bundle,
        source_path=None,
        should_save=True,
    )


def save_config(bundle: ConfigBundle, config_root: Path, logger: logging.Logger) -> None:
    if not yaml:
        logger.error("Cannot save config: PyYAML not installed.")
        return

    yaml_path = config_root / "config.yaml"
    yaml_path.parent.mkdir(parents=True, exist_ok=True)
    with open(yaml_path, "w", encoding="utf-8") as file:
        yaml.dump(bundle.to_dict(), file, allow_unicode=True, default_flow_style=False)

    logger.info(f"Configuration saved to {yaml_path}")


def apply_ports_override(
    bundle: ConfigBundle,
    base_dir: Path,
    config_root: Path,
    logger: logging.Logger,
) -> Optional[Path]:
    for path in _ports_override_paths(base_dir, config_root):
        if not path.exists():
            continue

        try:
            data = _read_json(path)
            bundle.network = NetworkConfig(**{**bundle.network.model_dump(), **data})
            logger.info(f"Ports overridden by {path}")
            return path
        except Exception as exc:
            logger.error(f"Failed to load ports.json override from {path}: {exc}")

    return None


def hydrate_config(data: Dict[str, Any], logger: logging.Logger) -> ConfigBundle:
    normalized = normalize_config_dict(data)
    bundle = ConfigBundle()

    constructors = {
        "network": NetworkConfig,
        "memory": MemoryConfig,
        "llm": LLMConfig,
        "stt": STTConfig,
        "tts": TTSConfig,
        "audio": AudioConfig,
        "search": SearchConfig,
        "models": ModelsConfig,
        "capabilities": CapabilitiesConfig,
    }

    for section, constructor in constructors.items():
        if section not in normalized:
            continue
        try:
            setattr(bundle, section, constructor(**normalized[section]))
        except Exception as exc:
            logger.error(f"Hydration error in section '{section}': {exc}")

    return bundle


def normalize_config_dict(data: Dict[str, Any]) -> Dict[str, Any]:
    normalized = dict(data or {})

    if "capabilities" in normalized:
        capabilities_data = dict(normalized.get("capabilities") or {})
        if "settings" in capabilities_data:
            capabilities_data["settings"] = dict(capabilities_data.get("settings") or {})
        if "desired_state" in capabilities_data:
            capabilities_data["desired_state"] = dict(capabilities_data.get("desired_state") or {})
        if "selected_providers" in capabilities_data:
            capabilities_data["selected_providers"] = dict(capabilities_data.get("selected_providers") or {})
        normalized["capabilities"] = capabilities_data

    if "llm" in normalized:
        llm_data = dict(normalized.get("llm") or {})
        providers = dict(llm_data.get("providers") or {})
        free_provider = dict(providers.get(FREE_LLM_PROVIDER_ID) or {})
        if free_provider.get("type") == "pollinations":
            free_provider["base_url"] = free_provider.get("base_url") or POLLINATIONS_BASE_URL
            if str(free_provider.get("api_key", "")).strip().lower() == "none":
                free_provider["api_key"] = ""
            legacy_pollinations_models = {"gpt-4o-mini", "gpt-4o", "claude-3-haiku", "openai"}
            provider_models = free_provider.get("models") or []
            if any(model in legacy_pollinations_models for model in provider_models):
                free_provider["models"] = [POLLINATIONS_DEFAULT_MODEL]
            providers[FREE_LLM_PROVIDER_ID] = free_provider
            llm_data["providers"] = providers

        legacy_pollinations_models = {"gpt-4o-mini", "gpt-4o", "claude-3-haiku", "openai"}
        routes = dict(llm_data.get("routes") or {})
        for route_id, route_data in list(routes.items()):
            route = dict(route_data or {})
            if (
                route.get("provider_id") == FREE_LLM_PROVIDER_ID
                and route.get("model") in legacy_pollinations_models
            ):
                route["model"] = POLLINATIONS_DEFAULT_MODEL
                routes[route_id] = route
        if routes:
            llm_data["routes"] = routes

        normalized["llm"] = llm_data

    return normalized


def _read_yaml(path: Path, logger: logging.Logger) -> Dict[str, Any]:
    if not yaml:
        logger.error("YAML config exists but PyYAML is not installed. Using defaults.")
        return {}

    try:
        with open(path, "r", encoding="utf-8") as file:
            return yaml.safe_load(file) or {}
    except Exception as exc:
        logger.error(f"Failed to load config.yaml: {exc}")
        return {}


def _read_json(path: Path) -> Dict[str, Any]:
    with open(path, "r", encoding="utf-8-sig") as file:
        data = json.load(file)
    return data if isinstance(data, dict) else {}


def _ports_override_paths(base_dir: Path, config_root: Path) -> tuple[Path, ...]:
    return (
        base_dir.parent / "config" / "ports.json",
        config_root / "config" / "ports.json",
        config_root / "ports.json",
    )
