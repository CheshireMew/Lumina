from collections import deque
from dataclasses import dataclass
from typing import List, Optional

import numpy as np

try:
    import webrtcvad
except ModuleNotFoundError:
    webrtcvad = None


DEFAULT_SPEECH_END_THRESHOLD = 0.15


@dataclass
class VADResult:
    status: str
    audio_data: Optional[np.ndarray] = None


class VADProcessor:
    def __init__(
        self,
        sample_rate: int = 16000,
        frame_duration_ms: int = 30,
        aggressiveness: int = 3,
        window_size: int = 15,
        speech_start_threshold: float = 0.8,
        speech_end_threshold: float = DEFAULT_SPEECH_END_THRESHOLD,
        min_speech_frames: int = 15,
    ):
        self.sample_rate = sample_rate
        self.frame_duration_ms = frame_duration_ms
        self.frame_size = int(sample_rate * frame_duration_ms / 1000)
        self.aggressiveness = aggressiveness
        self.window_size = window_size
        self.speech_start_threshold = speech_start_threshold
        self.speech_end_threshold = self._normalize_end_threshold(speech_end_threshold)
        self.min_speech_frames = min_speech_frames

        self.vad = webrtcvad.Vad(aggressiveness) if webrtcvad else None
        self.speech_buffer = deque(maxlen=self.window_size)
        pre_buffer_frames = int(0.5 * 1000 / frame_duration_ms)
        self.max_speech_frames = int(20 * 1000 / frame_duration_ms)
        self.pre_buffer = deque(maxlen=pre_buffer_frames)
        self.audio_frames: List[np.ndarray] = []
        self.is_speaking = False

    def update_params(
        self,
        start_threshold: Optional[float] = None,
        end_threshold: Optional[float] = None,
        min_frames: Optional[int] = None,
        aggressiveness: Optional[int] = None,
    ) -> None:
        if aggressiveness is not None:
            self.update_aggressiveness(aggressiveness)
        if start_threshold is not None:
            self.speech_start_threshold = max(0.1, min(1.0, start_threshold))
        if end_threshold is not None:
            self.speech_end_threshold = self._normalize_end_threshold(end_threshold)
        if min_frames is not None:
            self.min_speech_frames = max(5, min(100, min_frames))

    def update_aggressiveness(self, aggressiveness: int) -> None:
        self.aggressiveness = max(0, min(3, int(aggressiveness)))
        if self.vad is not None:
            self.vad.set_mode(self.aggressiveness)

    def _normalize_end_threshold(self, value: float) -> float:
        min_threshold = (1 / self.window_size) + 0.001
        return max(min_threshold, min(1.0, value))

    def process_frame(self, frame: np.ndarray) -> VADResult:
        rms = np.sqrt(np.mean(frame**2))

        if self.vad is None:
            is_speech = rms >= 0.01
        else:
            pcm = (frame.clip(-1, 1) * 32767).astype(np.int16).tobytes()
            try:
                is_speech = self.vad.is_speech(pcm, self.sample_rate)
            except Exception:
                is_speech = False

        if rms < 0.001:
            is_speech = False

        self.speech_buffer.append(is_speech)
        speech_ratio = (
            sum(self.speech_buffer) / len(self.speech_buffer)
            if self.speech_buffer
            else 0
        )

        if not self.is_speaking and speech_ratio > self.speech_start_threshold:
            self.is_speaking = True
            self.audio_frames.extend(list(self.pre_buffer))
            self.audio_frames.append(frame)
            return VADResult("speech_start")

        if self.is_speaking and speech_ratio < self.speech_end_threshold:
            if len(self.audio_frames) < self.min_speech_frames:
                self.is_speaking = False
                self.audio_frames.clear()
                return VADResult("silence")

            self.is_speaking = False
            audio_data = (
                np.concatenate(self.audio_frames)
                if self.audio_frames
                else np.array([])
            )
            self.audio_frames.clear()
            return VADResult("speech_end", audio_data)

        if self.is_speaking:
            self.audio_frames.append(frame)
            if len(self.audio_frames) >= self.max_speech_frames:
                self.is_speaking = False
                audio_data = np.concatenate(self.audio_frames)
                self.audio_frames.clear()
                return VADResult("speech_end", audio_data)
            return VADResult("speech_continue")

        self.pre_buffer.append(frame)
        return VADResult("silence")

    def reset(self) -> None:
        self.is_speaking = False
        self.audio_frames.clear()
        self.pre_buffer.clear()
        self.speech_buffer.clear()
