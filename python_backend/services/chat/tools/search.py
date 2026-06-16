
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
            return "Error: No query provided"

        from app_config import config as app_config
        spm = self.services.get_system_plugin_manager()

        provider_id = app_config.get_selected_provider("tool.search")
        if spm and not provider_id:
            provider_id = spm.find_provider("tool.search")

        if not spm or not provider_id:
            return "Error: No search provider is configured."

        provider = spm.get_plugin(provider_id)
        if not provider or not hasattr(provider, "search"):
            return f"Error: Search provider '{provider_id}' is not active or installed."

        try:
             return await provider.search(query)
        except Exception as e:
             return f"Error executing search with {provider_id}: {e}"
