import os
import sys
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock

import pytest

np = pytest.importorskip("numpy")

sys.path.insert(0, os.path.abspath("python_backend"))


@pytest.mark.anyio
async def test_voiceprint_chain():
    from capabilities.stt import globals as stt_globals
    from capability_modules.voiceprint.module import Capability
    from services.audio_filter_chain import AudioFilterChain

    AudioFilterChain.reset()
    chain = AudioFilterChain.instance()
    assert chain.count == 0

    mock_context = MagicMock()
    mock_context.config = SimpleNamespace(
        audio=SimpleNamespace(
            enable_voiceprint_filter=True,
            voiceprint_threshold=0.6,
            voiceprint_profile="default",
        )
    )

    module = Capability()
    module._bind_manifest(
        SimpleNamespace(
            id="system.voiceprint",
            kind="processor",
            capability="stt",
            runtime_target="worker:stt",
            permissions=[],
            config_schema={},
            provides=[],
        )
    )
    module.driver = MagicMock()
    module.driver.load = AsyncMock()
    module.driver.verify = MagicMock(return_value=(True, "default", 0.92))
    module.refresh_profiles = AsyncMock()
    module.profiles = {"default": np.zeros(192, dtype=np.float32)}
    module.profile_status = {"default": True}
    module.current_profile = "default"

    await module.load(mock_context)
    await module.enable()

    assert chain.count == 1
    assert module.id in chain.active_filters
    assert stt_globals.voiceprint_manager is module

    audio = np.zeros(16000, dtype=np.float32)
    should_continue, reason = await chain.process(audio, 16000, {"audio_id": "pass"})
    assert should_continue is True
    assert reason is None

    module.driver.verify.return_value = (False, "default", 0.4)
    should_continue, reason = await chain.process(audio, 16000, {"audio_id": "reject"})
    assert should_continue is False
    assert "Voiceprint mismatch" in reason

    await module.disable()
    await module.unload()

    assert chain.count == 0
    assert stt_globals.voiceprint_manager is None

    should_continue, reason = await chain.process(audio, 16000, {"audio_id": "after-disable"})
    assert should_continue is True
    assert reason is None
