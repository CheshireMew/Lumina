import logging
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).parents[3]
sys.path.append(str(PROJECT_ROOT / "python_backend"))

from config.loader import ConfigBundle
from config.secrets_bridge import BRAVE_SEARCH_PROVIDER_ID, CUSTOM_LLM_PROVIDER_ID, apply_secret_bridge
from security.secrets import SecretKey


class _PersistedSecretManager:
    def __init__(self, values: dict[SecretKey, str]):
        self._values = values

    def get_persisted(self, key: SecretKey) -> str | None:
        return self._values.get(key)

    def get_source(self, key: SecretKey) -> str | None:
        return "Keyring" if key in self._values else None


def test_secret_bridge_applies_persisted_secrets_without_config_fallback(monkeypatch):
    bundle = ConfigBundle()
    bundle.llm.providers[CUSTOM_LLM_PROVIDER_ID].api_key = "config-llm-key"
    bundle.capabilities.settings[BRAVE_SEARCH_PROVIDER_ID] = {"api_key": "config-brave-key"}
    bundle.memory.postgres.password = "config-pg-password"

    persisted = _PersistedSecretManager(
        {
            SecretKey.OPENAI_API_KEY: "keyring-llm-key",
            SecretKey.BRAVE_API_KEY: "keyring-brave-key",
            SecretKey.POSTGRES_PASSWORD: "keyring-pg-password",
        }
    )
    monkeypatch.setattr(
        "config.secrets_bridge._secret_manager",
        lambda: (persisted, SecretKey),
    )

    apply_secret_bridge(bundle, logging.getLogger("test"))

    assert bundle.llm.providers[CUSTOM_LLM_PROVIDER_ID].api_key == "keyring-llm-key"
    assert bundle.capabilities.settings[BRAVE_SEARCH_PROVIDER_ID]["api_key"] == "keyring-brave-key"
    assert bundle.memory.postgres.password == "keyring-pg-password"
