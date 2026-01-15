import logging
import os
import sys
from typing import AsyncGenerator

# We need to import the existing GPTSoVITS wrapper from parent directory or utils
# Ideally we move the wrapper logic here, but it depends on 'GPT-SoVITS' folder structure.
# For now, we import the existing class from python_backend.tts_engine_gptsovits
# We assume python_backend is in path.

from core.interfaces.driver import BaseTTSDriver

logger = logging.getLogger("GPTSoVITSDriver")

class GPTSoVITSDriver(BaseTTSDriver):
    def __init__(self):
        super().__init__(
            id="gpt-sovits",
            name="GPT-SoVITS (Local)",
            description="High fidelity, emotional local TTS. Requires GPU/CPU resources."
        )
        self.engine = None


    async def load(self):
        if self.engine: return
        
        # 0. Load Wrapper
        try:
            if "python_backend" not in sys.modules:
                sys.path.append(os.path.join(os.getcwd(), "python_backend"))
                
            from .gpt_sovits.engine import GPTSoVITSEngine
            logger.info("Initializing GPTSoVITSEngine...")
            self.engine = GPTSoVITSEngine()
        except ImportError as e:
            logger.error(f"Failed to load GPT-SoVITS Engine (Import Error): {e}")
            raise e
        except Exception as e:
            logger.error(f"Failed to initialize GPT-SoVITS Engine: {e}", exc_info=True)
            raise e

        # 1. Check Connection
        self.engine.check_connection()
        if self.engine.is_available:
            logger.info("GPT-SoVITS Service is ready.")
            return

        # 2. Auto-Launch
        # Import config locally to avoid circular dependency if any (though app_config should be safe)
        from app_config import config
        local_path = getattr(config.audio, "gpt_sovits_path", None)
        if local_path and os.path.exists(local_path):
             await self._launch_local_service(local_path)
             # Re-check
             self.engine.check_connection()
        else:
             logger.warning("GPT-SoVITS service unavailable and no local path configured.")

    async def _launch_local_service(self, root_path: str):
        logger.info(f"Launching GPT-SoVITS from {root_path}...")
        
        python_exe = os.path.join(root_path, "runtime", "python.exe")
        if not os.path.exists(python_exe):
            python_exe = sys.executable 
        
        script = "api.py"
        if os.path.exists(os.path.join(root_path, "api_v2.py")):
             script = "api_v2.py"
             
        cmd = [python_exe, script]
        # Force default settings for API (usually binds to 9880)
        
        try:
            subprocess.Popen(
                cmd, 
                cwd=root_path,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
                creationflags=subprocess.CREATE_NO_WINDOW if sys.platform == 'win32' else 0
            ) # Detached
            
            logger.info("Waiting for GPT-SoVITS service to warm up...")
            for i in range(30):
                await asyncio.sleep(2)
                if self._check_port_ready(self.engine.api_url):
                     logger.info("GPT-SoVITS Launched Successfully!")
                     return
            logger.error("GPT-SoVITS timed out during startup.")
        except Exception as e:
            logger.error(f"Failed to launch GPT-SoVITS: {e}")

    def _check_port_ready(self, url: str) -> bool:
         # Use sync httpx or requests inside async loop (brief blocking is acceptable here during startup)
         try:
             import requests
             return requests.get(url, timeout=0.5).status_code < 500
         except: return False

    def _parse_emotion_tags(self, text: str) -> tuple[str, str]:
        """
        Extracts emotion tags from text (e.g. "[happy] Hello")
        Returns: (clean_text, emotion)
        """
        import re
        emotion = None
        # 1. Extract first emotion tag
        match = re.search(r"\[([a-zA-Z0-9_-]+)\]", text)
        if match:
            emotion = match.group(1)
            
        # 2. Clean Text
        clean_text = re.sub(r"\[.*?\]", "", text)
        clean_text = re.sub(r"\(.*?\)", "", clean_text)
        clean_text = clean_text.replace("*", "").replace("_", "")
        clean_text = re.sub(r"\s+", " ", clean_text).strip()
        
        return clean_text, emotion

    async def _transcode_to_aac(self, pcm_iterator: AsyncGenerator[bytes, None], sample_rate=32000) -> AsyncGenerator[bytes, None]:
        """
        Stream Transcode: PCM (Stream) -> FFmpeg -> AAC (Stream)
        """
        cmd = [
            "ffmpeg", 
            "-f", "s16le", 
            "-ar", str(sample_rate), 
            "-ac", "1", 
            "-i", "pipe:0", 
            "-c:a", "aac", 
            "-b:a", "128k", 
            "-f", "adts", 
            "pipe:1"
        ]
        
        try:
            process = subprocess.Popen(
                cmd,
                stdin=subprocess.PIPE,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                bufsize=0
            )
        except Exception as e:
            logger.error(f"FFmpeg launch failed: {e}")
            return

        loop = asyncio.get_event_loop()
        
        async def writer():
            try:
                async for chunk in pcm_iterator:
                    if chunk:
                        await loop.run_in_executor(None, process.stdin.write, chunk)
                        await loop.run_in_executor(None, process.stdin.flush)
            except Exception as e:
                logger.debug(f"FFmpeg Writer error: {e}")
            finally:
                try:
                    await loop.run_in_executor(None, process.stdin.close)
                except Exception as e:
                    logger.debug(f"Error closing stdin: {e}")

        asyncio.create_task(writer())
        
        try:
            while True:
                # Read output in chunks
                chunk = await loop.run_in_executor(None, process.stdout.read, 4096)
                if not chunk: break
                yield chunk
        except Exception as e:
            logger.error(f"FFmpeg Reader error: {e}")
        finally:
            try:
                process.terminate()
                # process.wait() # Async wait ideally
            except Exception as e:
                logger.debug(f"Error terminating process: {e}")

    async def generate_stream(self, text: str, voice: str, **kwargs) -> AsyncGenerator[bytes, None]:
        if not self.engine:
            await self.load()
            
        # 1. Parse Emotion Tags (User Optimization Recovery)
        clean_text, detected_emotion = self._parse_emotion_tags(text)
        emotion = detected_emotion or kwargs.get("emotion") or "default"
        
        logger.info(f"Generating TTS: '{clean_text[:20]}...' [{emotion}]")

        # 2. Get Raw Stream from Engine (RAW -> AAC Transcoding)
        # We invoke synthesize with 'raw' to get PCM data, then use local FFmpeg to Encode to AAC
        # This matches the user's optimization for lower server CPU usage? Or lower latency?
        # User said: "璇锋眰 RAW (PCM) 鏍煎紡锛岄伩鍏?Server 绔?FFmpeg 浣庢晥"
        
        raw_iterator = self.engine.synthesize(
            text=clean_text,
            voice=voice,
            emotion=emotion,
            media_type="raw" # 鈿?Request RAW
        )
        
        # 3. Transcode Locally
        aac_stream = self._transcode_to_aac(raw_iterator, sample_rate=32000)
        
        async for chunk in aac_stream:
            yield chunk


