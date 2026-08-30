import sys
from pathlib import Path


PROJECT_ROOT = Path(__file__).parents[3]
sys.path.append(str(PROJECT_ROOT / "python_backend"))

from services.runtime_service import RuntimeService


def test_worker_capability_is_ready_only_when_selected_provider_is_running():
    assert RuntimeService._capability_status(
        True,
        "worker:vision",
        {"computed_status": "running", "error": None},
    ) == "ready"


def test_worker_capability_surfaces_provider_configuration_failure():
    assert RuntimeService._capability_status(
        True,
        "worker:vision",
        {"computed_status": "error", "error": "需要配置模型"},
    ) == "failed"


def test_worker_capability_without_status_report_is_starting_not_ready():
    assert RuntimeService._capability_status(True, "worker:vision", {}) == "starting"
