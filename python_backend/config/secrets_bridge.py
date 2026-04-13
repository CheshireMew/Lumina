"""Bridge SecretManager values into the runtime configuration bundle."""

import logging
from typing import Any, Optional


def _secret_manager():
    from security.secrets import SecretKey, SecretManager

    return SecretManager.instance(), SecretKey


def _get_non_env_secret(secret_manager: Any, secret_key: Any) -> Optional[str]:
    for backend in getattr(secret_manager, "_backends", []):
        if getattr(backend, "name", None) == "Environment":
            continue
        value = backend.get(secret_key)
        if value:
            return value

    config_cache = getattr(secret_manager, "_config_cache", {})
    return config_cache.get(secret_key)


def _register_config_fallbacks(bundle: Any) -> None:
    secret_manager, secret_key = _secret_manager()

    if bundle.llm.api_key:
        secret_manager.set_config_fallback(secret_key.OPENAI_API_KEY, bundle.llm.api_key)

    brave_settings = bundle.plugins.settings.get("brave", {})
    if brave_settings.get("api_key"):
        secret_manager.set_config_fallback(secret_key.BRAVE_API_KEY, brave_settings["api_key"])

    if bundle.memory.postgres.password:
        secret_manager.set_config_fallback(secret_key.POSTGRES_PASSWORD, bundle.memory.postgres.password)


def apply_secret_bridge(bundle: Any, logger: logging.Logger) -> None:
    try:
        _register_config_fallbacks(bundle)
        secret_manager, secret_key = _secret_manager()
    except ImportError:
        logger.warning("SecretManager not available, skipping secret bridge")
        return

    secret_map = (
        (secret_key.OPENAI_API_KEY, lambda value: setattr(bundle.llm, "api_key", value)),
        (
            secret_key.BRAVE_API_KEY,
            lambda value: bundle.plugins.settings.setdefault("brave", {}).__setitem__("api_key", value),
        ),
        (secret_key.POSTGRES_PASSWORD, lambda value: setattr(bundle.memory.postgres, "password", value)),
    )

    for key, apply_value in secret_map:
        value = _get_non_env_secret(secret_manager, key)
        if value:
            apply_value(value)

    source = secret_manager.get_source(secret_key.OPENAI_API_KEY)
    if bundle.llm.api_key and source:
        logger.info(f"LLM API Key loaded from: {source}")
