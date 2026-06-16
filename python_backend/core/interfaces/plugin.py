from abc import ABC
from typing import Any

from core.api_version import PLUGIN_API_VERSION


class Plugin(ABC):
    """
    Unified plugin contract.

    Lifecycle:
    - load(context)
    - enable()
    - disable()
    - unload()
    - health()
    - get_metadata()
    """

    API_VERSION = PLUGIN_API_VERSION

    def __init__(self):
        self._context = None
        self._manifest = None
        self._enabled = False

    @property
    def id(self) -> str:
        if not self._manifest:
            raise RuntimeError("Plugin manifest was not injected.")
        return self._manifest.id

    @property
    def context(self):
        if self._context is None:
            raise RuntimeError(f"Plugin {self.__class__.__name__} has not been loaded.")
        return self._context

    @property
    def manifest(self):
        return self._manifest

    @property
    def enabled(self) -> bool:
        return self._enabled

    @property
    def config(self) -> dict[str, Any]:
        if self._context is None:
            return {}
        return self.context.get_config()

    def _bind_manifest(self, manifest):
        self._manifest = manifest

    async def load(self, context):
        self._context = context

    async def enable(self):
        self._enabled = True

    async def disable(self):
        self._enabled = False

    async def unload(self):
        self._context = None

    async def health(self) -> dict[str, Any]:
        return {"status": "ready" if self._enabled else "disabled"}

    def get_metadata(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "name": self.id,
            "description": "",
            "kind": getattr(self._manifest, "kind", "extension"),
            "capability": getattr(self._manifest, "capability", "system"),
            "runtime_target": getattr(self._manifest, "runtime_target", "main"),
            "permissions": list(getattr(self._manifest, "permissions", []) or []),
            "config_schema": dict(getattr(self._manifest, "config_schema", {}) or {}),
            "provides": list(getattr(self._manifest, "provides", []) or []),
        }

    def load_data(self) -> dict[str, Any]:
        return self.context.load_data()

    def save_data(self, data: dict[str, Any]):
        self.context.save_data(data)

    def get_data_dir(self):
        return self.context.get_data_dir()

    def update_config(self, key: str, value: Any):
        self.context.update_config(key, value)

