import inspect
from pathlib import Path

import services.container as container_module

from capabilities.stt import routes as worker_stt_routes
from capabilities.tts import routes as worker_tts_routes
from routers import stt_routes as proxy_stt_routes
from routers import tts_routes as proxy_tts_routes
from services.chat.pipeline import ChatPipeline
from services.chat.tools.search import WebSearchTool
from services.config_service import ConfigService
from services.provider_config_service import ProviderConfigService
from services.runtime_service import RuntimeService


PROJECT_ROOT = Path(__file__).resolve().parents[3]


def test_business_services_receive_explicit_dependencies():
    for service_type in (
        ConfigService,
        ProviderConfigService,
        RuntimeService,
        ChatPipeline,
        WebSearchTool,
    ):
        parameters = inspect.signature(service_type.__init__).parameters
        assert "container" not in parameters
        assert "services_container" not in parameters


def test_legacy_global_service_locator_cannot_return():
    assert not hasattr(container_module, "services")

    legacy_import = "from services.container import services"
    offenders = [
        path.relative_to(PROJECT_ROOT).as_posix()
        for path in (PROJECT_ROOT / "python_backend").rglob("*.py")
        if legacy_import in path.read_text(encoding="utf-8")
    ]
    assert offenders == []


def test_business_services_do_not_reach_into_dependency_private_state():
    forbidden_access = {
        "python_backend/services/config_service.py": ("llm_manager._",),
        "python_backend/services/provider_config_service.py": (
            "process_manager._",
            "worker_control_hub._",
            "config_service._",
        ),
        "python_backend/services/runtime_service.py": (
            "llm_manager._",
            "memory_service._",
            "process_manager._",
            "worker_control_hub._",
        ),
    }
    offenders = []
    for relative_path, patterns in forbidden_access.items():
        source = (PROJECT_ROOT / relative_path).read_text(encoding="utf-8")
        offenders.extend(
            f"{relative_path}: {pattern}"
            for pattern in patterns
            if pattern in source
        )
    assert offenders == []


def test_worker_and_proxy_routes_share_request_contracts():
    assert worker_stt_routes.SttSwitchModelRequest is proxy_stt_routes.SttSwitchModelRequest
    assert worker_stt_routes.UnifiedAudioConfig is proxy_stt_routes.UnifiedAudioConfig
    assert worker_tts_routes.TtsSynthesisRequest is proxy_tts_routes.TtsSynthesisRequest
    assert worker_tts_routes.TtsSwitchRequest is proxy_tts_routes.TtsSwitchRequest
