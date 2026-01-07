import sys
import os
sys.path.append(os.path.join(os.getcwd(), 'python_backend'))
from soul_manager import SoulManager
import shutil

test_id = "test_char_persist"
base_dir = os.path.join('python_backend', 'characters', test_id)

# Cleanup
if os.path.exists(base_dir):
    shutil.rmtree(base_dir)

print(f"Creating SoulManager for {test_id}...")
soul = SoulManager(test_id)

if os.path.exists(base_dir):
    print("✅ Character directory created!")
    if os.path.exists(os.path.join(base_dir, 'config.json')):
        print("✅ config.json created!")
    else:
        print("❌ config.json MISSING!")
else:
    print("❌ Character directory MISSING!")
