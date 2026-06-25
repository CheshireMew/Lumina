import queue
from dataclasses import dataclass, field
from typing import Any


@dataclass
class SttRuntimeState:
    audio_manager: Any = None
    stt_manager: Any = None
    active_websockets: dict[str, Any] = field(default_factory=dict)
    message_queue: queue.Queue = field(default_factory=lambda: queue.Queue(maxsize=500))
    voiceprint_manager: Any = None
    filter_chain: Any = None

    def reset(self) -> None:
        self.audio_manager = None
        self.stt_manager = None
        self.active_websockets.clear()
        self.voiceprint_manager = None
        self.filter_chain = None
        while not self.message_queue.empty():
            try:
                self.message_queue.get_nowait()
            except queue.Empty:
                break


_state = SttRuntimeState()


def get_stt_runtime_state() -> SttRuntimeState:
    return _state
