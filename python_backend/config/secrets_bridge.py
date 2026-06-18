"""Bridge SecretManager values into the runtime configuration bundle."""

import logging
from typing import Any

from config.models import CUSTOM_LLM_PROVIDER_ID

BRAVE_SEARCH_PROVIDER_ID = "driver.tool.search.brave"


def _secret_manager():
    from security.secrets import SecretKey, SecretManager

    return SecretManager.instance(), SecretKey


def apply_secret_bridge(bundle: Any, logger: logging.Logger) -> None:
    try:
        secret_manager, secret_key = _secret_manager()
    except ImportError:
        logger.warning("SecretManager not available, skipping secret bridge")
        return

    custom_llm_provider = bundle.llm.providers.get(CUSTOM_LLM_PROVIDER_ID)
    secret_map = (
        (
            secret_key.OPENAI_API_KEY,
            lambda value: setattr(custom_llm_provider, "api_key", value) if custom_llm_provider else None,
        ),
        (
            secret_key.BRAVE_API_KEY,
            lambda value: bundle.capabilities.settings.setdefault(BRAVE_SEARCH_PROVIDER_ID, {}).__setitem__("api_key", value),
        ),
        (secret_key.POSTGRES_PASSWORD, lambda value: setattr(bundle.memory.postgres, "password", value)),
    )

    for key, apply_value in secret_map:
        value = secret_manager.get_persisted(key)
        if value:
            apply_value(value)

    source = secret_manager.get_source(secret_key.OPENAI_API_KEY)
    if custom_llm_provider and custom_llm_provider.api_key and source:
        logger.info(f"LLM API Key loaded from: {source}")
