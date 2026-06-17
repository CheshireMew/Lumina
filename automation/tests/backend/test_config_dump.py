
import json
import os
import sys

# Add python_backend to path
sys.path.insert(0, os.path.abspath("python_backend"))

# Mock environment to avoid loading secrets/db
os.environ["LUMINA_ENV"] = "dev"


def test_config_sections_are_serializable():
    from app_config import config

    extracted = {}
    for key in dir(config):
        if key.startswith("_"):
            continue
        val = getattr(config, key)
        if hasattr(val, "model_dump"):
            extracted[key] = val.model_dump()
        elif hasattr(val, "dict"):
            extracted[key] = val.dict()

    serialized = json.dumps(extracted, default=str)

    assert serialized
    assert {"audio", "capabilities", "llm", "memory", "models", "network", "search", "stt", "tts"}.issubset(
        extracted
    )
