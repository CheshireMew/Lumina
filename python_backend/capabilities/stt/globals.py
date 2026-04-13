
# STT Service Global State
# Used to share state between Lifecycle and Routers

import queue
from typing import Dict, Any

# Audio Manager (Singleton)
audio_manager: Any = None 

# STT Manager for this worker runtime
stt_manager: Any = None

# WebSocket Connections
active_websockets: Dict[str, Any] = {}

# Message Queue for VAD/Speech Events
message_queue = queue.Queue(maxsize=500)

# Voiceprint Manager (Singleton)
voiceprint_manager: Any = None
