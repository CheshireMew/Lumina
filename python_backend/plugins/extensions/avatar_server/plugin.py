import logging
import os
import re
from pathlib import Path
from typing import Dict, Optional

from app_config import IS_FROZEN, config
from core.interfaces.plugin import Plugin as BasePlugin
from core.protocol import EventType

from .vmc_protocol import VMCClient

logger = logging.getLogger("AvatarServer")


class Plugin(BasePlugin):
    def __init__(self):
        super().__init__()
        self.vmc_client: Optional[VMCClient] = None
        self.mappings: Dict[str, str] = {}
        self.tag_pattern = re.compile(r"[\[\(](joy|sad|angry|surprised|neutral|thinking)[\]\)]", re.IGNORECASE)

    async def load(self, context):
        await super().load(context)
        vmc_ip = self.config.get("vmc_ip", "127.0.0.1")
        vmc_port = self.config.get("vmc_port", 39539)
        self.mappings = self.config.get("mappings", {})
        self.vmc_client = VMCClient(ip=vmc_ip, port=vmc_port)

    async def enable(self):
        await super().enable()
        self.context.subscribe(EventType.BRAIN_RESPONSE, self.handle_brain_response)

    async def disable(self):
        await super().disable()
        self.vmc_client = None

    async def handle_brain_response(self, event):
        packet = event.data
        if not packet or not hasattr(packet, "payload"):
            return
        content = packet.payload.get("content", "")
        for match in self.tag_pattern.findall(content):
            emotion = match.lower()
            if self.vmc_client:
                self.vmc_client.send_emotion(emotion, self.mappings)
            if self.config.get("sync_frontend", True):
                await self.context.emit("avatar.emotion", {"emotion": emotion, "provider": "vmc"})

    def scan_models(self) -> list[dict]:
        public_root = config.base_dir / "public" if IS_FROZEN else config.base_dir.parent / "public"
        if not public_root.exists():
            return []

        def find_thumbnail(model_path: Path) -> Optional[str]:
            for candidate in (
                "thumbnail.png",
                "thumbnail.jpg",
                "preview.png",
                "preview.jpg",
                f"{model_path.stem}.png",
                f"{model_path.stem}.jpg",
                "icon.png",
            ):
                thumb_file = model_path.parent / candidate
                if thumb_file.exists():
                    return f"/{thumb_file.relative_to(public_root).as_posix()}"
            return None

        seen_names = set()
        models: list[dict] = []

        def add_model(model_data: dict):
            if model_data["name"] in seen_names:
                return
            seen_names.add(model_data["name"])
            models.append(model_data)

        live2d_root = public_root / "live2d"
        if live2d_root.exists():
            for root, _dirs, files in os.walk(live2d_root):
                for file in files:
                    if not file.endswith(".model3.json"):
                        continue
                    abs_path = Path(root) / file
                    add_model(
                        {
                            "name": abs_path.parent.name if abs_path.parent.name != "imported" else file.replace(".model3.json", ""),
                            "path": f"/{abs_path.relative_to(public_root).as_posix()}",
                            "type": "live2d",
                            "thumbnail": find_thumbnail(abs_path),
                        }
                    )

        vrm_root = public_root / "vrm"
        if vrm_root.exists():
            for root, _dirs, files in os.walk(vrm_root):
                for file in files:
                    if not file.endswith(".vrm"):
                        continue
                    abs_path = Path(root) / file
                    add_model(
                        {
                            "name": file.replace(".vrm", ""),
                            "path": f"/{abs_path.relative_to(public_root).as_posix()}",
                            "type": "vrm",
                            "thumbnail": find_thumbnail(abs_path),
                        }
                    )

        sprites_root = public_root / "sprites"
        if sprites_root.exists():
            for entry in sprites_root.iterdir():
                if not entry.is_dir():
                    continue
                for candidate in ("default.png", "normal.png", "stand.png"):
                    main_sprite = entry / candidate
                    if main_sprite.exists():
                        add_model(
                            {
                                "name": entry.name,
                                "path": f"/{main_sprite.relative_to(public_root).as_posix()}",
                                "type": "sprite",
                                "thumbnail": find_thumbnail(main_sprite) or f"/{main_sprite.relative_to(public_root).as_posix()}",
                            }
                        )
                        break

        return sorted(models, key=lambda item: item["name"])

    def get_metadata(self) -> dict:
        metadata = super().get_metadata()
        metadata.update(
            {
                "name": "Avatar Server",
                "description": "Bridges chat emotion output into VMC avatars and frontend animation.",
                "func_tag": "Avatar",
            }
        )
        return metadata
