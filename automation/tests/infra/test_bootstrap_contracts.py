import sys
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock

import pytest

PROJECT_ROOT = Path(__file__).parents[3]
sys.path.append(str(PROJECT_ROOT / "python_backend"))


@pytest.mark.anyio
async def test_provider_config_service_bootstrap_failure_propagates(monkeypatch):
    from core.bootstrap.services import ProviderConfigBootstrapper
    from services.provider_config_service import ProviderConfigService

    class Container:
        def __init__(self):
            self.provider_config_service = None

        def set_provider_config_service(self, provider_config_service):
            self.provider_config_service = provider_config_service

    def fail_init(self, container):
        raise RuntimeError("provider config service init failed")

    monkeypatch.setattr(ProviderConfigService, "__init__", fail_init)

    container = Container()
    with pytest.raises(RuntimeError, match="provider config service init failed"):
        await ProviderConfigBootstrapper().bootstrap(container)

    assert container.provider_config_service is None


@pytest.mark.anyio
async def test_memory_bootstrap_connection_failure_propagates(monkeypatch):
    from core.bootstrap.infrastructure import DatabaseBootstrapper
    from memory.factory import MemoryDriverFactory

    class Container:
        def __init__(self):
            self.memory = None

        def get_config(self):
            return SimpleNamespace(
                get_selected_provider=lambda capability: "driver.memory.test",
                memory=SimpleNamespace(model_dump=lambda: {}),
            )

        def get_worker_runtime_registry(self):
            registry = MagicMock()
            registry.resolve.return_value = None
            return registry

        def set_memory(self, memory_service):
            self.memory = memory_service

    driver = MagicMock()
    driver.connect = AsyncMock(side_effect=RuntimeError("memory connect failed"))
    monkeypatch.setattr(MemoryDriverFactory, "create_driver", MagicMock(return_value=driver))

    container = Container()
    with pytest.raises(RuntimeError, match="memory connect failed"):
        await DatabaseBootstrapper().bootstrap(container)

    assert container.memory is None


@pytest.mark.anyio
async def test_middleware_registers_context_tools_search_and_emotion_broker():
    from core.bootstrap.services import MiddlewareBootstrapper
    from services.chat.emotion_broker import EmotionBroker
    from services.chat.search_providers import BraveSearchProvider, DuckDuckGoSearchProvider
    from services.chat.tools.search import WebSearchTool

    class Container:
        def __init__(self):
            self.search_providers = []
            self.tool_providers = []
            self.emotion_broker = None
            self.config = SimpleNamespace(get_provider_settings=lambda _provider_id: {})
            self.event_bus = MagicMock()
            self.event_bus.subscribe.return_value = 1

        def register_search_provider(self, provider):
            self.search_providers.append(provider)

        def register_tool_provider(self, provider):
            self.tool_providers.append(provider)

        def get_config(self):
            return self.config

        def get_event_bus(self):
            return self.event_bus

        def set_emotion_broker(self, broker):
            self.emotion_broker = broker

    container = Container()

    await MiddlewareBootstrapper().bootstrap(container)

    assert [type(provider) for provider in container.search_providers] == [
        BraveSearchProvider,
        DuckDuckGoSearchProvider,
    ]
    assert [type(provider) for provider in container.tool_providers] == [WebSearchTool]
    assert type(container.emotion_broker) is EmotionBroker
