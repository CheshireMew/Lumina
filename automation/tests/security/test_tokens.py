import sys
from pathlib import Path

import pytest

PROJECT_ROOT = Path(__file__).parents[3]
sys.path.insert(0, str(PROJECT_ROOT / "python_backend"))

pytest.importorskip("jwt")

from security.tokens import TokenManager


def test_token_manager_defaults_to_runtime_client_scope(monkeypatch):
    monkeypatch.setattr(TokenManager, "_secret_key", "test-secret")

    token = TokenManager.create_token("frontend", permissions=["gateway.connect"])

    assert TokenManager.verify_token(token, expected_scope="runtime_client")
    assert TokenManager.verify_token(token, expected_scope="plug" + "in") is None
