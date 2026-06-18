from __future__ import annotations

import time
from typing import Any, Dict, Optional


class ProviderHostManager:
    def __init__(self, config: Any, capability: str):
        self.config = config
        self.capability = capability
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

    def register_driver(self, driver: Any) -> None:
        self.drivers[driver.id] = driver

    def unregister_driver(self, driver_id: str) -> Any:
        return self.drivers.pop(driver_id, None)

    def has_driver(self, driver_id: str) -> bool:
        return driver_id in self.drivers

    def get_driver(self, driver_id: str) -> Any | None:
        return self.drivers.get(driver_id)

    def is_driver_active(self, driver_id: str) -> bool:
        return self.active_driver_id == driver_id and self.active_driver is not None

    def require_driver(self, driver_id: str) -> Any:
        driver = self.get_driver(driver_id)
        if driver is None:
            raise ValueError(f"Unknown {self.capability.upper()} provider: {driver_id}")
        return driver

    def resolve_startup_driver_id(self) -> str | None:
        if not self.drivers:
            self.mark_error(f"No {self.capability.upper()} drivers available")
            self.active_driver_id = "none"
            return None

        target_id = self.config.get_selected_provider(self.capability)
        if not target_id:
            self.mark_error(f"No {self.capability.upper()} provider selected in configuration")
            self.active_driver_id = "none"
            return None

        if target_id not in self.drivers:
            self.mark_error(f"Configured {self.capability.upper()} provider not discovered: {target_id}")
            self.active_driver_id = "none"
            return None

        return target_id

    def iter_drivers(self) -> tuple[tuple[str, Any], ...]:
        return tuple(self.drivers.items())

    def update_driver_config(self, driver_id: str, key: str, value: Any) -> dict[str, Any]:
        driver = self.require_driver(driver_id)
        driver.config[key] = value
        return dict(driver.config)

    def get_driver_config(self, driver_id: str) -> dict[str, Any]:
        return dict(self.require_driver(driver_id).config)

    def get_driver_metadata(self, driver_id: str) -> dict[str, Any]:
        driver = self.require_driver(driver_id)
        return {
            "id": driver.id,
            "name": driver.name,
            "description": driver.description,
            "config_schema": driver.config_schema,
        }

    def snapshot_provider_state(self, provider_id: str) -> dict[str, Any]:
        driver = self.require_driver(provider_id)
        is_active = self.is_driver_active(provider_id)
        active_status = "stopped"
        if is_active:
            active_status = "ready" if self.loading_status == "idle" else self.loading_status
        desired_enabled = bool(self.config.is_provider_desired_enabled(provider_id))
        return {
            "id": provider_id,
            "name": driver.name,
            "description": driver.description,
            "kind": "provider",
            "enabled": desired_enabled,
            "desired_enabled": desired_enabled,
            "active": is_active and active_status in {"ready", "idle", "running"},
            "active_status": active_status,
            "active_in_group": is_active,
            "group_policy": "exclusive",
            "config_schema": driver.config_schema,
            "current_config": self.config.get_provider_settings(provider_id),
            "is_driver": True,
            "driver_id": provider_id,
            "error": self.last_error if provider_id == self.active_driver_id else None,
            "load_time_ms": self.last_load_duration_ms if provider_id == self.active_driver_id else None,
        }
