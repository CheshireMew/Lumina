from config.loader import ConfigBundle
from core.runtime import (
    get_capability_contract,
    list_capability_names,
    port_key_for_runtime_target,
    resolve_runtime_port,
)
from core.worker_runtimes import WorkerRuntimeRegistry


def test_runtime_catalog_owns_all_public_capabilities():
    assert list_capability_names() == (
        "stt",
        "tts",
        "voiceprint",
        "vision",
        "llm",
        "memory",
    )


def test_runtime_catalog_cross_references_worker_definitions():
    registry = WorkerRuntimeRegistry()
    for capability in list_capability_names():
        contract = get_capability_contract(capability)
        assert contract is not None
        if not contract.runtime_id:
            continue
        definition = registry.get_definition(contract.runtime_id)
        assert definition is not None
        assert capability in definition.capabilities


def test_runtime_ports_are_derived_from_catalog_port_keys():
    config = ConfigBundle()
    assert port_key_for_runtime_target("worker:stt") == "stt_port"
    assert resolve_runtime_port(config, "worker:stt") == config.network.stt_port
    assert resolve_runtime_port(config, "main") == config.network.core_port
