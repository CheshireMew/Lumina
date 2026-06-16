import logging
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).parents[3]
sys.path.append(str(PROJECT_ROOT / "python_backend"))

from config.loader import ConfigBundle, hydrate_config
from config.models import DEFAULT_SELECTED_PROVIDERS


def test_default_config_materializes_selected_providers():
    bundle = ConfigBundle()

    assert bundle.plugins.selected_providers == DEFAULT_SELECTED_PROVIDERS


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

    assert bundle.plugins.selected_providers == DEFAULT_SELECTED_PROVIDERS


def test_plugin_settings_use_plugin_ids():
    bundle = hydrate_config(
        {
            "plugins": {
                "settings": {
                    "driver.tool.search.brave": {"api_key": "test-key"},
                },
            },
        },
        logging.getLogger("test"),
    )

    assert bundle.plugins.settings == {
        "driver.tool.search.brave": {"api_key": "test-key"},
    }


def test_explicit_selected_providers_are_not_backfilled():
    bundle = hydrate_config(
        {"plugins": {"selected_providers": {}}},
        logging.getLogger("test"),
    )

    assert bundle.plugins.selected_providers == {}
