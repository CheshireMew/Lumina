from pathlib import Path
import sys

import pytest

PROJECT_ROOT = Path(__file__).parents[3]
sys.path.append(str(PROJECT_ROOT / "python_backend"))
sys.path.append(str(PROJECT_ROOT))

from core.interfaces.module import CapabilityModule
from core.manifest import CapabilityManifest
from services.capability_kernel.loader import CapabilityModuleLoader


def make_manifest(module_dir: Path, module_id: str = "test.module") -> CapabilityManifest:
    return CapabilityManifest(
        id=module_id,
        api_version="1.0",
        kind="extension",
        capability="chat.post_processor",
        runtime_target="main",
        path=str(module_dir),
    )


def test_capability_loader_instantiates_module(tmp_path):
    (tmp_path / "module.py").write_text(
        """
from core.interfaces.module import CapabilityModule

class Capability(CapabilityModule):
    pass
""",
        encoding="utf-8",
    )

    capability = CapabilityModuleLoader().instantiate(make_manifest(tmp_path))

    assert isinstance(capability, CapabilityModule)
    assert capability.id == "test.module"


def test_capability_loader_supports_relative_imports(tmp_path):
    (tmp_path / "helper.py").write_text('MODULE_NAME = "Relative Module"\n', encoding="utf-8")
    (tmp_path / "module.py").write_text(
        """
from core.interfaces.module import CapabilityModule
from .helper import MODULE_NAME

class Capability(CapabilityModule):
    def get_metadata(self):
        data = super().get_metadata()
        data["name"] = MODULE_NAME
        return data
""",
        encoding="utf-8",
    )

    capability = CapabilityModuleLoader().instantiate(make_manifest(tmp_path, "test.relative"))

    assert capability.get_metadata()["name"] == "Relative Module"


def test_capability_loader_requires_module_file(tmp_path):
    with pytest.raises(FileNotFoundError, match="module.py not found"):
        CapabilityModuleLoader().instantiate(make_manifest(tmp_path))


def test_capability_loader_requires_capability_export(tmp_path):
    (tmp_path / "module.py").write_text("class NotCapability:\n    pass\n", encoding="utf-8")

    with pytest.raises(TypeError, match="must export class Capability"):
        CapabilityModuleLoader().instantiate(make_manifest(tmp_path))


def test_capability_loader_surfaces_syntax_errors(tmp_path):
    (tmp_path / "module.py").write_text("class Capability(\n", encoding="utf-8")

    with pytest.raises(SyntaxError):
        CapabilityModuleLoader().instantiate(make_manifest(tmp_path))
