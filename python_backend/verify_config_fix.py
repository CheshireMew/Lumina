
import sys
import os

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
        
    # 3. Access Models Config through the typed section.
    stt_model = config1.models.stt_model_path
    print(f"✅ ConfigManager Initialized. STT Model Path: {stt_model}")
    print("✅ P0 Verification Passed")

if __name__ == "__main__":
    test_config_initialization()
