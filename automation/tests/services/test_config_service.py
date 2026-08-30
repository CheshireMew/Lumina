import sys
from pathlib import Path

import pytest

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

    def replace_sections(self, *, persist=True, **sections):
        for name, value in sections.items():
            setattr(self.bundle, name, value)
            setattr(self, name, value)
        if persist:
            self.saved += 1

    def set_selected_provider(self, capability: str, provider_id: str):
        raise AssertionError(f"Unexpected provider selection write: {capability}={provider_id}")


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

    service = ConfigService(settings, build_llm_manager(settings))

    runtime = service.get_llm_runtime_settings()

    assert runtime.providerId == "custom_provider"
    assert runtime.apiKey == "custom-key"
    assert runtime.baseUrl == "https://llm.invalid/v1"
    assert runtime.model == "chat-model"


def test_pollinations_runtime_reports_effective_history_limit():
    settings = AppSettingsStub()
    settings.memory.history_limit = 20
    service = ConfigService(settings, build_llm_manager(settings))

    runtime = service.get_llm_runtime_settings()

    assert runtime.providerId == "free_tier"
    assert runtime.historyLimit == 5


def test_update_llm_runtime_writes_provider_route_and_selection_atomically():
    settings = AppSettingsStub()
    service = ConfigService(settings, build_llm_manager(settings))

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
    assert settings.capabilities.selected_providers["llm"] == "custom_provider"

    chat_route = settings.llm.routes["chat"]
    assert chat_route.provider_id == "custom_provider"
    assert chat_route.model == "new-model"
    assert chat_route.temperature == 0.2
    assert chat_route.top_p == 0.8
    assert chat_route.presence_penalty == 0.1
    assert chat_route.frequency_penalty == 0.3

    for feature, route in settings.llm.routes.items():
        if feature == "chat":
            continue
        assert route.provider_id == "free_tier"
        assert route.model == "openai"

    assert settings.memory.history_limit == 12
    assert settings.memory.overflow_strategy == "reset"
    assert settings.saved == 1


def test_pollinations_runtime_saves_credentials_and_clamps_history():
    settings = AppSettingsStub()
    service = ConfigService(settings, build_llm_manager(settings))

    service.update_llm_runtime(
        api_key="pollinations-key",
        base_url="https://custom.invalid/v1",
        model="openai",
        history_limit=20,
        provider_id="free_tier",
    )

    free_provider = settings.llm.providers["free_tier"]
    assert free_provider.api_key == "pollinations-key"
    assert free_provider.base_url == "https://gen.pollinations.ai/v1"
    assert settings.memory.history_limit == 5


def test_pollinations_runtime_requires_api_key():
    settings = AppSettingsStub()
    service = ConfigService(settings, build_llm_manager(settings))

    with pytest.raises(ValueError, match="Pollinations"):
        service.update_llm_runtime(
            api_key="",
            base_url="",
            model="openai",
            provider_id="free_tier",
        )


def test_remote_custom_llm_requires_api_key():
    settings = AppSettingsStub()
    service = ConfigService(settings, build_llm_manager(settings))

    with pytest.raises(ValueError, match="API 密钥"):
        service.update_llm_runtime(
            api_key="",
            base_url="https://custom.invalid/v1",
            model="custom-model",
            provider_id="custom_provider",
        )
