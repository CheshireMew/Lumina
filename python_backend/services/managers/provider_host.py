from __future__ import annotations

import time
from typing import Any, Dict, Optional


class ProviderHostManager:
    def __init__(self, config: Any, capability: str, default_driver_id: str):
        self.config = config
        self.capability = capability
        self.default_driver_id: str = default_driver_id
        self.drivers: Dict[str, Any] = {}
        self.active_driver_id: str = "none"
        self.active_driver: Optional[Any] = None
        self.loading_status: str = "idle"
        self.last_error: Optional[str] = None
        self.last_load_duration_ms: Optional[int] = None
        self.last_transition_started_at: Optional[float] = None

    def begin_transition(self, target_id: str):
        self.active_driver_id = target_id
        self.loading_status = "loading"
        self.last_error = None
        self.last_transition_started_at = time.perf_counter()

    def mark_ready(self, driver: Any, driver_id: str):
        self.active_driver = driver
        self.active_driver_id = driver_id
        self.loading_status = "idle"
        if self.last_transition_started_at is not None:
            self.last_load_duration_ms = int((time.perf_counter() - self.last_transition_started_at) * 1000)
        self.last_transition_started_at = None

    def mark_unloaded(self):
        self.active_driver = None
        self.active_driver_id = "none"
        self.loading_status = "idle"
        self.last_transition_started_at = None

    def mark_error(self, message: str):
        self.last_error = message
        self.active_driver = None
        self.loading_status = "idle"
        if self.last_transition_started_at is not None:
            self.last_load_duration_ms = int((time.perf_counter() - self.last_transition_started_at) * 1000)
        self.last_transition_started_at = None

    def snapshot_provider_state(self, provider_id: str) -> dict[str, Any]:
        driver = self.drivers.get(provider_id)
        is_active = provider_id == self.active_driver_id and self.active_driver is not None
        return {
            "id": provider_id,
            "name": getattr(driver, "name", provider_id),
            "description": getattr(driver, "description", ""),
            "enabled": is_active,
            "active_status": "ready" if is_active else "stopped",
            "active_in_group": is_active,
            "driver_id": provider_id,
            "error": self.last_error if provider_id == self.active_driver_id else None,
            "load_time_ms": self.last_load_duration_ms if provider_id == self.active_driver_id else None,
        }
