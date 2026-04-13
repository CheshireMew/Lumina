import argparse
from pathlib import Path


MANIFEST_TEMPLATE = """id: "{plugin_id}"
api_version: "1.0"
kind: "{kind}"
capability: "{capability}"
runtime_target: "{runtime_target}"
permissions: []
config_schema: {{}}
provides: []
"""

PLUGIN_TEMPLATE = """import logging

from core.interfaces.plugin import Plugin as BasePlugin

logger = logging.getLogger("{plugin_id}")


class Plugin(BasePlugin):
    async def load(self, context):
        await super().load(context)

    async def enable(self):
        await super().enable()
        logger.info("Enabled {plugin_id}")

    async def disable(self):
        await super().disable()

    async def unload(self):
        await super().unload()

    def get_metadata(self):
        metadata = super().get_metadata()
        metadata.update(
            {{
                "name": "{plugin_name}",
                "description": "{description}",
                "func_tag": "{func_tag}",
            }}
        )
        return metadata
"""


def to_plugin_name(plugin_id: str) -> str:
    parts = plugin_id.replace("-", " ").replace(".", " ").replace("_", " ").split()
    return " ".join(word.capitalize() for word in parts)


def create_scaffold(
    plugin_id: str,
    kind: str,
    capability: str,
    runtime_target: str,
    description: str,
    target_root: str | None = None,
) -> Path:
    root = Path(target_root) if target_root else Path(__file__).resolve().parent.parent / "plugins" / "extensions"
    plugin_dir = root / plugin_id.split(".")[-1].replace("-", "_")
    if plugin_dir.exists():
        raise FileExistsError(f"Plugin directory already exists: {plugin_dir}")

    plugin_dir.mkdir(parents=True)
    plugin_name = to_plugin_name(plugin_id)

    (plugin_dir / "manifest.yaml").write_text(
        MANIFEST_TEMPLATE.format(
            plugin_id=plugin_id,
            kind=kind,
            capability=capability,
            runtime_target=runtime_target,
        ),
        encoding="utf-8",
    )
    (plugin_dir / "plugin.py").write_text(
        PLUGIN_TEMPLATE.format(
            plugin_id=plugin_id,
            plugin_name=plugin_name,
            description=description,
            func_tag=kind.title(),
        ),
        encoding="utf-8",
    )
    return plugin_dir


def main():
    parser = argparse.ArgumentParser(description="Scaffold a unified Lumina plugin")
    parser.add_argument("plugin_id")
    parser.add_argument("--kind", choices=["provider", "extension", "gateway", "processor"], default="extension")
    parser.add_argument("--capability", default="chat.post_processor")
    parser.add_argument("--runtime-target", default="main")
    parser.add_argument("--description", default="TODO: Describe what this plugin does")
    parser.add_argument("--target-root")
    args = parser.parse_args()

    created = create_scaffold(
        plugin_id=args.plugin_id,
        kind=args.kind,
        capability=args.capability,
        runtime_target=args.runtime_target,
        description=args.description,
        target_root=args.target_root,
    )
    print(f"Plugin scaffold created at {created}")


if __name__ == "__main__":
    main()
