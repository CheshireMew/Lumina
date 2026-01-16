import re
import logging
import asyncio
from typing import Dict, Optional

from core.interfaces.plugin import BaseSystemPlugin
from core.protocol import EventPacket, EventType
from .vmc_protocol import VMCClient

logger = logging.getLogger("AvatarServer")

class AvatarServerPlugin(BaseSystemPlugin):
    """
    Passive Avatar Driver.
    Listens to BRAIN_RESPONSE and extracts emotion tags.
    Broadcasts to VMC (OSC) and Frontend (WebSocket).
    """

    @property
    def id(self) -> str:
        return "system.avatar_server"

    @property
    def name(self) -> str:
        return "Avatar Driver (VMC)"

    @property
    def description(self) -> str:
        return "Synchronizes AI emotions with VMC-compatible avatars and Live2D models."

    def __init__(self):
        super().__init__()
        self.vmc_client: Optional[VMCClient] = None
        self.mappings: Dict[str, str] = {}
        # Regex to capture [emotion] or (emotion)
        self.tag_pattern = re.compile(r'[\[\(](joy|sad|angry|surprised|neutral|thinking)[\]\)]', re.IGNORECASE)

    async def initialize(self, context):
        super().initialize(context)
        
        # Load Config
        vmc_ip = self.config.get("vmc_ip", "127.0.0.1")
        vmc_port = self.config.get("vmc_port", 39539)
        self.mappings = self.config.get("mappings", {})
        
        # Init Client
        self.vmc_client = VMCClient(ip=vmc_ip, port=vmc_port)
        
        # Subscribe to Brain Response (Stream)
        # Note: We listen to the RAW stream chunks. 
        # Ideally, we should listen to a "sentence_end" event or process chunks statefully.
        # For this MVP, we scan chunks. Tag splitting across chunks is a known edge case.
        if hasattr(self.context, 'bus'):
            self.context.bus.subscribe(EventType.BRAIN_RESPONSE, self.handle_brain_response)
        
        logger.info(f"馃幁 Avatar Driver Listening via OSC on {vmc_ip}:{vmc_port}")

    async def handle_brain_response(self, event):
        """
        Process text chunks for emotion tags.
        """
        # Unwrap Event wrapper
        packet = event.data
        if not packet or not hasattr(packet, "payload"): return

        content = packet.payload.get("content", "")

        # Simple Scan
        matches = self.tag_pattern.findall(content)
        for match in matches:
            emotion = match.lower()
            logger.info(f"鉁?Detected Emotion Tag: {emotion}")
            
            # 1. Drive VMC (External)
            if self.vmc_client:
                self.vmc_client.send_emotion(emotion, self.mappings)
            
            # 2. Drive Frontend (Internal)
            # If "sync_frontend" is true, we emit a dedicated event
            # so the Frontend doesn't HAVE to parse text anymore.
            if self.config.get("sync_frontend", True):
                await self.context.bus.emit(EventPacket(
                    session_id=packet.session_id,
                    type="avatar.emotion",
                    source=self.id,
                    payload={"emotion": emotion, "provider": "vmc_mirror"}
                ))

    def scan_models(self) -> list:
        """
        Scan for available avatars (Live2D, VRM, Sprites).
        Returns list of {name, path, type, thumbnail}.
        """
        from app_config import config, IS_FROZEN
        from pathlib import Path
        import os

        # Root paths
        if IS_FROZEN:
             public_root = config.base_dir / "public"
        else:
             public_root = config.base_dir.parent / "public"

        if not public_root.exists():
            logger.warning(f"Public directory not found: {public_root}")
            return []

        models = []
        
        # Helper to find thumbnail
        def find_thumbnail(model_path: Path) -> Optional[str]:
            # Priority: thumbnail.png/jpg -> preview.png/jpg -> model_name.png/jpg
            candidates = [
                "thumbnail.png", "thumbnail.jpg",
                "preview.png", "preview.jpg",
                f"{model_path.stem}.png", f"{model_path.stem}.jpg",
                "icon.png"
            ]
            
            parent = model_path.parent
            for cand in candidates:
                thumb_file = parent / cand
                if thumb_file.exists():
                    try:
                        rel = thumb_file.relative_to(public_root)
                        return f"/{rel.as_posix()}"
                    except ValueError:
                        continue
            return None

        # 1. Scan Live2D (.model3.json)
        live2d_root = public_root / "live2d"
        if live2d_root.exists():
            for root, dirs, files in os.walk(live2d_root):
                for file in files:
                    if file.endswith(".model3.json"):
                        try:
                            abs_path = Path(root) / file
                            rel_path = abs_path.relative_to(public_root)
                            web_path = f"/{rel_path.as_posix()}"
                            
                            name = abs_path.parent.name
                            if name == "imported": name = file.replace(".model3.json", "")
                            
                            models.append({
                                "name": name,
                                "path": web_path,
                                "type": "live2d",
                                "thumbnail": find_thumbnail(abs_path)
                            })
                        except Exception as e:
                            logger.warn(f"Error processing Live2D {file}: {e}")

        # 2. Scan VRM (.vrm)
        vrm_root = public_root / "vrm"
        if vrm_root.exists():
            for root, dirs, files in os.walk(vrm_root):
                for file in files:
                    if file.endswith(".vrm"):
                        try:
                            abs_path = Path(root) / file
                            rel_path = abs_path.relative_to(public_root)
                            web_path = f"/{rel_path.as_posix()}"
                            
                            models.append({
                                "name": file.replace(".vrm", ""),
                                "path": web_path,
                                "type": "vrm",
                                "thumbnail": find_thumbnail(abs_path)
                            })
                        except Exception: pass

        # 3. Scan Sprites (custom convention: folders in public/sprites)
        sprites_root = public_root / "sprites"
        if sprites_root.exists():
             for entry in sprites_root.iterdir():
                 if entry.is_dir():
                     # Check for main image
                     candidates = ["default.png", "normal.png", "stand.png"]
                     main_sprite = None
                     for c in candidates:
                         if (entry / c).exists():
                             main_sprite = entry / c
                             break
                     
                     if main_sprite:
                         try:
                             web_path = f"/{main_sprite.relative_to(public_root).as_posix()}"
                             models.append({
                                 "name": entry.name,
                                 "path": web_path,
                                 "type": "sprite",
                                 "thumbnail": find_thumbnail(main_sprite) or web_path # Use itself as thumb
                             })
                         except: pass

        return sorted(models, key=lambda x: x['name'])
