"""
Centralized Configuration for Lumina Backend
Handles path resolution for Dev vs Frozen (PyInstaller) environments.
"""
import sys
import os
from pathlib import Path

# Detect frozen state (PyInstaller)
# sys.frozen is set by PyInstaller
IS_FROZEN = getattr(sys, 'frozen', False)

# Resolution Base Path
if IS_FROZEN:
    # In PyInstaller bundle, use _MEIPASS
    BASE_DIR = Path(sys._MEIPASS) # type: ignore
else:
    # In Dev, use script directory
    BASE_DIR = Path(__file__).parent.absolute()

# Resource Paths
# In Lite Mode packaging, models/assets might be in external "bin" folder or internal
# We define standard lookups here.

# Models Directory
# Prioritize local models folder if exists, else look relative to binary
MODELS_DIR = BASE_DIR / "models"
if not MODELS_DIR.exists() and IS_FROZEN:
    # If not in MEIPASS, check executable directory (Sidecar pattern)
    # sys.executable points to the exe
    EXE_DIR = Path(sys.executable).parent
    MODELS_DIR = EXE_DIR / "models"

# Assets Directory (Conf, etc)
ASSETS_DIR = BASE_DIR / "assets"

# Config Persistence (always next to executable/script, not in temp MEIPASS)
if IS_FROZEN:
    CONFIG_ROOT = Path(sys.executable).parent
else:
    CONFIG_ROOT = BASE_DIR

# Feature Flags
LITE_MODE = os.environ.get("LITE_MODE", "false").lower() == "true"

def get_writable_path(filename: str) -> Path:
    """Returns a path suitable for writing config/logs (not in temp/frozen)"""
    return CONFIG_ROOT / filename
