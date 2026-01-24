import os
import re
import sys
import yaml
from pathlib import Path

def sanitize_id(plugin_id):
    """Normalize ID to safe folder name"""
    return re.sub(r'[^a-z0-9_\-\.]', '', plugin_id.lower())

def create_plugin():
    print("🚀 Lumina Plugin Scaffolder")
    print("===========================")
    
    # 1. Gather Info
    name = input("Plugin Name (e.g., Stock Ticker): ").strip()
    plugin_id = input("Plugin ID (e.g., extensions.stock_ticker): ").strip()
    description = input("Description: ").strip()
    author = input("Author: ").strip()
    
    safe_name = plugin_id.split(".")[-1]
    
    # 2. Paths
    # Assume script is run from project root or scripts folder
    root = Path.cwd()
    if (root / "python_backend").exists():
        target_dir = root / "python_backend" / "plugins" / "extensions" / safe_name
    elif (root / "plugins").exists():
        target_dir = root / "plugins" / "extensions" / safe_name
    else:
        # Fallback
        target_dir = root / "extensions" / safe_name
        
    if target_dir.exists():
        print(f"❌ Error: Directory {target_dir} already exists.")
        sys.exit(1)
        
    os.makedirs(target_dir, exist_ok=True)
    
    # 3. Manifest
    manifest = {
        "id": plugin_id,
        "name": name,
        "description": description,
        "version": "0.1.0",
        "author": author,
        "entrypoint": "main:MyPlugin",
        "isolation_mode": "local", # Default to local for simpler routing/debugging
        "permissions": [
            "network.external"
        ],
        "ui_slots": [
            {
                "slot": "sidebar_right",
                # "type": "iframe", # Implicit/Removed
                "src": "/assets/index.html",
                "name": name, # Was title
                "height": "300px",
                "width": "100%"
            }
        ]
    }
    
    with open(target_dir / "manifest.yaml", "w", encoding="utf-8") as f:
        yaml.dump(manifest, f, sort_keys=False)
        
    # 4. Entrypoint (main.py)
    code = f"""from core.interfaces.plugin import BaseSystemPlugin
import logging

logger = logging.getLogger("{plugin_id}")

class MyPlugin(BaseSystemPlugin):
    @property
    def id(self):
        return "{plugin_id}"

    @property
    def name(self):
        return "{name}"

    def initialize(self, context):
        super().initialize(context)
        logger.info("INIT: {name} Plugin Loaded!")
        
        # Register API Route
        self.register_route(
            method="GET",
            path="/status",
            handler=self.handle_status
        )

    async def handle_status(self):
        return {{"status": "active", "plugin": self.id}}
"""
    with open(target_dir / "main.py", "w", encoding="utf-8") as f:
        f.write(code)
        
    # 5. UI Assets
    ui_dir = target_dir / "ui"
    os.makedirs(ui_dir, exist_ok=True)
    
    html = f"""<!DOCTYPE html>
<html>
<head>
    <style>
        body {{ background: #1a1a1a; color: white; font-family: sans-serif; padding: 10px; }}
        h3 {{ margin: 0 0 10px 0; color: #ff69b4; }}
    </style>
</head>
<body>
    <h3>{name}</h3>
    <p>{description}</p>
    <div id="status">Loading...</div>
    
    <script>
        // Use Backend API
        fetch('/api/plugins/{plugin_id}/status')
            .then(res => res.json())
            .then(data => {{
                document.getElementById('status').innerText = JSON.stringify(data, null, 2);
            }});
    </script>
</body>
</html>"""
    with open(ui_dir / "index.html", "w", encoding="utf-8") as f:
        f.write(html)
        
    print(f"\n✅ Plugin created at: {target_dir}")
    print("Restart backend to load!")

if __name__ == "__main__":
    create_plugin()
