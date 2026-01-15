from typing import Dict, Any, Optional
from datetime import datetime
import logging

logger = logging.getLogger("Ticker")

class HeartbeatContext:
    def __init__(self, soul, dreaming):
        self.soul = soul
        self.dreaming = dreaming
        # Helper to get last interaction time smoothly
        self.last_interaction: datetime = soul.last_interaction

class BaseTicker:
    def __init__(self, id: str, name: str, interval: float = 1.0):
        self.id = id
        self.name = name
        self.interval = interval # Minimal check interval in seconds
        self.enabled = False
        self.config: Dict[str, Any] = {}
        self._last_tick = datetime.fromtimestamp(0)

    def load_config(self, config: Dict[str, Any]):
        self.config.update(config)
        self.enabled = self.config.get("enabled", False)

    def get_config_schema(self) -> Optional[Dict]:
        return None

    def should_tick(self, now: datetime) -> bool:
        if not self.enabled: return False
        return (now - self._last_tick).total_seconds() >= self.interval

    def tick(self, now: datetime, context: HeartbeatContext):
        self._last_tick = now
        try:
            self.on_tick(now, context)
        except Exception as e:
            logger.error(f"Ticker {self.id} failed: {e}")

    def on_tick(self, now: datetime, context: HeartbeatContext):
        """Override this"""
        pass

    def start(self):
        self.enabled = True
        self.config["enabled"] = True
        logger.info(f"Ticker Started: {self.name}")

    def stop(self):
        self.enabled = False
        self.config["enabled"] = False
        logger.info(f"Ticker Stopped: {self.name}")
