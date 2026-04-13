
# TTS Service Global State

import httpx
from typing import Any, Optional

# HTTP Client for external API calls (e.g. EdgeTTS if needed, or other drivers)
# Initialized in on_startup
http_client: Optional[httpx.AsyncClient] = None

# TTS Manager for this worker runtime
tts_manager: Any = None
