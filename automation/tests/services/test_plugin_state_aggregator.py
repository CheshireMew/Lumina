import pytest

from services.plugin_state_aggregator import PluginStateAggregator

pytestmark = pytest.mark.anyio


async def test_aggregator_does_not_infer_desired_state_from_enabled():
    aggregator = PluginStateAggregator()

    await aggregator._merge_state(
        "plugin.legacy",
        {
            "id": "plugin.legacy",
            "enabled": True,
            "active_status": "ready",
        },
        source="worker",
    )

    state = aggregator.get_plugin("plugin.legacy")
    assert state["enabled"] is False
    assert state["active"] is True
    assert state["computed_status"] == "stopping"


async def test_aggregator_uses_desired_enabled_as_intent_source():
    aggregator = PluginStateAggregator()

    await aggregator._merge_state(
        "plugin.current",
        {
            "id": "plugin.current",
            "desired_enabled": True,
            "active_status": "ready",
        },
        source="worker",
    )

    state = aggregator.get_plugin("plugin.current")
    assert state["enabled"] is True
    assert state["active"] is True
    assert state["computed_status"] == "running"
