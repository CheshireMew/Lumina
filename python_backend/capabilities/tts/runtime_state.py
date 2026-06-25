from dataclasses import dataclass
from typing import Any


@dataclass
class TtsRuntimeState:
    tts_manager: Any = None

    def reset(self) -> None:
        self.tts_manager = None


_state = TtsRuntimeState()


def get_tts_runtime_state() -> TtsRuntimeState:
    return _state
