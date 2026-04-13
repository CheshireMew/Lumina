import json
import logging
from pathlib import Path
from typing import Any, Dict, Optional

from app_config import CONFIG_ROOT

logger = logging.getLogger(__name__)


DEFAULT_AUDIO_CONFIG_PATH = CONFIG_ROOT / "audio_config.json"


class AudioConfigStore:
    def __init__(self, config_path: Optional[Path] = None):
        self.config_path = config_path or DEFAULT_AUDIO_CONFIG_PATH

    def load(self) -> Dict[str, Any]:
        if not self.config_path.exists():
            return {}

        try:
            with open(self.config_path, "r", encoding="utf-8") as f:
                data = json.load(f)
                return data if isinstance(data, dict) else {}
        except Exception as e:
            logger.error(f"Failed to load audio config: {e}")
            return {}

    def save(self, updates: Dict[str, Any]) -> None:
        config = self.load()
        config.update(updates)

        try:
            self.config_path.parent.mkdir(parents=True, exist_ok=True)
            with open(self.config_path, "w", encoding="utf-8") as f:
                json.dump(config, f, ensure_ascii=False, indent=2)
            logger.info("Audio config saved.")
        except Exception as e:
            logger.error(f"Config save failed: {e}")
