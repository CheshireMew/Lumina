from plugins.base import BaseSystemPlugin
from app_config import config as app_config

class DisabledSearchPlugin(BaseSystemPlugin):
    @property
    def id(self) -> str:
        return "none"

    @property
    def name(self) -> str:
        return "Disabled"

    @property
    def category(self) -> str:
        return "skill"

    @property
    def description(self) -> str:
        return "Disable Web Search completely."

    @property
    def enabled(self) -> bool:
        return True

    @property
    def config_schema(self):
        return None

    @property
    def active_in_group(self) -> bool:
        return app_config.search.provider == "none" or not app_config.search.provider

    @property
    def group_id(self) -> str:
        return "search_provider"

    @property
    def func_tag(self) -> str:
        return "Web Search"

    def initialize(self, context):
        pass
