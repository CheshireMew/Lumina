
import sys
import os
import json
import logging

# Add python_backend to path
sys.path.insert(0, os.path.abspath("python_backend"))

# Mock environment to avoid loading secrets/db
os.environ["LUMINA_ENV"] = "dev"

try:
    from app_config import config
    print("Config Object:", type(config))
    
    # Simulate Proxy Logic
    extracted = {}
    obj_to_scan = config
    
    for key in dir(obj_to_scan):
        if key.startswith("_"): continue
        val = getattr(obj_to_scan, key)
        if hasattr(val, 'model_dump'):
             extracted[key] = val.model_dump()
        elif hasattr(val, 'dict'):
             extracted[key] = val.dict()
             
    print(f"Extracted Keys: {list(extracted.keys())}")
    
    # Test Serialization
    serialized = json.dumps(extracted, default=str)
    print("Serialization Success!")
    print("Length:", len(serialized))
except Exception as e:
    print(f"Serialization Failed: {e}")
    sys.exit(1)
