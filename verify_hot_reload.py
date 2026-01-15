import requests
import time
import os
import shutil
from pathlib import Path

BASE_URL = "http://127.0.0.1:8010"
PLUGIN_DIR = Path("python_backend/plugins/system/test_reload")
MANIFEST_PATH = PLUGIN_DIR / "manifest.yaml"
MODULE_PATH = PLUGIN_DIR / "plugin.py"

def create_test_plugin(version="v1"):
    if not PLUGIN_DIR.exists():
        PLUGIN_DIR.mkdir(parents=True)

    manifest = f"""
id: system.test_reload
version: 1.0.0
name: Test Reload Plugin
description: Plugin for testing hot reload
entrypoint: plugin:TestReloadPlugin
permissions: []
"""
    with open(MANIFEST_PATH, "w") as f:
        f.write(manifest)

    code_v1 = """
from plugins.base import BaseSystemPlugin
import logging

class TestReloadPlugin(BaseSystemPlugin):
    @property
    def id(self): return "system.test_reload"
    @property
    def name(self): return "Test Reload Plugin"
    
    def initialize(self, context):
        self.context = context
        logging.getLogger("TestReload").info("v1 Initialized")
    
    def get_version(self):
        return "v1"
"""
    
    code_v2 = """
from plugins.base import BaseSystemPlugin
import logging

class TestReloadPlugin(BaseSystemPlugin):
    @property
    def id(self): return "system.test_reload"
    @property
    def name(self): return "Test Reload Plugin"
    
    def initialize(self, context):
        self.context = context
        logging.getLogger("TestReload").info("v2 Initialized (RELOADED)")
    
    def get_version(self):
        return "v2"
"""
    
    target_code = code_v1 if version == "v1" else code_v2
    with open(MODULE_PATH, "w") as f:
        f.write(target_code)
    print(f"📝 Created plugin {version}")

def trigger_reload():
    print("🔄 Triggering reload via API...")
    try:
        resp = requests.post(f"{BASE_URL}/debug/plugins/system.test_reload/reload")
        if resp.status_code == 200:
            print("✅ Reload API Success:", resp.json())
            return True
        else:
            print("❌ Reload API Failed:", resp.text)
            return False
    except Exception as e:
        print(f"❌ Connection Error: {e}")
        return False

def verify_active(expected_version):
    # Since we can't easily call get_version remotely without another endpoint,
    # we'll rely on the reload success log for now.
    # Ideally, we would inspect the plugin list status if it returned version metadata from the instance.
    print(f"❓ Verifying {expected_version} (Log check required)")
    pass

def main():
    try:
        # 1. Create v1
        create_test_plugin("v1")
        
        # 2. Reload to load v1 (since it's new)
        if not trigger_reload():
            print("❌ Failed initial load")
            return
            
        time.sleep(2)
        
        # 3. Modify to v2
        create_test_plugin("v2")
        
        # 4. Reload
        if trigger_reload():
            print("🎉 Hot Reload Triggered Successfully!")
            print("⚠️ Check logs for 'v2 Initialized (RELOADED)' to confirm code change.")
        
    finally:
        # Cleanup
        if PLUGIN_DIR.exists():
            shutil.rmtree(PLUGIN_DIR)
            print("🧹 Cleanup complete")

if __name__ == "__main__":
    main()
