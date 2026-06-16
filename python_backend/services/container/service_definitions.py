from typing import Any


SERVICE_NAMES = (
    "config",
    "event_bus",
    "gateway",
    "memory_service",
    "llm_manager",
    "system_plugin_manager",
    "process_manager",
    "reconciliation_service",
    "capability_registry",
    "capability_package_registry",
    "plugin_state_aggregator",
    "automation_service",
    "soul",
    "mcp_host",
    "batch_manager",
    "session_manager",
    "skill_manager",
    "chat_pipeline",
    "chat_turn_service",
    "chat_turn_event_adapter",
    "tts",
    "stt",
    "vision",
    "ticker",
    "config_watcher",
    "prewarm_task",
    "plugin_service",
    "plugin_sync",
    "character_service",
)


class ServiceSlot:
    def __init__(self, value: Any = None):
        self._value = value

    def __call__(self) -> Any:
        return self._value

    def override(self, value: Any) -> None:
        self._value = value


class LuminaContainer:
    def __init__(self):
        for name in SERVICE_NAMES:
            setattr(self, name, ServiceSlot())
