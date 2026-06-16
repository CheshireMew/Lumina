from typing import Any, Optional, TYPE_CHECKING

from .provider_registry import ProviderRegistry
from .service_definitions import LuminaContainer, ServiceSlot

if TYPE_CHECKING:
    from core.interfaces.services import ILLMManager, IMemoryService, ISTTManager, ITTSManager


class ServiceNotInitializedError(Exception):
    """Raised when accessing a required service that has not been initialized."""


class ServiceContainer:
    _instance: Optional["ServiceContainer"] = None

    def __init__(self):
        self._container = LuminaContainer()
        self._providers = ProviderRegistry()

    def _require(self, provider: ServiceSlot, name: str) -> Any:
        value = provider()
        if value is None:
            raise ServiceNotInitializedError(f"{name} not initialized.")
        return value

    def _value(self, name: str) -> Any:
        return getattr(self._container, name)()

    def _override(self, name: str, instance: Any):
        getattr(self._container, name).override(instance)

    def has_service(self, name: str) -> bool:
        return self._value(name) is not None

    def get_gateway(self) -> Any:
        return self._require(self._container.gateway, "Gateway")

    def get_event_bus(self) -> Any:
        return self._require(self._container.event_bus, "EventBus")

    def get_config(self) -> Any:
        return self._require(self._container.config, "Config")

    def get_memory(self) -> "IMemoryService":
        return self._require(self._container.memory_service, "MemoryService")

    def get_llm_manager(self) -> "ILLMManager":
        return self._require(self._container.llm_manager, "LLMManager")

    def get_tts(self) -> "ITTSManager":
        return self._require(self._container.tts, "TTSManager")

    def get_vision(self) -> Any:
        return self._require(self._container.vision, "VisionManager")

    def get_stt(self) -> "ISTTManager":
        return self._require(self._container.stt, "STTManager")

    def get_plugin_service(self) -> Any:
        return self._require(self._container.plugin_service, "PluginService")

    def get_system_plugin_manager(self) -> Any:
        return self._value("system_plugin_manager")

    def get_character_service(self) -> Any:
        return self._require(self._container.character_service, "CharacterService")

    def get_soul(self) -> Any:
        return self._value("soul")

    def get_mcp_host(self) -> Any:
        return self._value("mcp_host")

    def get_batch_manager(self) -> Any:
        return self._value("batch_manager")

    def get_session_manager(self) -> Any:
        return self._value("session_manager")

    def get_skill_manager(self) -> Any:
        return self._value("skill_manager")

    def get_ticker(self) -> Any:
        return self._value("ticker")

    def get_chat_turn_event_adapter(self) -> Any:
        return self._value("chat_turn_event_adapter")

    def get_chat_pipeline(self) -> Any:
        return self._value("chat_pipeline")

    def get_capability_registry(self) -> Any:
        return self._value("capability_registry")

    def get_plugin_state_aggregator(self) -> Any:
        return self._value("plugin_state_aggregator")

    def get_automation_service(self) -> Any:
        return self._value("automation_service")

    def get_plugin_sync(self) -> Any:
        return self._value("plugin_sync")

    def get_prewarm_task(self) -> Any:
        return self._value("prewarm_task")

    def get_process_manager(self) -> Any:
        return self._value("process_manager")

    def get_capability_package_registry(self) -> Any:
        return self._value("capability_package_registry")

    def get_reconciliation_service(self) -> Any:
        return self._value("reconciliation_service")

    def get_config_watcher(self) -> Any:
        return self._value("config_watcher")

    def get_chat_turn_service(self) -> Any:
        return self._require(self._container.chat_turn_service, "ChatTurnService")

    def set_gateway(self, instance: Any):
        self._override("gateway", instance)

    def set_event_bus(self, instance: Any):
        self._override("event_bus", instance)

    def set_config(self, instance: Any):
        self._override("config", instance)

    def set_memory(self, instance: Any):
        self._override("memory_service", instance)

    def set_llm_manager(self, instance: Any):
        self._override("llm_manager", instance)

    def set_tts(self, instance: Any):
        self._override("tts", instance)

    def set_vision(self, instance: Any):
        self._override("vision", instance)

    def set_stt(self, instance: Any):
        self._override("stt", instance)

    def set_plugin_service(self, instance: Any):
        self._override("plugin_service", instance)

    def set_system_plugin_manager(self, instance: Any):
        self._override("system_plugin_manager", instance)

    def set_character_service(self, instance: Any):
        self._override("character_service", instance)

    def set_soul(self, instance: Any):
        self._override("soul", instance)

    def set_mcp_host(self, instance: Any):
        self._override("mcp_host", instance)

    def set_batch_manager(self, instance: Any):
        self._override("batch_manager", instance)

    def set_session_manager(self, instance: Any):
        self._override("session_manager", instance)

    def set_skill_manager(self, instance: Any):
        self._override("skill_manager", instance)

    def set_ticker(self, instance: Any):
        self._override("ticker", instance)

    def set_process_manager(self, instance: Any):
        self._override("process_manager", instance)

    def set_capability_package_registry(self, instance: Any):
        self._override("capability_package_registry", instance)

    def set_capability_registry(self, instance: Any):
        self._override("capability_registry", instance)

    def set_reconciliation_service(self, instance: Any):
        self._override("reconciliation_service", instance)

    def set_plugin_state_aggregator(self, instance: Any):
        self._override("plugin_state_aggregator", instance)

    def set_config_watcher(self, instance: Any):
        self._override("config_watcher", instance)

    def set_chat_pipeline(self, instance: Any):
        self._override("chat_pipeline", instance)

    def set_chat_turn_service(self, instance: Any):
        self._override("chat_turn_service", instance)

    def set_automation_service(self, instance: Any):
        self._override("automation_service", instance)

    def set_plugin_sync(self, instance: Any):
        self._override("plugin_sync", instance)

    def set_prewarm_task(self, instance: Any):
        self._override("prewarm_task", instance)

    def register_context_provider(self, provider: Any):
        self._providers.register_context_provider(provider)

    def get_context_providers(self):
        return self._providers.get_context_providers()

    def register_tool_provider(self, provider: Any):
        self._providers.register_tool_provider(provider)

    def get_tool_provider(self, name: str):
        return self._providers.get_tool_provider(name)

    def get_all_tools(self):
        return self._providers.get_all_tools()

    def register_search_provider(self, provider: Any):
        self._providers.register_search_provider(provider)

    def get_search_provider(self, provider_id: str):
        return self._providers.get_search_provider(provider_id)

    @classmethod
    def get_instance(cls) -> "ServiceContainer":
        if cls._instance is None:
            cls._instance = ServiceContainer()
        return cls._instance
