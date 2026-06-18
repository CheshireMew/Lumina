
from typing import Dict, Any
from core.interfaces.tool import ToolProvider

class WebSearchTool(ToolProvider):
    def __init__(self, services_container):
        self.services = services_container

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

        provider_id = self.services.get_config().get_selected_provider("tool.search")
        if not provider_id:
            raise ValueError("tool.search provider must be configured")

        provider = self.services.get_search_provider(provider_id)
        if not provider or not hasattr(provider, "search"):
            raise RuntimeError(f"Search provider '{provider_id}' is not active")

        return await provider.search(query)
