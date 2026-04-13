from __future__ import annotations


LEGACY_PROVIDER_ALIASES: dict[str, dict[str, str]] = {
    "stt": {
        "sense-voice": "driver.stt.sensevoice",
        "sensevoice": "driver.stt.sensevoice",
        "mock_driver": "driver.stt.sensevoice",
    },
    "tts": {
        "edge-tts": "driver.tts.edge",
        "edge": "driver.tts.edge",
        "driver.tts.edge-tts": "driver.tts.edge",
    },
    "memory": {
        "postgres": "driver.memory.postgres",
        "postgres-db": "driver.memory.postgres",
        "surreal": "driver.memory.postgres",
        "surreal-db": "driver.memory.postgres",
    },
    "tool.search": {
        "brave": "driver.tool.search.brave",
        "duckduckgo": "driver.tool.search.duckduckgo",
    },
}


def normalize_provider_id(capability: str, provider_id: str | None) -> str | None:
    if provider_id is None:
        return None

    normalized_capability = capability.strip().lower()
    normalized_provider = provider_id.strip()
    if not normalized_provider:
        return normalized_provider

    return LEGACY_PROVIDER_ALIASES.get(normalized_capability, {}).get(
        normalized_provider.lower(),
        normalized_provider,
    )
