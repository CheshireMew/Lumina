import sys
from pathlib import Path
from unittest.mock import AsyncMock, patch

import pytest

PROJECT_ROOT = Path(__file__).parents[3]
sys.path.append(str(PROJECT_ROOT / "python_backend"))


class LocalStoreStub:
    def __init__(self):
        self.list_voiceprint_profiles = AsyncMock(return_value=[])
        self.set_voiceprint_enabled = AsyncMock()
        self.delete_voiceprint_profile = AsyncMock()
        self.upsert_voiceprint_profile = AsyncMock()


@pytest.mark.anyio
async def test_voiceprint_list_profiles_uses_local_store_boundary():
    from services import voiceprint_store

    rows = [
        {
            "id": "voiceprint_profiles:alice",
            "name": "alice",
            "enabled": True,
            "embedding": "abc",
            "created_at": "created",
            "updated_at": "updated",
        }
    ]
    store = LocalStoreStub()
    store.list_voiceprint_profiles.return_value = rows

    with patch("services.voiceprint_store.get_local_state_store", return_value=store):
        profiles = await voiceprint_store.list_profiles()

    assert profiles == rows
    store.list_voiceprint_profiles.assert_awaited_once_with()


@pytest.mark.anyio
async def test_voiceprint_mutations_use_local_store_boundary():
    from services import voiceprint_store

    store = LocalStoreStub()

    with patch("services.voiceprint_store.get_local_state_store", return_value=store):
        await voiceprint_store.set_profile_enabled("alice", False)
        await voiceprint_store.delete_profile("alice")
        await voiceprint_store.upsert_profile("alice", "embedding", enabled=True)

    store.set_voiceprint_enabled.assert_awaited_once_with("alice", False)
    store.delete_voiceprint_profile.assert_awaited_once_with("alice")
    store.upsert_voiceprint_profile.assert_awaited_once_with("alice", "embedding", True)


@pytest.mark.anyio
async def test_voiceprint_store_failure_raises_domain_error():
    from services import voiceprint_store

    store = LocalStoreStub()
    store.list_voiceprint_profiles.side_effect = RuntimeError("sqlite unavailable")

    with patch("services.voiceprint_store.get_local_state_store", return_value=store):
        with pytest.raises(voiceprint_store.VoiceprintStoreUnavailable) as exc_info:
            await voiceprint_store.list_profiles()

    assert "Voiceprint database is unavailable" in str(exc_info.value)
    assert isinstance(exc_info.value.__cause__, RuntimeError)
