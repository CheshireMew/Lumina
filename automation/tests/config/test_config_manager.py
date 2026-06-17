import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).parents[3]
sys.path.append(str(PROJECT_ROOT / "python_backend"))

from app_config import ConfigManager


def test_config_manager_singleton_exposes_typed_models_section():
    config1 = ConfigManager()
    config2 = ConfigManager()

    assert config1 is config2
    assert config1.models is not None
    assert hasattr(config1.models, "stt_model_path")

