import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).parents[3]
sys.path.insert(0, str(PROJECT_ROOT / "python_backend"))


def test_voiceprint_router_uses_capability_prefix(monkeypatch):
    import fastapi.dependencies.utils as fastapi_dependency_utils

    monkeypatch.setattr(
        fastapi_dependency_utils,
        "ensure_multipart_is_installed",
        lambda: None,
    )

    from routers.voiceprint import router

    assert router.prefix == "/capabilities/voiceprint"
