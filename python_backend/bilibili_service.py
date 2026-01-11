import asyncio
import logging
import random
from typing import Optional

import blivedm
import blivedm.models.web as b_models # [FIX] Import models
from soul_manager import SoulManager

# Configure logging
logger = logging.getLogger("BilibiliService")

class BilibiliService:
    """
    Service to monitor Bilibili Live Danmaku and trigger Soul interactions.
    """
    def __init__(self, soul_manager: SoulManager, room_id: int):
        self.soul = soul_manager
        self.room_id = room_id
        self.client: Optional[blivedm.BLiveClient] = None
        self.running = False
        self.task: Optional[asyncio.Task] = None
        
        # Rate Limiting
        self.last_handled_time = 0
        self.cooldown_seconds = 5.0 # Minimum seconds between danmaku responses
        self.enabled = False 

    async def start(self):
        """Starts the Bilibili monitoring task."""
        if self.running: return
        
        # Check settings
        config = self.soul.config.get("bilibili", {})
        self.enabled = config.get("enabled", False)
        self.room_id = int(config.get("room_id", self.room_id))
        
        if not self.enabled or not self.room_id:
            logger.info("Bilibili Service disabled or missing Room ID.")
            return

        self.running = True
        logger.info(f"Starting Bilibili Service for Room {self.room_id}...")
        
        self.client = blivedm.BLiveClient(self.room_id, ssl=True)
        handler = DanmakuHandler(self)
        self.client.add_handler(handler)
        
        self.client.start()
        
        # Keep client alive in background
        # Note: blivedm's client.start() is non-blocking (it creates tasks)
        # But we need to keep a ref to ensure it runs or use join()
        # Actually client.start() just launches the connection task.
        # We should probably wait on it or keep the service alive.
        # Since this is running in FastAPI lifespan, we just hold the ref.
        
    async def stop(self):
        """Stops the service."""
        if self.client:
            await self.client.stop()
        self.running = False
        logger.info("Bilibili Service Stopped.")

    def handle_danmaku(self, user: str, content: str):
        """
        Called by Handler when a valid danmaku is received.
        Decides whether to trigger the AI.
        """
        import time
        now = time.time()
        
        # 1. Cooldown Check
        if now - self.last_handled_time < self.cooldown_seconds:
            # Drop it (or maybe queue it? For now, drop to keep it real-time)
            return

        # 2. Trigger Soul
        logger.info(f"🎥 [Bilibili] {user}: {content}")
        
        data = {
            "platform": "bilibili",
            "user": user,
            "content": content
        }
        
        # Set pending interaction with 'bilibili_danmaku' reason
        self.soul.set_pending_interaction(
            True, 
            reason="bilibili_danmaku",
            data=data
        )
        
        self.last_handled_time = now


class DanmakuHandler(blivedm.BaseHandler):
    def __init__(self, service: BilibiliService):
        self.service = service

    async def _on_danmaku(self, client: blivedm.BLiveClient, message: b_models.DanmakuMessage):
        # Filter spam/emojis if needed?
        # For now, pass everything
        self.service.handle_danmaku(message.uname, message.msg)

    async def _on_gift(self, client: blivedm.BLiveClient, message: b_models.GiftMessage):
        # Optional: React to gifts!
        if message.num >= 1:
            content =f"(Sent Gift: {message.gift_name} x{message.num})"
            self.service.handle_danmaku(message.uname, content)
