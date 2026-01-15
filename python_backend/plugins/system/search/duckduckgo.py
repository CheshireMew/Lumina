from plugins.base import BaseSystemPlugin
from app_config import config as app_config

class DuckDuckGoPlugin(BaseSystemPlugin):
    @property
    def id(self) -> str:
        return "duckduckgo"

    @property
    def name(self) -> str:
        return "DuckDuckGo"

    @property
    def category(self) -> str:
        return "skill"

    @property
    def description(self) -> str:
        return "Free, no-key search provider. Uses duckduckgo-search."

    @property
    def enabled(self) -> bool:
        return True

    @property
    def config_schema(self):
        return None

    @property
    def active_in_group(self) -> bool:
        return app_config.search.provider == "duckduckgo"

    @property
    def group_id(self) -> str:
        return "search_provider"

    @property
    def func_tag(self) -> str:
        return "Web Search"

    def initialize(self, context):
        try:
            from plugins.skills.ddg_search import DuckDuckGoSearch
            from services.container import services
            
            provider = DuckDuckGoSearch()
            services.register_search_provider(provider)
        except Exception as e:
            print(f"Failed to register DDG: {e}")
