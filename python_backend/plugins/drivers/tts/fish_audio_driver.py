import os
import httpx
import logging
from typing import AsyncGenerator
from core.interfaces.driver import BaseTTSDriver
from app_config import config as app_settings

logger = logging.getLogger("FishAudioDriver")

class FishAudioDriver(BaseTTSDriver):
    def __init__(self):
        super().__init__("fish_audio", "Fish Audio", "Cloud/Local TTS")
        self.default_api_url = "https://api.fish.audio/v1"
        self.default_voice = "9546a36622834041b34a6a683cb0d065" # Default voice ID
        self.process = None

    async def load(self):
        # Check connectivity
        base_url = app_settings.audio.fish_audio_api_url
        if not base_url: base_url = self.default_api_url
        
        # 1. Ping Service
        if await self._is_service_ready(base_url):
            logger.info("Fish Audio Service is ready.")
            return

        # 2. If down, check for local path
        local_path = getattr(app_settings.audio, "fish_audio_path", None)
        if local_path and os.path.exists(local_path):
            await self._launch_local_service(local_path)
        else:
            logger.warning(f"Fish Audio service unavailable at {base_url} and no local path configured.")

    async def _is_service_ready(self, url: str) -> bool:
        try:
            # Simple health check or docs ping
            async with httpx.AsyncClient(timeout=2.0) as client:
                # Fish Audio Swagger/Docs usually at /docs or root
                resp = await client.get(url.replace("/v1", "/docs")) 
                return resp.status_code < 500
        except:
            return False

    async def _launch_local_service(self, root_path: str):
        logger.info(f"Launching Fish Audio from {root_path}...")
        
        # Command: python -m tools.api_server --listen 127.0.0.1:8080 ...
        # We assume user installed it in a venv or conda env available to system path?
        # OR we assume they pointed to the python executable?
        # Actually simplest is to assume they pointed to the project ROOT, 
        # and we use the SYSTEM python or efficient guess. 
        # BUT user might have a specific venv.
        
        # BETTER STRATEGY: 
        # If 'fish_audio_path' is a FOLDER, check for 'venv' or 'env' inside.
        # If 'fish_audio_path' is a FILE (python.exe), use that.
        
        cmd = []
        if os.path.isdir(root_path):
            # Try to find venv python
            venv_python = os.path.join(root_path, "venv", "Scripts", "python.exe")
            if os.path.exists(venv_python):
                 cmd = [venv_python]
            else:
                 cmd = [sys.executable] # Use current python?? Unlikely to have dependencies.
                 logger.warning("No venv found in Fish Audio folder. Using system python (risky).")
        elif os.path.isfile(root_path) and root_path.endswith("python.exe"):
            cmd = [root_path]
            root_path = os.path.dirname(os.path.dirname(root_path)) # infer root?
        
        if not cmd:
             logger.error("Could not determine python interpreter for Fish Audio.")
             return

        # Appending Server Args
        # python -m tools.api_server --listen 127.0.0.1:8080
        # We enforce localhost for security on auto-launch
        cmd.extend(["-m", "tools.api_server", "--listen", "127.0.0.1:8080"])
        
        try:
            # DETACHED PROCESS so it survives backend reload if possible? 
            # Or child process that dies with us. For now child.
            self.process = subprocess.Popen(
                cmd, 
                cwd=root_path,
                stdout=subprocess.DEVNULL, # Redirect logs to avoid clutter? or file?
                stderr=subprocess.DEVNULL,
                creationflags=subprocess.CREATE_NO_WINDOW if sys.platform == 'win32' else 0
            )
            
            # Wait for startup
            logger.info("Waiting for Fish Audio service to warm up...")
            for i in range(20):
                await asyncio.sleep(2)
                if await self._is_service_ready(self.default_api_url.replace("https://api.fish.audio", "http://127.0.0.1:8080")):
                    logger.info("Fish Audio Launched Successfully!")
                    # Update runtime config to use local
                    app_settings.audio.fish_audio_api_url = "http://127.0.0.1:8080/v1"
                    return
            
            logger.error("Fish Audio timed out during startup.")
        except Exception as e:
            logger.error(f"Failed to launch Fish Audio: {e}")

    async def generate_stream(self, text: str, voice: str, **kwargs) -> AsyncGenerator[bytes, None]:
        # Resolve Config (Runtime from Plugin Store or app_settings)
        # Note: In plugin system, we often stored config in self.config dict via `load_config`
        # But here we might read directly from app_settings if available, or fallback.
        
        # Check active settings
        # We assume PluginManager injects configuration or we look up global config.
        # Since we don't have a FishAudioConfig model yet, we might use generic kv or environment.
        
        # Configuration from ConfigManager (Single Source of Truth)
        api_key = app_settings.audio.fish_audio_api_key
        base_url = app_settings.audio.fish_audio_api_url or self.default_api_url
        
        # If running purely local, key might not be needed
        # but Cloud requires it.
        
        voice_id = voice if voice and len(voice) > 10 else self.default_voice
        
        url = f"{base_url}/tts"
        
        headers = {
            "Content-Type": "application/json"
        }
        if api_key:
            headers["Authorization"] = f"Bearer {api_key}"

        # Fish Audio Payload
        # Reference: https://docs.fish.audio/
        payload = {
            "text": text,
            "reference_id": voice_id,
            "format": "mp3",
            "latency": "normal"
        }
        
        # If local, format might differ slightly based on version? 
        # Assuming API compatibility with Cloud v1.
        
        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                async with client.stream("POST", url, json=payload, headers=headers) as response:
                    if response.status_code == 200:
                         async for chunk in response.aiter_bytes(chunk_size=4096):
                             yield chunk
                    else:
                        err_text = await response.read()
                        logger.error(f"Fish Audio Error {response.status_code}: {err_text.decode('utf-8', errors='ignore')}")
        except Exception as e:
            logger.error(f"Fish Audio Connection Failed: {e}")
            # Yield silence or raise?
            pass
