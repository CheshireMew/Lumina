from typing import Any, Optional, TYPE_CHECKING

from dependency_injector import providers

from .provider_registry import ProviderRegistry
from .service_definitions import LuminaContainer

if TYPE_CHECKING:
    from core.interfaces.services import ILLMManager, IMemoryService, ISTTManager, ITTSManager


class ServiceNotInitializedError(Exception):
    """Raised when accessing a required service that has not been initialized."""


class ServiceContainer:
    _instance: Optional["ServiceContainer"] = None

    def __init__(self):
        self._container = LuminaContainer()
        self._providers = ProviderRegistry()

    def _require(self, provider: providers.Provider, name: str) -> Any:
        value = provider()
        if value is None:
            raise ServiceNotInitializedError(f"{name} not initialized.")
        return value

    def _value(self, name: str) -> Any:
        return getattr(self._container, name)()

    def _override(self, name: str, instance: Any):
        getattr(self._container, name).override(instance)

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

    def get_character_service(self) -> Any:
        return self._require(self._container.character_service, "CharacterService")

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

    def set_character_service(self, instance: Any):
        self._override("character_service", instance)

    def set_process_manager(self, instance: Any):
        self._override("process_manager", instance)

    def set_capability_package_registry(self, instance: Any):
        self._override("capability_package_registry", instance)

    def set_config_watcher(self, instance: Any):
        self._override("config_watcher", instance)

    def set_chat_pipeline(self, instance: Any):
        self._override("chat_pipeline", instance)

    def set_chat_turn_service(self, instance: Any):
        self._override("chat_turn_service", instance)

    def set_automation_service(self, instance: Any):
        self._override("automation_service", instance)

    def register_tts(self, instance: Any):
        self.set_tts(instance)

    def register_stt(self, instance: Any):
        self.set_stt(instance)

    def register_memory(self, instance: Any):
        self.set_memory(instance)

    def register_vision(self, instance: Any):
        self.set_vision(instance)

    def register_reconciliation_service(self, instance: Any):
        self._override("reconciliation_service", instance)

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

    @property
    def gateway(self):
        return self._value("gateway")

    @gateway.setter
    def gateway(self, value):
        self._override("gateway", value)

    @property
    def event_bus(self):
        return self._value("event_bus")

    @event_bus.setter
    def event_bus(self, value):
        self._override("event_bus", value)

    @property
    def config(self):
        return self._value("config")

    @config.setter
    def config(self, value):
        self._override("config", value)

    @property
    def memory(self):
        return self._value("memory_service")

    @property
    def llm_manager(self):
        return self._value("llm_manager")

    @llm_manager.setter
    def llm_manager(self, value):
        self._override("llm_manager", value)

    @property
    def system_plugin_manager(self):
        return self._value("system_plugin_manager")

    @system_plugin_manager.setter
    def system_plugin_manager(self, value):
        self._override("system_plugin_manager", value)

    @property
    def soul(self):
        return self._value("soul")

    @soul.setter
    def soul(self, value):
        self._override("soul", value)

    @property
    def mcp_host(self):
        return self._value("mcp_host")

    @mcp_host.setter
    def mcp_host(self, value):
        self._override("mcp_host", value)

    @property
    def batch_manager(self):
        return self._value("batch_manager")

    @batch_manager.setter
    def batch_manager(self, value):
        self._override("batch_manager", value)

    @property
    def session_manager(self):
        return self._value("session_manager")

    @session_manager.setter
    def session_manager(self, value):
        self._override("session_manager", value)

    @property
    def skill_manager(self):
        return self._value("skill_manager")

    @skill_manager.setter
    def skill_manager(self, value):
        self._override("skill_manager", value)

    @property
    def ticker(self):
        return self._value("ticker")

    @ticker.setter
    def ticker(self, value):
        self._override("ticker", value)

    @property
    def stt(self):
        return self._value("stt")

    @stt.setter
    def stt(self, value):
        self._override("stt", value)

    @property
    def tts(self):
        return self._value("tts")

    @tts.setter
    def tts(self, value):
        self._override("tts", value)

    @property
    def vision(self):
        return self._value("vision")

    @vision.setter
    def vision(self, value):
        self._override("vision", value)

    @property
    def chat_bridge(self):
        return self._value("chat_bridge")

    @chat_bridge.setter
    def chat_bridge(self, value):
        self._override("chat_bridge", value)

    @property
    def chat_pipeline(self):
        return self._value("chat_pipeline")

    @chat_pipeline.setter
    def chat_pipeline(self, value):
        self._override("chat_pipeline", value)

    @property
    def chat_turn_service(self):
        return self._value("chat_turn_service")

    @chat_turn_service.setter
    def chat_turn_service(self, value):
        self._override("chat_turn_service", value)

    @property
    def capability_registry(self):
        return self._value("capability_registry")

    @capability_registry.setter
    def capability_registry(self, value):
        self._override("capability_registry", value)

    @property
    def capability_package_registry(self):
        return self._value("capability_package_registry")

    @capability_package_registry.setter
    def capability_package_registry(self, value):
        self._override("capability_package_registry", value)

    @property
    def plugin_state_aggregator(self):
        return self._value("plugin_state_aggregator")

    @plugin_state_aggregator.setter
    def plugin_state_aggregator(self, value):
        self._override("plugin_state_aggregator", value)

    @property
    def automation_service(self):
        return self._value("automation_service")

    @automation_service.setter
    def automation_service(self, value):
        self._override("automation_service", value)

    @property
    def plugin_sync(self):
        return self._value("plugin_sync")

    @plugin_sync.setter
    def plugin_sync(self, value):
        self._override("plugin_sync", value)

    @property
    def prewarm_task(self):
        return self._value("prewarm_task")

    @prewarm_task.setter
    def prewarm_task(self, value):
        self._override("prewarm_task", value)

    @property
    def character_service(self):
        return self._value("character_service")

    @character_service.setter
    def character_service(self, value):
        self._override("character_service", value)

    @classmethod
    def get_instance(cls) -> "ServiceContainer":
        if cls._instance is None:
            cls._instance = ServiceContainer()
        return cls._instance
