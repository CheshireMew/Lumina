
from typing import Dict, Any
from core.interfaces.tool import ToolProvider

class WebSearchTool(ToolProvider):
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
            return "Error: No query provided"
            
        # Dynamic Lookup via ServiceContainer
        from services.container import services
        from app_config import config as app_config
        
        provider_id = app_config.search.provider # e.g. "brave" or "duckduckgo"
        provider = services.get_search_provider(provider_id)
        
        if not provider:
             return f"Error: Search provider '{provider_id}' is not active or installed."

        try:
             return await provider.search(query)
        except Exception as e:
             return f"Error executing search with {provider_id}: {e}"
