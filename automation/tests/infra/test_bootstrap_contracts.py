import sys
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock

import pytest

PROJECT_ROOT = Path(__file__).parents[3]
sys.path.append(str(PROJECT_ROOT / "python_backend"))


@pytest.mark.anyio
async def test_provider_config_service_bootstrap_failure_propagates(monkeypatch):
    from core.bootstrap.services import ProviderConfigServicesBootstrapper
    from services.provider_config_service import ProviderConfigService

    class Container:
        def __init__(self):
            self.provider_config_service = None

        def set_provider_config_service(self, provider_config_service):
            self.provider_config_service = provider_config_service

    def fail_init(self, container):
        raise RuntimeError("plugin service init failed")

    monkeypatch.setattr(ProviderConfigService, "__init__", fail_init)

    container = Container()
    with pytest.raises(RuntimeError, match="plugin service init failed"):
        await ProviderConfigServicesBootstrapper().bootstrap(container)

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

        def get_capability_package_registry(self):
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
async def test_middleware_registers_only_rag_context_provider():
    from core.bootstrap.services import MiddlewareBootstrapper
    from services.chat.providers import RAGContextProvider
    from services.chat.tools.search import WebSearchTool

    class Container:
        def __init__(self):
            self.context_providers = []
            self.tool_providers = []

        def register_context_provider(self, provider):
            self.context_providers.append(provider)

        def register_tool_provider(self, provider):
            self.tool_providers.append(provider)

    container = Container()

    await MiddlewareBootstrapper().bootstrap(container)

    assert [type(provider) for provider in container.context_providers] == [RAGContextProvider]
    assert [type(provider) for provider in container.tool_providers] == [WebSearchTool]
