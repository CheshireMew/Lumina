from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock

import pytest

from routers.companion import register_companion_activity
from services.companion.interaction import CompanionInteractionRecorder

pytestmark = pytest.mark.anyio


async def test_register_companion_activity_uses_companion_recorder_activity():
    soul = SimpleNamespace(update_last_interaction=MagicMock())
    recorder = CompanionInteractionRecorder(
        memory_service=SimpleNamespace(record_turn=AsyncMock()),
        session_manager=SimpleNamespace(add_turn=AsyncMock()),
        soul_service=soul,
    )

    response = await register_companion_activity(interaction_recorder=recorder)

    assert response == {"status": "ok", "message": "Heartbeat reset"}
    soul.update_last_interaction.assert_called_once_with()
