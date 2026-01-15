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

    async def handle_brain_response(self, event: EventPacket):
        """
        Process text chunks for emotion tags.
        """
        content = event.payload.get("content", "")
        if not content: return

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
                    type="avatar.emotion",
                    source=self.id,
                    payload={"emotion": emotion, "provider": "vmc_mirror"}
                ))

    def scan_models(self) -> list:
        """
        Scan for available Live2D models in the public/live2d directory.
        Returns a list of {name, path} dicts.
        """
        from app_config import config, IS_FROZEN
        from pathlib import Path
        import os

        # Resolve public/live2d path
        if IS_FROZEN:
             # In packaged app, it's likely alongside the executable or in resources
             # Adjust based on actual electron builder config
             live2d_root = config.base_dir / "public" / "live2d"
             if not live2d_root.exists():
                 # Fallback to ../public/live2d relative to backend in some builds
                 live2d_root = config.base_dir.parent / "public" / "live2d"
        else:
             # Dev mode: Project Root / public / live2d
             live2d_root = config.base_dir.parent / "public" / "live2d"

        if not live2d_root.exists():
            logger.warning(f"Live2D directory not found: {live2d_root}")
            return []

        models = []
        try:
            # Recursive scan for .model3.json
            for root, dirs, files in os.walk(live2d_root):
                for file in files:
                    if file.endswith(".model3.json"):
                        abs_path = Path(root) / file
                        # Create web-accessible path (relative to public)
                        # e.g. /live2d/Hiyori/Hiyori.model3.json
                        try:
                            rel_path = abs_path.relative_to(live2d_root.parent)
                            web_path = f"/{rel_path.as_posix()}" # Ensure forward slashes
                            
                            # Name strategy: Use parent folder name or file name
                            name = abs_path.parent.name
                            if name == "imported": # Edge case for flat structure
                                 name = file.replace(".model3.json", "")
                            
                            models.append({
                                "name": name,
                                "path": web_path
                            })
                        except ValueError:
                            continue
        except Exception as e:
            logger.error(f"Error scanning Live2D models: {e}")
            
        return sorted(models, key=lambda x: x['name'])
