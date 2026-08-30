import os
import sys
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock

import pytest

np = pytest.importorskip("numpy")

sys.path.insert(0, os.path.abspath("python_backend"))


@pytest.mark.anyio
async def test_voiceprint_chain():
    from services.audio_filter_chain import AudioFilterChain
    from services.voiceprint_filter import VoiceprintFilter

    AudioFilterChain.reset()
    chain = AudioFilterChain.instance()
    assert chain.count == 0

    config = SimpleNamespace(
        audio=SimpleNamespace(
            enable_voiceprint_filter=True,
            voiceprint_threshold=0.6,
            voiceprint_profile="default",
        )
    )

    module = VoiceprintFilter(config)
    module.driver = MagicMock()
    module.driver.load = AsyncMock()
    module.driver.verify = MagicMock(return_value=(True, "default", 0.92))
    module.profiles = {"default": np.zeros(192, dtype=np.float32)}
    module.profile_status = {"default": True}
    module.current_profile = "default"
    module.refresh_profiles = AsyncMock(
        side_effect=lambda *args, **kwargs: None
    )

    await module.start()

    assert chain.count == 1
    assert module.id in chain.active_filters

    audio = np.zeros(16000, dtype=np.float32)
    should_continue, reason = await chain.process(audio, 16000, {"audio_id": "pass"})
    assert should_continue is True
    assert reason is None

    module.driver.verify.return_value = (False, "default", 0.4)
    should_continue, reason = await chain.process(audio, 16000, {"audio_id": "reject"})
    assert should_continue is False
    assert "Voiceprint mismatch" in reason

    await module.stop()

    assert chain.count == 0

    should_continue, reason = await chain.process(audio, 16000, {"audio_id": "after-disable"})
    assert should_continue is True
    assert reason is None


@pytest.mark.anyio
async def test_enabled_voiceprint_filter_rejects_when_no_profile_is_available():
    from services.voiceprint_filter import VoiceprintFilter

    config = SimpleNamespace(
        audio=SimpleNamespace(
            enable_voiceprint_filter=True,
            voiceprint_threshold=0.6,
            voiceprint_profile="",
        )
    )
    module = VoiceprintFilter(config)
    module.refresh_profiles = AsyncMock(side_effect=lambda *args, **kwargs: None)

    should_continue, reason = await module.filter(
        np.zeros(16000, dtype=np.float32),
        16000,
        {"audio_id": "missing-profile"},
    )

    assert should_continue is False
    assert "没有可用" in reason
