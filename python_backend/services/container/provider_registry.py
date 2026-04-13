from typing import Any, Dict, List, Optional


class ProviderRegistry:
    def __init__(self):
        self._context_providers: List[Any] = []
        self._tool_providers: Dict[str, Any] = {}
        self._search_providers: Dict[str, Any] = {}

    def register_context_provider(self, provider: Any):
        self._context_providers.append(provider)

    def get_context_providers(self) -> List[Any]:
        return list(self._context_providers)

    def register_tool_provider(self, provider: Any):
        self._tool_providers[provider.name] = provider

    def get_tool_provider(self, name: str) -> Optional[Any]:
        return self._tool_providers.get(name)

    def get_all_tools(self) -> List[Any]:
        return list(self._tool_providers.values())

    def register_search_provider(self, provider: Any):
        self._search_providers[provider.id] = provider

    def get_search_provider(self, provider_id: str) -> Optional[Any]:
        return self._search_providers.get(provider_id)
