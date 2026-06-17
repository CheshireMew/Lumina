import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).parents[3]
sys.path.append(str(PROJECT_ROOT / "python_backend"))

from config.loader import ConfigBundle
from llm.manager import LLMManager
from services.config_service import ConfigService


class AppSettingsStub:
    def __init__(self):
        self.bundle = ConfigBundle()
        self.llm = self.bundle.llm
        self.memory = self.bundle.memory
        self.capabilities = self.bundle.capabilities
        self.saved = 0

    def save(self):
        self.saved += 1

    def set_selected_provider(self, capability: str, provider_id: str):
        raise AssertionError(f"Unexpected provider selection write: {capability}={provider_id}")


class ContainerStub:
    def __init__(self, settings: AppSettingsStub, llm_manager: LLMManager):
        self._settings = settings
        self._llm_manager = llm_manager

    def get_config(self):
        return self._settings

    def get_llm_manager(self):
        return self._llm_manager


def build_llm_manager(settings: AppSettingsStub) -> LLMManager:
    llm_manager = LLMManager(settings)
    llm_manager.register_driver_type("openai", lambda provider_id: None)
    return llm_manager


def test_get_llm_runtime_settings_reads_unified_route_and_provider_config():
    settings = AppSettingsStub()
    settings.llm.routes["chat"].provider_id = "custom_provider"
    settings.llm.routes["chat"].model = "chat-model"
    settings.llm.providers["custom_provider"].api_key = "custom-key"
    settings.llm.providers["custom_provider"].base_url = "https://llm.invalid/v1"

    service = ConfigService(ContainerStub(settings, build_llm_manager(settings)))

    runtime = service.get_llm_runtime_settings()

    assert runtime.providerId == "custom_provider"
    assert runtime.apiKey == "custom-key"
    assert runtime.baseUrl == "https://llm.invalid/v1"
    assert runtime.model == "chat-model"


def test_update_llm_runtime_writes_unified_config_without_llm_selected_provider():
    settings = AppSettingsStub()
    service = ConfigService(ContainerStub(settings, build_llm_manager(settings)))

    service.update_llm_runtime(
        api_key="new-key",
        base_url="https://new.invalid/v1",
        model="new-model",
        temperature=0.2,
        top_p=0.8,
        presence_penalty=0.1,
        frequency_penalty=0.3,
        history_limit=12,
        overflow_strategy="reset",
        provider_id="custom_provider",
    )

    custom_provider = settings.llm.providers["custom_provider"]
    assert custom_provider.api_key == "new-key"
    assert custom_provider.base_url == "https://new.invalid/v1"
    assert custom_provider.models == ["new-model"]
    assert "llm" not in settings.capabilities.selected_providers

    for route in settings.llm.routes.values():
        assert route.provider_id == "custom_provider"
        assert route.model == "new-model"
        assert route.temperature == 0.2
        assert route.top_p == 0.8
        assert route.presence_penalty == 0.1
        assert route.frequency_penalty == 0.3

    assert settings.memory.history_limit == 12
    assert settings.memory.overflow_strategy == "reset"
    assert settings.saved > 0
