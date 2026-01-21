
# STT Service Global State
# Used to share state between Lifecycle (stt_server.py) and Routers (routers/stt_routes.py)

import queue
from typing import Dict, Any, Optional

# Audio Manager (Singleton)
# Initialized in stt_server.startup_event
audio_manager: Any = None 

# WebSocket Connections
active_websockets: Dict[str, Any] = {}

# Message Queue for VAD/Speech Events
# Thread-safe queue for communicating between AudioCallback and WebSocket Loop
message_queue = queue.Queue()

# Voiceprint Manager (Singleton)
voiceprint_manager: Any = None
