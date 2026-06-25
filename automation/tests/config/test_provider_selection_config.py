import logging
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).parents[3]
sys.path.append(str(PROJECT_ROOT / "python_backend"))

from config.loader import ConfigBundle, hydrate_config
from config.models import DEFAULT_SELECTED_PROVIDERS, POLLINATIONS_DEFAULT_MODEL


def test_default_config_materializes_selected_providers():
    bundle = ConfigBundle()

    assert bundle.capabilities.selected_providers == DEFAULT_SELECTED_PROVIDERS


def test_legacy_provider_fields_do_not_drive_selected_providers():
    bundle = hydrate_config(
        {
            "memory": {"provider": "driver.memory.other"},
            "stt": {"provider": "driver.stt.other"},
            "tts": {"provider": "driver.tts.other"},
            "search": {"provider": "driver.tool.search.other"},
        },
        logging.getLogger("test"),
    )

    assert bundle.capabilities.selected_providers == DEFAULT_SELECTED_PROVIDERS


def test_provider_settings_use_provider_ids():
    bundle = hydrate_config(
        {
            "capabilities": {
                "settings": {
                    "driver.tool.search.brave": {"api_key": "test-key"},
                },
            },
        },
        logging.getLogger("test"),
    )

    assert bundle.capabilities.settings == {
        "driver.tool.search.brave": {"api_key": "test-key"},
    }


def test_legacy_llm_fields_do_not_drive_runtime_routes_or_providers():
    bundle = hydrate_config(
        {
            "llm": {
                "model": "legacy-model",
                "base_url": "https://legacy.invalid/v1",
                "api_key": "legacy-key",
            },
        },
        logging.getLogger("test"),
    )

    assert bundle.llm.routes["chat"].model == POLLINATIONS_DEFAULT_MODEL
    assert bundle.llm.providers["custom_provider"].base_url == "http://localhost:11434/v1"
    assert bundle.llm.providers["custom_provider"].api_key == ""


def test_explicit_selected_providers_are_not_backfilled():
    bundle = hydrate_config(
        {"capabilities": {"selected_providers": {}}},
        logging.getLogger("test"),
    )

    assert bundle.capabilities.selected_providers == {}
