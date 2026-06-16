import sys
from pathlib import Path

import pytest

PROJECT_ROOT = Path(__file__).parents[3]
sys.path.insert(0, str(PROJECT_ROOT / "python_backend"))

from routers.llm_mgmt import get_feature_params


class FakeLLMManager:
    def __init__(self):
        self.calls = []

    def get_parameters(self, feature, soul_state=None):
        self.calls.append({"feature": feature, "soul_state": soul_state})
        return {"feature": feature, "soul_state": soul_state}


class FakeSoulService:
    def __init__(self, state):
        self.state = state
        self.calls = 0

    def get_llm_adjustment_state(self):
        self.calls += 1
        return self.state


class SoulStateShouldNotBeRead:
    def get_llm_adjustment_state(self):
        raise AssertionError("Soul state should not be read for non-personality routes")


@pytest.mark.anyio
async def test_get_feature_params_passes_soul_state_for_chat_route():
    llm_manager = FakeLLMManager()
    soul_service = FakeSoulService({"temperature": 0.9})

    params = await get_feature_params(
        "chat",
        llm_manager=llm_manager,
        soul_service=soul_service,
    )

    assert params == {"feature": "chat", "soul_state": {"temperature": 0.9}}
    assert soul_service.calls == 1
    assert llm_manager.calls == [{"feature": "chat", "soul_state": {"temperature": 0.9}}]


@pytest.mark.anyio
async def test_get_feature_params_passes_soul_state_for_proactive_route():
    llm_manager = FakeLLMManager()
    soul_service = FakeSoulService({"presence_penalty": 0.2})

    params = await get_feature_params(
        "proactive",
        llm_manager=llm_manager,
        soul_service=soul_service,
    )

    assert params == {"feature": "proactive", "soul_state": {"presence_penalty": 0.2}}
    assert soul_service.calls == 1


@pytest.mark.anyio
async def test_get_feature_params_does_not_read_soul_state_for_other_routes():
    llm_manager = FakeLLMManager()

    params = await get_feature_params(
        "memory",
        llm_manager=llm_manager,
        soul_service=SoulStateShouldNotBeRead(),
    )

    assert params == {"feature": "memory", "soul_state": None}
    assert llm_manager.calls == [{"feature": "memory", "soul_state": None}]
