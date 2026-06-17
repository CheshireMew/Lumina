from typing import Any


SERVICE_NAMES = (
    "config",
    "event_bus",
    "gateway",
    "memory_service",
    "llm_manager",
    "capability_module_manager",
    "process_manager",
    "capability_registry",
    "capability_package_registry",
    "automation_service",
    "soul",
    "mcp_host",
    "session_manager",
    "skill_manager",
    "chat_pipeline",
    "chat_turn_service",
    "companion_runtime",
    "companion_context_resolver",
    "companion_interaction_recorder",
    "chat_turn_event_adapter",
    "tts",
    "stt",
    "vision",
    "ticker",
    "config_watcher",
    "prewarm_task",
    "provider_config_service",
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
