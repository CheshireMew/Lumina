#!/usr/bin/env python
"""
Lumina Plugin Template Generator

Creates a new plugin with proper structure and boilerplate code.

Usage:
    python scripts/create_plugin.py my_company.my_plugin
    python scripts/create_plugin.py my_plugin --author "Your Name" --category feature
    
Options:
    --author     Author name for manifest
    --category   Plugin category (system/feature/integration)
    --target     Target directory (default: plugins/extensions)
"""

import sys
import argparse
from pathlib import Path

# Add parent to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))


MANIFEST_TEMPLATE = '''id: "{plugin_id}"
version: "1.0.0"
name: "{plugin_name}"
description: "TODO: Describe what this plugin does"
entrypoint: "manager:{class_name}"
author: "{author}"
category: "{category}"
tags: []

# API version this plugin is built for
api_version: "1.0"

# Dependencies (other plugin IDs)
dependencies: []

# Required permissions (see docs/PLUGIN_DEVELOPMENT.md)
permissions:
  - event.subscribe
  - event.emit

# Optional: Group exclusivity (for STT/TTS drivers)
# group_id: "stt"
# group_exclusive: true

# Optional: Configuration schema for settings UI
# config_schema:
#   key: "my_setting"
#   type: "string"
#   label: "My Setting"
#   description: "Configure something"
#   default: ""
'''

MANAGER_TEMPLATE = '''"""
{plugin_name} Plugin

TODO: Describe what this plugin does.
"""

import logging
from typing import Any
from core.interfaces.plugin import BaseSystemPlugin

logger = logging.getLogger("{class_name}")


class {class_name}(BaseSystemPlugin):
    """
    {plugin_name}
    
    TODO: Add plugin description.
    """

    @property
    def id(self) -> str:
        return "{plugin_id}"

    @property
    def name(self) -> str:
        return "{plugin_name}"

    def initialize(self, context: Any):
        """Called when the plugin is loaded."""
        super().initialize(context)
        
        # Subscribe to events
        # context.bus.subscribe("system.tick", self._on_tick)
        
        # Register as a service (optional)
        # context.register_service("{service_name}", self)
        
        logger.info("✨ {plugin_name} initialized!")

    def terminate(self):
        """Called before the plugin is unloaded."""
        # Cleanup resources here
        logger.info("👋 {plugin_name} terminated")

    # ============ Event Handlers ============
    
    # async def _on_tick(self, event):
    #     """Called every second"""
    #     pass

    # ============ Public API ============
    
    def get_status(self) -> dict:
        """Return plugin status for frontend."""
        status = super().get_status()
        # Add custom status fields
        # status["my_field"] = "value"
        return status
'''

README_TEMPLATE = '''# {plugin_name}

> TODO: One-line description

## Features

- TODO: List features

## Configuration

| Key | Type | Description | Default |
|-----|------|-------------|---------|
| TODO | string | TODO | "" |

## API

### Events Emitted

- `{plugin_id}.ready` - Emitted when plugin is ready

### Events Subscribed

- `system.tick` - System tick event

## Development

```bash
# Reload during development
curl -X POST http://localhost:8010/plugins/reload/{plugin_id}
```

## License

MIT
'''


def to_class_name(plugin_id: str) -> str:
    """Convert plugin ID to class name (PascalCase)"""
    # my_company.my_plugin -> MyCompanyMyPlugin
    # my-plugin -> MyPlugin
    parts = plugin_id.replace("-", "_").replace(".", "_").split("_")
    return "".join(word.capitalize() for word in parts)


def to_plugin_name(plugin_id: str) -> str:
    """Convert plugin ID to human-readable name"""
    # my_company.my_plugin -> My Company My Plugin
    parts = plugin_id.replace("-", " ").replace(".", " ").replace("_", " ").split()
    return " ".join(word.capitalize() for word in parts)


def create_plugin(
    plugin_id: str,
    author: str = "Lumina User",
    category: str = "feature",
    target_dir: str = None
):
    """Create a new plugin from template"""
    
    # Validate plugin ID
    if not plugin_id or not plugin_id.replace(".", "").replace("_", "").replace("-", "").isalnum():
        print(f"❌ Invalid plugin ID: {plugin_id}")
        print("   Use lowercase letters, numbers, dots, underscores, or hyphens")
        return False
    
    # Determine target directory
    if target_dir:
        base_dir = Path(target_dir)
    else:
        # Default to plugins/extensions
        script_dir = Path(__file__).parent
        base_dir = script_dir.parent / "plugins" / "extensions"
    
    # Create plugin directory name (last part of ID)
    dir_name = plugin_id.split(".")[-1].replace("-", "_")
    plugin_dir = base_dir / dir_name
    
    if plugin_dir.exists():
        print(f"❌ Plugin directory already exists: {plugin_dir}")
        return False
    
    # Generate names
    class_name = to_class_name(dir_name) + "Manager"
    plugin_name = to_plugin_name(dir_name)
    service_name = dir_name.replace("-", "_")
    
    # Create directory
    plugin_dir.mkdir(parents=True)
    print(f"📁 Created: {plugin_dir}")
    
    # Create manifest.yaml
    manifest_content = MANIFEST_TEMPLATE.format(
        plugin_id=plugin_id,
        plugin_name=plugin_name,
        class_name=class_name,
        author=author,
        category=category
    )
    (plugin_dir / "manifest.yaml").write_text(manifest_content, encoding="utf-8")
    print(f"📄 Created: manifest.yaml")
    
    # Create manager.py
    manager_content = MANAGER_TEMPLATE.format(
        plugin_id=plugin_id,
        plugin_name=plugin_name,
        class_name=class_name,
        service_name=service_name
    )
    (plugin_dir / "manager.py").write_text(manager_content, encoding="utf-8")
    print(f"📄 Created: manager.py")
    
    # Create README.md
    readme_content = README_TEMPLATE.format(
        plugin_id=plugin_id,
        plugin_name=plugin_name
    )
    (plugin_dir / "README.md").write_text(readme_content, encoding="utf-8")
    print(f"📄 Created: README.md")
    
    # Create __init__.py
    (plugin_dir / "__init__.py").write_text("", encoding="utf-8")
    print(f"📄 Created: __init__.py")
    
    print()
    print(f"✅ Plugin created successfully!")
    print()
    print(f"Next steps:")
    print(f"  1. Edit {plugin_dir / 'manifest.yaml'} to update metadata")
    print(f"  2. Implement your logic in {plugin_dir / 'manager.py'}")
    print(f"  3. Restart backend to load the plugin")
    print()
    print(f"Useful commands:")
    print(f"  # Hot reload during development")
    print(f"  curl -X POST http://localhost:8010/plugins/reload/{plugin_id}")
    print()
    
    return True


def main():
    parser = argparse.ArgumentParser(
        description="Create a new Lumina plugin from template",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python create_plugin.py my_awesome_plugin
  python create_plugin.py my_company.my_plugin --author "John Doe"
  python create_plugin.py tts_driver --category system
        """
    )
    
    parser.add_argument(
        "plugin_id",
        help="Plugin ID (e.g., 'my_plugin' or 'my_company.my_plugin')"
    )
    parser.add_argument(
        "--author",
        default="Lumina User",
        help="Author name for manifest (default: 'Lumina User')"
    )
    parser.add_argument(
        "--category",
        choices=["system", "feature", "integration", "driver"],
        default="feature",
        help="Plugin category (default: 'feature')"
    )
    parser.add_argument(
        "--target",
        help="Target directory (default: plugins/extensions)"
    )
    
    args = parser.parse_args()
    
    success = create_plugin(
        plugin_id=args.plugin_id,
        author=args.author,
        category=args.category,
        target_dir=args.target
    )
    
    sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()
