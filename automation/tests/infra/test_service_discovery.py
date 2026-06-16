import sys
from pathlib import Path

import pytest

PROJECT_ROOT = Path(__file__).parents[3]
sys.path.append(str(PROJECT_ROOT / "python_backend"))

from services.infra.service_discovery import ServiceDiscovery


def test_service_discovery_returns_registered_worker_url():
    discovery = ServiceDiscovery()
    discovery.register(
        worker_id="stt-worker",
        host="10.0.0.5",
        port=8765,
        capabilities=["stt"],
        runtime_target="worker:stt",
    )

    assert discovery.get_url("stt-worker") == "http://10.0.0.5:8765"
    assert discovery.get_url("worker:stt") == "http://10.0.0.5:8765"


def test_service_discovery_does_not_fallback_to_configured_worker_url():
    discovery = ServiceDiscovery()

    with pytest.raises(ValueError, match="not registered in service discovery"):
        discovery.get_url("worker:stt")


def test_service_discovery_prunes_stale_workers():
    discovery = ServiceDiscovery()
    discovery.ttl = -1
    discovery.register(
        worker_id="stale-worker",
        host="127.0.0.1",
        port=8765,
        capabilities=["stt"],
        runtime_target="worker:stt",
    )

    assert discovery.get_node("stale-worker") is None

    with pytest.raises(ValueError, match="not registered in service discovery"):
        discovery.get_url("worker:stt")
