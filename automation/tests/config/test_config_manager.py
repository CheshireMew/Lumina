import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).parents[3]
sys.path.append(str(PROJECT_ROOT / "python_backend"))

from app_config import ConfigManager


def test_config_manager_instances_are_isolated_and_typed():
    config1 = ConfigManager()
    config2 = ConfigManager()

    assert config1 is not config2
    assert config1.models is not None
    assert hasattr(config1.models, "stt_model_path")
