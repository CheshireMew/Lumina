from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock

import pytest

from services.chat.tools.search import WebSearchTool

pytestmark = pytest.mark.anyio


class ServicesStub:
    def __init__(self, *, provider_id="provider.search.test", provider=None):
        self.config = SimpleNamespace(
            get_selected_provider=MagicMock(return_value=provider_id),
        )
        self.provider = provider

    def get_search_provider(self, provider_id: str):
        return self.provider


async def test_web_search_requires_query():
    services = ServicesStub()
    tool = WebSearchTool(services.config, services.get_search_provider)

    with pytest.raises(ValueError, match="web_search requires query"):
        await tool.execute({})


async def test_web_search_requires_configured_provider():
    services = ServicesStub(provider_id=None)
    tool = WebSearchTool(services.config, services.get_search_provider)

    with pytest.raises(ValueError, match="tool.search provider must be configured"):
        await tool.execute({"query": "hello"})

async def test_web_search_requires_active_provider():
    services = ServicesStub(provider_id="provider.search.test", provider=None)
    tool = WebSearchTool(services.config, services.get_search_provider)

    with pytest.raises(RuntimeError, match="Search provider 'provider.search.test' is not active"):
        await tool.execute({"query": "hello"})


async def test_web_search_provider_failure_propagates():
    provider = SimpleNamespace(search=AsyncMock(side_effect=RuntimeError("search failed")))
    services = ServicesStub(provider_id="provider.search.test", provider=provider)
    tool = WebSearchTool(services.config, services.get_search_provider)

    with pytest.raises(RuntimeError, match="search failed"):
        await tool.execute({"query": "hello"})


async def test_web_search_returns_provider_result():
    provider = SimpleNamespace(search=AsyncMock(return_value="search result"))
    services = ServicesStub(provider_id="provider.search.test", provider=provider)
    tool = WebSearchTool(services.config, services.get_search_provider)

    result = await tool.execute({"query": "hello"})

    assert result == "search result"
    provider.search.assert_awaited_once_with("hello")
