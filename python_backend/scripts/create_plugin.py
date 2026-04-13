#!/usr/bin/env python
"""Create a plugin scaffold using the unified contract."""

import argparse
import sys
from pathlib import Path


MANIFEST_TEMPLATE = """id: "{plugin_id}"
api_version: "1.0"
kind: "{kind}"
capability: "{capability}"
runtime_target: "main"
permissions: []
config_schema: {{}}
provides: []
"""

PLUGIN_TEMPLATE = """import logging

from core.interfaces.plugin import Plugin as BasePlugin

logger = logging.getLogger("{logger_name}")


class Plugin(BasePlugin):
    async def load(self, context):
        await super().load(context)

    async def enable(self):
        await super().enable()
        logger.info("Enabled {plugin_name}")

    async def disable(self):
        await super().disable()

    async def unload(self):
        await super().unload()

    def get_metadata(self):
        metadata = super().get_metadata()
        metadata.update(
            {{
                "name": "{plugin_name}",
                "description": "TODO: Describe what this plugin does",
                "func_tag": "{func_tag}",
            }}
        )
        return metadata
"""


def to_plugin_name(plugin_id: str) -> str:
    parts = plugin_id.replace("-", " ").replace(".", " ").replace("_", " ").split()
    return " ".join(word.capitalize() for word in parts)


def create_plugin(plugin_id: str, kind: str, capability: str, target_dir: str | None = None) -> bool:
    if not plugin_id or not plugin_id.replace(".", "").replace("_", "").replace("-", "").isalnum():
        print(f"Invalid plugin ID: {plugin_id}")
        return False

    base_dir = Path(target_dir) if target_dir else Path(__file__).resolve().parent.parent / "plugins" / "extensions"
    plugin_dir = base_dir / plugin_id.split(".")[-1].replace("-", "_")
    if plugin_dir.exists():
        print(f"Plugin directory already exists: {plugin_dir}")
        return False

    plugin_dir.mkdir(parents=True)
    plugin_name = to_plugin_name(plugin_id)

    (plugin_dir / "manifest.yaml").write_text(
        MANIFEST_TEMPLATE.format(plugin_id=plugin_id, kind=kind, capability=capability),
        encoding="utf-8",
    )
    (plugin_dir / "plugin.py").write_text(
        PLUGIN_TEMPLATE.format(
            logger_name=plugin_id,
            plugin_name=plugin_name,
            func_tag=kind.title(),
        ),
        encoding="utf-8",
    )
    print(f"Plugin created at {plugin_dir}")
    return True


def main():
    parser = argparse.ArgumentParser(description="Create a Lumina plugin scaffold")
    parser.add_argument("plugin_id")
    parser.add_argument("--kind", choices=["provider", "extension", "gateway", "processor"], default="extension")
    parser.add_argument("--capability", default="chat.post_processor")
    parser.add_argument("--target")
    args = parser.parse_args()
    sys.exit(0 if create_plugin(args.plugin_id, args.kind, args.capability, args.target) else 1)


if __name__ == "__main__":
    main()
