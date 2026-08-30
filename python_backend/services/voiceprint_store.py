import logging
from typing import Any

from services.infra.local_state_store import get_local_state_store

logger = logging.getLogger("VoiceprintStore")

TABLE = "voiceprint_profiles"


class VoiceprintStoreUnavailable(RuntimeError):
    pass


def _store():
    return get_local_state_store()


async def list_profiles() -> list[dict[str, Any]]:
    try:
        return await _store().list_voiceprint_profiles()
    except Exception as exc:
        raise VoiceprintStoreUnavailable("Voiceprint database is unavailable") from exc


async def set_profile_enabled(name: str, enabled: bool):
    try:
        await _store().set_voiceprint_enabled(name, enabled)
    except Exception as exc:
        raise VoiceprintStoreUnavailable("Voiceprint database is unavailable") from exc


async def delete_profile(name: str):
    try:
        await _store().delete_voiceprint_profile(name)
    except Exception as exc:
        raise VoiceprintStoreUnavailable("Voiceprint database is unavailable") from exc


async def upsert_profile(name: str, embedding_b64: str, enabled: bool = True):
    try:
        await _store().upsert_voiceprint_profile(name, embedding_b64, enabled)
    except Exception as exc:
        raise VoiceprintStoreUnavailable("Voiceprint database is unavailable") from exc
