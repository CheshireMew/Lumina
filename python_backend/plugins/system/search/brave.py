from plugins.base import BaseSystemPlugin
from app_config import config as app_config

class BraveSearchPlugin(BaseSystemPlugin):
    @property
    def id(self) -> str:
        return "brave"

    @property
    def name(self) -> str:
        return "Brave Search"

    @property
    def category(self) -> str:
        return "skill"

    @property
    def description(self) -> str:
        return "Official Brave Search API. Requires API Key."

    @property
    def enabled(self) -> bool:
        return app_config.brave.api_key != ""

    @property
    def config_schema(self):
        return {"type": "string", "key": "BRAVE_API_KEY", "label": "API Key"}

    @property
    def active_in_group(self) -> bool:
        return app_config.search.provider == "brave"

    @property
    def group_id(self) -> str:
        return "search_provider"

    @property
    def func_tag(self) -> str:
        return "Web Search"

    def initialize(self, context):
        try:
            from plugins.skills.brave_search import BraveSearch
            from services.container import services
            
            if self.enabled:
                provider = BraveSearch(app_config.brave.api_key)
                services.register_search_provider(provider)
        except Exception as e:
            print(f"Failed to register Brave Search: {e}")
