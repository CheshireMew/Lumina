from pathlib import Path
import sys

import pytest

PROJECT_ROOT = Path(__file__).parents[3]
sys.path.append(str(PROJECT_ROOT / "python_backend"))
sys.path.append(str(PROJECT_ROOT))

from core.interfaces.plugin import Plugin as BasePlugin
from core.manifest import PluginManifest
from services.plugin_kernel.loader import PluginLoader


def make_manifest(plugin_dir: Path, plugin_id: str = "test.plugin") -> PluginManifest:
    return PluginManifest(
        id=plugin_id,
        api_version="1.0",
        kind="extension",
        capability="chat.post_processor",
        runtime_target="main",
        permissions=[],
        path=str(plugin_dir),
    )


def test_plugin_loader_instantiates_plugin(tmp_path):
    (tmp_path / "plugin.py").write_text(
        """
from core.interfaces.plugin import Plugin as BasePlugin

class Plugin(BasePlugin):
    pass
""",
        encoding="utf-8",
    )

    plugin = PluginLoader().instantiate(make_manifest(tmp_path))

    assert isinstance(plugin, BasePlugin)
    assert plugin.id == "test.plugin"


def test_plugin_loader_supports_relative_imports(tmp_path):
    (tmp_path / "helper.py").write_text('PLUGIN_NAME = "Relative Plugin"\n', encoding="utf-8")
    (tmp_path / "plugin.py").write_text(
        """
from core.interfaces.plugin import Plugin as BasePlugin
from .helper import PLUGIN_NAME

class Plugin(BasePlugin):
    def get_metadata(self):
        data = super().get_metadata()
        data["name"] = PLUGIN_NAME
        return data
""",
        encoding="utf-8",
    )

    plugin = PluginLoader().instantiate(make_manifest(tmp_path, "test.relative"))

    assert plugin.get_metadata()["name"] == "Relative Plugin"


def test_plugin_loader_requires_plugin_file(tmp_path):
    with pytest.raises(FileNotFoundError, match="plugin.py not found"):
        PluginLoader().instantiate(make_manifest(tmp_path))


def test_plugin_loader_requires_plugin_export(tmp_path):
    (tmp_path / "plugin.py").write_text("class NotPlugin:\n    pass\n", encoding="utf-8")

    with pytest.raises(TypeError, match="must export class Plugin"):
        PluginLoader().instantiate(make_manifest(tmp_path))


def test_plugin_loader_surfaces_syntax_errors(tmp_path):
    (tmp_path / "plugin.py").write_text("class Plugin(\n", encoding="utf-8")

    with pytest.raises(SyntaxError):
        PluginLoader().instantiate(make_manifest(tmp_path))
