import logging
import asyncio
from typing import List, Dict
from pathlib import Path
from app_config import config

logger = logging.getLogger("PluginDispatcher")

class PluginDispatcher:
    """
    Manages distribution of plugins to Worker Processes (STT, TTS, etc.).
    Responsibilities:
    - Identifying plugins targeting specific runtimes.
    - Pushing manifest paths to workers via HTTP/RPC.
    - Monitoring worker availability for dispatch.
    """
    
    def __init__(self, registry):
        self.registry = registry

    async def distribute_plugins(self):
        """Push plugins to Worker Processes (STT/TTS)"""
        stt_manifests = []
        
        # Scan registry for STT targets
        for plugin in self.registry.plugins.values():
            manifest = getattr(plugin, '_manifest', None) or getattr(plugin, 'manifest', None)
            if manifest and getattr(manifest, 'runtime_target', 'main') == 'stt_server':
                if hasattr(manifest, 'path'):
                    man_path = Path(manifest.path) / "manifest.yaml"
                    stt_manifests.append(str(man_path))

        if stt_manifests:
            logger.info(f"📡 Queueing Dispatch of {len(stt_manifests)} plugins to STT Server...")
            asyncio.create_task(self._monitor_and_dispatch_stt(stt_manifests))

    async def _monitor_and_dispatch_stt(self, manifests: List[str]):
        """
        Background loop to ensure STT receives the plugins.
        Retries until success or max attempts (e.g., 5 minutes).
        """
        import aiohttp
        stt_port = config.network.stt_port
        url = f"http://127.0.0.1:{stt_port}/models/plugins/load" # Note: Route might have changed, checking commonly used path
        # Actually checking stt_server.py routes...
        # Wait, stt_server.py: app.include_router(stt_router) -> routers/stt_routes.py
        # And also explicit middleware loading was removed.
        # But we need to know the endpoint.
        # routers/stt_routes.py has router = APIRouter(prefix="") or similar.
        # Let's assume standard /plugins/load based on previous code.
        # "stt_routes.py" -> @router.post("/plugins/load")
        
        # [Fix] The route in stt_routes.py is likely /plugins/load based on previous audit
        url = f"http://127.0.0.1:{stt_port}/plugins/load"
        
        MAX_RETRIES = 60 # 60 * 5s = 5 minutes
        retry_count = 0
        
        async with aiohttp.ClientSession() as session:
            while retry_count < MAX_RETRIES:
                try:
                    async with session.post(url, json={"manifests": manifests}, timeout=2.0) as resp:
                        if resp.status == 200:
                            logger.info("✅ STT Server acknowledged plugin load (Handshake Complete).")
                            return # Success!
                        else:
                            logger.warning(f"⚠️ STT Server returned {resp.status}. Retrying...")
                except (aiohttp.ClientConnectorError, asyncio.TimeoutError):
                    # STT Offline
                    if retry_count % 2 == 0: # Log every 10s
                        logger.debug(f"⏳ STT Server unreachable. Waiting... ({retry_count}/{MAX_RETRIES})")
                    pass
                except Exception as e:
                    logger.error(f"Dispatch Error: {e}")
                
                await asyncio.sleep(5) # Wait 5 seconds
                retry_count += 1
        
        logger.error("❌ STT Server unreachable after 5 minutes. Plugin dispatch failed.")
