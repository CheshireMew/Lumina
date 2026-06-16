"""
STT Service Global State.

Used to share state between Lifecycle and Routers.
These are singleton references initialized during STT Capability startup.
"""
import queue
from typing import Dict, Any

# Audio Manager (Singleton)
# Initialized in STT Capability on_startup
audio_manager: Any = None 

# WebSocket Connections
active_websockets: Dict[str, Any] = {}

# Message Queue for VAD/Speech Events
# Thread-safe queue for communicating between AudioCallback and WebSocket Loop
message_queue: queue.Queue = queue.Queue(maxsize=500)

# Audio Filter Chain
# Provider extensions register filters here to intercept audio before STT
# Initialized in STT Capability on_startup
filter_chain: Any = None
