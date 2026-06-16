"""Environment loading and runtime overrides for backend configuration."""

import logging
import os
from typing import Any


BRAVE_SEARCH_PROVIDER_ID = "driver.tool.search.brave"

_DOTENV_LOADED = False


def load_environment(logger: logging.Logger) -> None:
    global _DOTENV_LOADED
    if _DOTENV_LOADED:
        return

    try:
        from dotenv import find_dotenv, load_dotenv
    except ImportError:
        logger.debug("python-dotenv not installed; skipping .env loading")
        _DOTENV_LOADED = True
        return

    env_file = find_dotenv(usecwd=True)
    if env_file:
        logger.info(f"Loading environment variables from: {env_file}")
        load_dotenv(env_file)
    else:
        logger.debug("No .env file found (Searching CWD)")

    _DOTENV_LOADED = True


def apply_env_overrides(bundle: Any) -> None:
    network = bundle.network
    llm = bundle.llm
    plugins = bundle.plugins
    postgres = bundle.memory.postgres

    if os.environ.get("LUMINA_MEMORY_PORT"):
        network.memory_port = int(os.environ["LUMINA_MEMORY_PORT"])
    if os.environ.get("LUMINA_STT_PORT"):
        network.stt_port = int(os.environ["LUMINA_STT_PORT"])
    if os.environ.get("LUMINA_TTS_PORT"):
        network.tts_port = int(os.environ["LUMINA_TTS_PORT"])

    if os.environ.get("OPENAI_API_KEY"):
        llm.api_key = os.environ["OPENAI_API_KEY"]
    if os.environ.get("OPENAI_BASE_URL"):
        llm.base_url = os.environ["OPENAI_BASE_URL"]
    if os.environ.get("LLM_MODEL"):
        llm.model = os.environ["LLM_MODEL"]

    if os.environ.get("BRAVE_API_KEY"):
        plugins.settings.setdefault(BRAVE_SEARCH_PROVIDER_ID, {})["api_key"] = os.environ["BRAVE_API_KEY"]

    if os.environ.get("LUMINA_PG_HOST"):
        postgres.host = os.environ["LUMINA_PG_HOST"]
    if os.environ.get("LUMINA_PG_PORT"):
        postgres.port = int(os.environ["LUMINA_PG_PORT"])
    if os.environ.get("LUMINA_PG_USER"):
        postgres.user = os.environ["LUMINA_PG_USER"]
    if os.environ.get("LUMINA_PG_PASSWORD"):
        postgres.password = os.environ["LUMINA_PG_PASSWORD"]
    if os.environ.get("LUMINA_PG_DATABASE"):
        postgres.database = os.environ["LUMINA_PG_DATABASE"]

    if os.environ.get("SEARCH_PROVIDER"):
        plugins.selected_providers["tool.search"] = os.environ["SEARCH_PROVIDER"]
