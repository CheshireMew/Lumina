"""Path resolution and directory setup for backend configuration."""

import logging
import os
import sys
import tempfile
from dataclasses import dataclass
from pathlib import Path

logger = logging.getLogger("ConfigPaths")

IS_FROZEN = getattr(sys, "frozen", False)

if IS_FROZEN:
    BASE_DIR = Path(sys._MEIPASS)  # type: ignore[attr-defined]
else:
    BASE_DIR = Path(__file__).resolve().parent.parent

ENV_VAR = os.getenv("LUMINA_ENV", "").lower()
IS_DEV = (not IS_FROZEN) or (ENV_VAR == "dev") or (ENV_VAR == "development")


def resolve_data_root() -> Path:
    env_value = os.environ.get("LUMINA_DATA_PATH")
    if env_value:
        env_path = Path(env_value)
        try:
            env_path.mkdir(parents=True, exist_ok=True)
            logger.info(f"Using LUMINA_DATA_PATH: {env_path}")
            return env_path
        except Exception as exc:
            logger.error(f"Failed to create LUMINA_DATA_PATH: {exc}")

    if IS_FROZEN:
        portable_dir = Path(sys.executable).parent / "Lumina_Data"
    else:
        portable_dir = BASE_DIR.parent / "Lumina_Data"

    if portable_dir.exists():
        logger.info(f"Portable Mode Detected: {portable_dir}")
        return portable_dir

    if not IS_FROZEN:
        try:
            portable_dir.mkdir(parents=True, exist_ok=True)
            logger.info(f"Dev Mode: Auto-created local data dir: {portable_dir}")
            return portable_dir
        except Exception:
            pass

    home = Path.home()
    app_data = home / "AppData" / "Roaming" / "Lumina" if sys.platform == "win32" else home / ".config" / "lumina"

    try:
        app_data.mkdir(parents=True, exist_ok=True)
        return app_data
    except Exception:
        return Path(tempfile.gettempdir()) / "Lumina"


DATA_ROOT = resolve_data_root()
CONFIG_ROOT = DATA_ROOT
MODELS_DIR = BASE_DIR / "models" if IS_FROZEN else BASE_DIR.parent / "models"

(DATA_ROOT / "logs").mkdir(parents=True, exist_ok=True)
(DATA_ROOT / "database").mkdir(parents=True, exist_ok=True)


@dataclass(frozen=True)
class PathsConfig:
    base_dir: Path
    models_dir: Path


def get_model_path(model_name: str) -> Path:
    local_path = CONFIG_ROOT / "models" / model_name
    if local_path.exists():
        return local_path

    models_dir_path = MODELS_DIR / model_name
    if models_dir_path.exists():
        return models_dir_path

    return BASE_DIR / "models" / model_name


def get_paths_config() -> PathsConfig:
    return PathsConfig(BASE_DIR, MODELS_DIR)
