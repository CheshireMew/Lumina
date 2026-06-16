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
    from plugins.extensions.voiceprint.plugin import Plugin
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

    plugin = Plugin()
    plugin._bind_manifest(
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
    plugin.driver = MagicMock()
    plugin.driver.load = AsyncMock()
    plugin.driver.verify = MagicMock(return_value=(True, "default", 0.92))
    plugin.refresh_profiles = AsyncMock()
    plugin.profiles = {"default": np.zeros(192, dtype=np.float32)}
    plugin.profile_status = {"default": True}
    plugin.current_profile = "default"

    await plugin.load(mock_context)
    await plugin.enable()

    assert chain.count == 1
    assert plugin.id in chain.active_filters
    assert stt_globals.voiceprint_manager is plugin

    audio = np.zeros(16000, dtype=np.float32)
    should_continue, reason = await chain.process(audio, 16000, {"audio_id": "pass"})
    assert should_continue is True
    assert reason is None

    plugin.driver.verify.return_value = (False, "default", 0.4)
    should_continue, reason = await chain.process(audio, 16000, {"audio_id": "reject"})
    assert should_continue is False
    assert "Voiceprint mismatch" in reason

    await plugin.disable()
    await plugin.unload()

    assert chain.count == 0
    assert stt_globals.voiceprint_manager is None

    should_continue, reason = await chain.process(audio, 16000, {"audio_id": "after-disable"})
    assert should_continue is True
    assert reason is None
