"""Config file loading, saving, port overrides, and legacy migration."""

import json
import logging
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, Iterable, Optional

from services.provider_aliases import normalize_provider_id

from .models import (
    AudioConfig,
    LLMConfig,
    MemoryConfig,
    ModelsConfig,
    NetworkConfig,
    PluginsConfig,
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
    plugins: PluginsConfig = field(default_factory=PluginsConfig)

    def section_map(self) -> Dict[str, Any]:
        return {
            "memory": self.memory,
            "llm": self.llm,
            "tts": self.tts,
            "stt": self.stt,
            "audio": self.audio,
            "network": self.network,
            "search": self.search,
            "plugins": self.plugins,
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
            "plugins": self.plugins.model_dump(),
        }


@dataclass(frozen=True)
class ConfigLoadResult:
    bundle: ConfigBundle
    source_path: Optional[Path]
    migrated_legacy_paths: tuple[Path, ...] = ()
    should_save: bool = False


def load_config(config_root: Path, base_dir: Path, logger: logging.Logger) -> ConfigLoadResult:
    yaml_path = config_root / "config.yaml"
    if yaml_path.exists():
        data = _read_yaml(yaml_path, logger)
        bundle = hydrate_config(data, logger)
        logger.info(f"Loaded unified config from {yaml_path}")
        return ConfigLoadResult(bundle=bundle, source_path=yaml_path)

    logger.info("config.yaml not found. Attempting migration from legacy JSONs...")
    data, legacy_paths = _load_legacy_jsons(config_root, base_dir, logger)
    bundle = hydrate_config(data, logger)
    return ConfigLoadResult(
        bundle=bundle,
        source_path=None,
        migrated_legacy_paths=tuple(legacy_paths),
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
def archive_legacy_jsons(paths: Iterable[Path], logger: logging.Logger) -> None:
    for path in paths:
        if not path.exists():
            continue

        archived_path = path.with_suffix(path.suffix + ".migrated")
        index = 1
        while archived_path.exists():
            archived_path = path.with_suffix(path.suffix + f".migrated.{index}")
            index += 1

        try:
            path.rename(archived_path)
            logger.info(f"Archived legacy config {path} -> {archived_path}")
        except Exception as exc:
            logger.warning(f"Failed to archive legacy config {path}: {exc}")


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
        "plugins": PluginsConfig,
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

    plugins_data = dict(normalized.get("plugins", {}) or {})
    plugin_settings = dict(plugins_data.get("settings", {}) or {})
    desired_state = dict(plugins_data.get("desired_state", {}) or {})
    selected_providers = dict(plugins_data.get("selected_providers", {}) or {})

    if "selected_providers" not in plugins_data:
        legacy_provider_map = {
            "stt": (normalized.get("stt") or {}).get("provider"),
            "tts": (normalized.get("tts") or {}).get("provider"),
            "tool.search": (normalized.get("search") or {}).get("provider"),
            "memory": (normalized.get("memory") or {}).get("provider"),
        }
        for capability, provider_id in legacy_provider_map.items():
            if provider_id:
                normalized_provider_id = normalize_provider_id(capability, provider_id)
                selected_providers.setdefault(capability, normalized_provider_id)
                desired_state.setdefault(normalized_provider_id, True)

    if "brave" in normalized:
        plugin_settings.setdefault("brave", normalized["brave"])

    plugins_data["settings"] = plugin_settings
    plugins_data["desired_state"] = desired_state
    plugins_data["selected_providers"] = selected_providers
    normalized["plugins"] = plugins_data

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


def _load_legacy_jsons(
    config_root: Path,
    base_dir: Path,
    logger: logging.Logger,
) -> tuple[Dict[str, Any], list[Path]]:
    merged: Dict[str, Any] = {}
    loaded_paths: list[Path] = []

    candidates = (
        ("memory_config.json", _merge_legacy_memory_config),
        ("audio_config.json", _merge_legacy_audio_config),
    )

    for filename, merge_func in candidates:
        for root in _legacy_roots(config_root, base_dir):
            path = root / filename
            if not path.exists():
                continue

            try:
                merge_func(merged, _read_json(path))
                if _is_relative_to(path, config_root):
                    loaded_paths.append(path)
                logger.info(f"Loaded legacy config from {path}")
                break
            except Exception as exc:
                logger.error(f"Failed to load legacy config {path}: {exc}")

    return merged, loaded_paths


def _legacy_roots(config_root: Path, base_dir: Path) -> tuple[Path, ...]:
    return (config_root, base_dir, base_dir.parent)


def _is_relative_to(path: Path, root: Path) -> bool:
    try:
        path.resolve().relative_to(root.resolve())
        return True
    except ValueError:
        return False


def _merge_legacy_memory_config(target: Dict[str, Any], data: Dict[str, Any]) -> None:
    llm_data = {
        key: data[key]
        for key in ("api_key", "base_url", "model")
        if key in data and data[key] is not None
    }
    if llm_data:
        target.setdefault("llm", {}).update(llm_data)

    memory_keys = (
        "provider",
        "namespace",
        "database",
        "character_id",
        "history_limit",
        "overflow_strategy",
    )
    memory_data = {
        key: data[key]
        for key in memory_keys
        if key in data and data[key] is not None
    }
    if memory_data:
        target.setdefault("memory", {}).update(memory_data)

    if data.get("embedder"):
        target.setdefault("models", {})["embedding_model_name"] = data["embedder"]


def _merge_legacy_audio_config(target: Dict[str, Any], data: Dict[str, Any]) -> None:
    audio_keys = (
        "device_name",
        "enable_voiceprint_filter",
        "voiceprint_threshold",
        "voiceprint_profile",
    )
    audio_data = {
        key: data[key]
        for key in audio_keys
        if key in data and data[key] is not None
    }
    if audio_data:
        target.setdefault("audio", {}).update(audio_data)
