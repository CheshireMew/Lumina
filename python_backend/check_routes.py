
import sys
import os

# Setup Path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from main import app
from fastapi.routing import APIRoute

print("=== REGISTERED ROUTES ===")
found_audio = False
for route in app.routes:
    if isinstance(route, APIRoute):
        print(f"Path: {route.path} | Name: {route.name} | Methods: {route.methods}")
        if "audio" in route.path:
            found_audio = True

if found_audio:
    print("\n✅ SUCCESS: /audio routes found!")
else:
    print("\n❌ FAILED: /audio routes NOT found!")
