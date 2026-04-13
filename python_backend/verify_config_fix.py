
import sys
import os
from pathlib import Path

# Add project root to path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from app_config import ConfigManager

def test_config_initialization():
    print("Testing ConfigManager Initialization...")
    
    # 1. First Instantiation
    config1 = ConfigManager()
    if not config1._is_initialized:
        print("❌ ConfigManager not initialized after __init__")
        sys.exit(1)
        
    # 2. Singleton Check
    config2 = ConfigManager()
    if config1 is not config2:
        print("❌ Singleton property failed")
        sys.exit(1)
        
    if config1._models_config is None:
        print("❌ _models_config is None")
        sys.exit(1)
        
    # 3. Access Models Config
    models = config1.get("models", "stt_model_path")
    # Note: get("models", "key") in app_config returns getattr(config_object, key)
    # But wait, app_config.py get() implementation:
    # return getattr(config_obj, key, default)
    # If section is "models", key is "stt_model_path".
    
    stt_model = config1.get("models", "stt_model_path")
    print(f"✅ ConfigManager Initialized. STT Model Path: {stt_model}")
    print("✅ P0 Verification Passed")

if __name__ == "__main__":
    test_config_initialization()
