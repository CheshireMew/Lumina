import sys
from pathlib import Path

import pytest

PROJECT_ROOT = Path(__file__).parents[3]
sys.path.append(str(PROJECT_ROOT / "python_backend"))
sys.path.append(str(PROJECT_ROOT))

from config.loader import ConfigBundle
from core.api.context import LuminaContext
from core.events.bus import EventBus
from core.interfaces.module import CapabilityModule
from core.manifest import CapabilityManifest
from services.capability_registry import CapabilityRegistry
from services.capability_kernel.context_binder import CapabilityContextBinder


class ContainerStub:
    def __init__(self):
        self.config = ConfigBundle()
        self.event_bus = EventBus()

    def get_config(self):
        return self.config

    def get_event_bus(self):
        return self.event_bus


def build_manifest() -> CapabilityManifest:
    return CapabilityManifest(id="test.module", capability="tool.search")


def test_lumina_context_requires_complete_runtime_dependencies():
    manifest = build_manifest()
    event_bus = EventBus()
    capability_registry = CapabilityRegistry()

    with pytest.raises(ValueError, match="ServiceContainer"):
        LuminaContext(None, "test.module", manifest, event_bus, capability_registry)

    with pytest.raises(ValueError, match="EventBus"):
        LuminaContext(ContainerStub(), "test.module", manifest, None, capability_registry)

    with pytest.raises(ValueError, match="CapabilityRegistry"):
        LuminaContext(ContainerStub(), "test.module", manifest, event_bus, None)


def test_lumina_context_exposes_config_and_capability_registry():
    container = ContainerStub()
    capability_registry = CapabilityRegistry()
    capability_registry.register_module(
        module_id="provider.search.test",
        capabilities=["tool.search"],
        runtime_target="main",
        kind="provider",
        enabled=True,
    )

    context = LuminaContext(
        container,
        "test.module",
        build_manifest(),
        container.get_event_bus(),
        capability_registry,
    )

    assert context.config is not None
    assert context.find_capability("tool.search") == "provider.search.test"


@pytest.mark.anyio
async def test_capability_context_binder_uses_required_container_services():
    container = ContainerStub()
    capability_registry = CapabilityRegistry()
    capability = CapabilityModule()

    await CapabilityContextBinder(container, capability_registry).bind(capability, build_manifest())

    assert capability.context.events is container.event_bus
    assert capability.context.config is not None


def test_capability_context_binder_requires_core_dependencies():
    capability_registry = CapabilityRegistry()

    with pytest.raises(ValueError, match="ServiceContainer"):
        CapabilityContextBinder(None, capability_registry)

    with pytest.raises(ValueError, match="CapabilityRegistry"):
        CapabilityContextBinder(ContainerStub(), None)
