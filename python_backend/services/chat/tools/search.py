
from typing import Dict, Any, Callable
from core.interfaces.tool import ToolProvider

class WebSearchTool(ToolProvider):
    def __init__(self, config, get_search_provider: Callable[[str], Any]):
        self.config = config
        self.get_search_provider = get_search_provider

    @property
    def name(self) -> str:
        return "web_search"

    def get_definition(self) -> Dict[str, Any]:
        return {
            "type": "function",
            "function": {
                "name": "web_search",
                "description": "Search the internet for up-to-date information.",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "query": {"type": "string", "description": "Search query"}
                    },
                    "required": ["query"]
                }
            }
        }

    async def execute(self, args: Dict[str, Any]) -> str:
        query = args.get("query", "")
        if not query:
            raise ValueError("web_search requires query")

        provider_id = self.config.get_selected_provider("tool.search")
        if not provider_id:
            raise ValueError("tool.search provider must be configured")

        provider = self.get_search_provider(provider_id)
        if not provider or not hasattr(provider, "search"):
            raise RuntimeError(f"Search provider '{provider_id}' is not active")

        return await provider.search(query)
