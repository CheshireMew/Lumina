import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).parents[3]
sys.path.append(str(PROJECT_ROOT / "python_backend"))
sys.path.append(str(PROJECT_ROOT))

from config.loader import ConfigBundle
from config.models import WorkerNodeConfig
from core.runtime import (
    resolve_capability_base_url,
    resolve_contract_url,
    resolve_runtime_base_url,
    resolve_runtime_host,
    resolve_runtime_port,
)


def test_runtime_resolution_uses_network_config_methods():
    config = ConfigBundle()

    assert resolve_runtime_host(config, "worker:stt") == "127.0.0.1"
    assert resolve_runtime_port(config, "main") == 8010
    assert resolve_runtime_port(config, "worker:stt") == 8765
    assert resolve_runtime_port(config, "worker:tts") == 8766
    assert resolve_runtime_base_url(config, "worker:stt") == "http://127.0.0.1:8765"


def test_runtime_resolution_uses_worker_node_overrides():
    config = ConfigBundle()
    config.network.workers["worker:search"] = WorkerNodeConfig(
        id="worker:search",
        host="10.0.0.9",
        port=9100,
    )

    assert resolve_runtime_host(config, "worker:search") == "10.0.0.9"
    assert resolve_runtime_port(config, "worker:search") == 9100
    assert resolve_runtime_base_url(config, "worker:search") == "http://10.0.0.9:9100"


def test_contract_url_uses_capability_contract_and_network_config():
    config = ConfigBundle()

    assert resolve_capability_base_url(config, "tts") == "http://127.0.0.1:8766"
    assert resolve_contract_url(config, "tts", "switch") == "http://127.0.0.1:8766/models/switch"
