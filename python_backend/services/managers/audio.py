import logging
from typing import Callable, Dict, List, Optional

import numpy as np

from .audio_config_store import AudioConfigStore
from .audio_devices import AudioDeviceSelector
from .vad_processor import VADProcessor

logger = logging.getLogger(__name__)


class AudioManager:
    def __init__(
        self,
        sample_rate: int = 16000,
        frame_duration_ms: int = 30,
        aggressiveness: int = 3,
        on_speech_start: Optional[Callable] = None,
        on_speech_end: Optional[Callable[[np.ndarray], None]] = None,
        on_vad_status_change: Optional[Callable[[str], None]] = None,
    ):
        self.sample_rate = sample_rate
        self.frame_duration_ms = frame_duration_ms
        self.frame_size = int(sample_rate * frame_duration_ms / 1000)

        self.on_speech_start = on_speech_start
        self.on_speech_end = on_speech_end
        self.on_vad_status_change = on_vad_status_change

        self.config_store = AudioConfigStore()
        self.device_selector = AudioDeviceSelector(sample_rate, self.frame_size)
        self.vad_processor = VADProcessor(
            sample_rate=sample_rate,
            frame_duration_ms=frame_duration_ms,
            aggressiveness=aggressiveness,
        )

        self.is_running = False
        self.stream = None
        self.device_index: Optional[int] = None
        self.device_name: Optional[str] = None

        self._load_config()

    @property
    def is_speaking(self) -> bool:
        return self.vad_processor.is_speaking

    @is_speaking.setter
    def is_speaking(self, value: bool) -> None:
        self.vad_processor.is_speaking = value

    @property
    def speech_start_threshold(self) -> float:
        return self.vad_processor.speech_start_threshold

    @speech_start_threshold.setter
    def speech_start_threshold(self, value: float) -> None:
        self.vad_processor.speech_start_threshold = value

    @property
    def speech_end_threshold(self) -> float:
        return self.vad_processor.speech_end_threshold

    @speech_end_threshold.setter
    def speech_end_threshold(self, value: float) -> None:
        self.vad_processor.speech_end_threshold = value

    @property
    def min_speech_frames(self) -> int:
        return self.vad_processor.min_speech_frames

    @min_speech_frames.setter
    def min_speech_frames(self, value: int) -> None:
        self.vad_processor.min_speech_frames = value

    def _load_config(self) -> None:
        config = self.config_store.load()
        if not config:
            return

        self.device_name = config.get("device_name")
        self.speech_start_threshold = config.get("speech_start_threshold", 0.6)
        self.speech_end_threshold = config.get("speech_end_threshold", 0.05)
        self.min_speech_frames = config.get("min_speech_frames", 15)
        logger.info(
            "Loaded audio config: "
            f"Device={self.device_name}, "
            f"Start={self.speech_start_threshold}, "
            f"End={self.speech_end_threshold}"
        )

    def save_config(self) -> None:
        self.config_store.save(
            {
                "device_name": self.device_name,
                "speech_start_threshold": self.speech_start_threshold,
                "speech_end_threshold": self.speech_end_threshold,
                "min_speech_frames": self.min_speech_frames,
            }
        )

    def update_params(
        self,
        start_threshold: Optional[float] = None,
        end_threshold: Optional[float] = None,
        min_frames: Optional[int] = None,
    ) -> None:
        self.vad_processor.update_params(start_threshold, end_threshold, min_frames)
        self.save_config()
        logger.info(
            f"VAD params updated: Start={self.speech_start_threshold}, "
            f"End={self.speech_end_threshold}"
        )

    def list_devices(self) -> List[Dict]:
        return self.device_selector.list_input_devices(check_available=True)

    def set_device_by_name(self, device_name: str) -> bool:
        device = self.device_selector.select_by_name(device_name)
        if not device:
            logger.warning(f"Device not found: {device_name}")
            return False

        self.device_index = device["index"]
        self.device_name = device_name
        self.save_config()
        logger.info(f"Set audio device: {device_name} (Index: {self.device_index})")
        return True

    def set_device(self, device_index: int) -> bool:
        device = self.device_selector.select_by_index(device_index)
        if not device:
            logger.warning(f"Invalid device index: {device_index}")
            return False

        self.device_index = device_index
        self.device_name = device["name"]
        self.save_config()
        logger.info(f"Set audio device: {self.device_name} (Index: {device_index})")
        return True

    def switch_device(self, device_name: str) -> bool:
        was_running = self.is_running
        if was_running:
            logger.info("Hot-switching device: stopping current stream...")
            self.stop()

        success = self.set_device_by_name(device_name)

        if was_running and success:
            logger.info(f"Restarting stream with new device: {device_name}")
            self.start()
        elif was_running:
            logger.warning("Device switch failed, restarting with previous device")
            self.start()

        return success

    def _audio_callback(self, indata: np.ndarray, frames: int, time_info, status):
        if status and status.input_overflow:
            pass

        audio_frame = indata[:, 0].copy() if indata.ndim > 1 else indata.copy()
        result = self.vad_processor.process_frame(audio_frame)

        if result.status == "speech_start":
            self._notify_speech_start()
        elif result.status == "speech_end" and result.audio_data is not None:
            self._notify_speech_end(result.audio_data)

    def _notify_speech_start(self) -> None:
        if self.on_speech_start:
            try:
                self.on_speech_start()
            except Exception as e:
                logger.warning(f"on_speech_start callback failed: {e}")

        self._notify_vad_status("listening")

    def _notify_speech_end(self, audio_data: np.ndarray) -> None:
        if self.on_speech_end and len(audio_data) > 0:
            try:
                self.on_speech_end(audio_data)
            except Exception as e:
                logger.error(f"Error in on_speech_end callback: {e}", exc_info=True)

        self._notify_vad_status("idle")

    def _notify_vad_status(self, status: str) -> None:
        if not self.on_vad_status_change:
            return

        try:
            self.on_vad_status_change(status)
        except Exception as e:
            logger.debug(f"on_vad_status_change failed: {e}")

    def start(self) -> None:
        if self.is_running:
            logger.warning("Audio manager already running.")
            return

        if self.device_name and self.device_index is None:
            self.set_device_by_name(self.device_name)

        try:
            self._start_stream(self.device_index)
            self.is_running = True
            logger.info("Audio capture started.")
        except Exception as e:
            logger.error(f"Start capture failed: {e}", exc_info=True)
            self.is_running = False
            self.stream = None

            if "Invalid device" in str(e) or "PaErrorCode -9996" in str(e):
                self._start_default_device()

    def _start_stream(self, device_index: Optional[int]) -> None:
        if device_index is not None:
            device_info = self.device_selector.get_device_info(device_index)
            logger.info(f"Using Device: [{device_index}] {device_info['name']}")
            logger.info(f"Native Rate: {device_info['default_samplerate']} Hz")
            logger.info("Forcing 16000 Hz")
        else:
            logger.info("Using system default audio input device")

        logger.info(
            f"Starting capture (device={device_index}, "
            f"rate=16000, frame_size={self.frame_size})"
        )
        self.stream = self.device_selector.create_input_stream(
            device_index=device_index,
            callback=self._audio_callback,
        )
        self.stream.start()

    def _start_default_device(self) -> None:
        logger.warning("Device invalid, switching to default.")
        self.device_index = None
        self.device_name = None
        try:
            self._start_stream(None)
            self.is_running = True
            logger.info("Switched to system default device.")
        except Exception as e:
            logger.error(f"Default device also failed: {e}", exc_info=True)

    def stop(self) -> None:
        if not self.is_running:
            return

        try:
            logger.info("Stopping audio stream...")
            if self.stream:
                self.stream.stop()
                self.stream.close()
                self.stream = None

            self.is_running = False
            self.vad_processor.reset()
            logger.debug("Audio stream stopped and buffers cleared.")
        except Exception as e:
            logger.error(f"Stop capture failed: {e}", exc_info=True)

    def get_status(self) -> Dict:
        return {
            "is_running": self.is_running,
            "is_speaking": self.is_speaking,
            "device_name": self.device_name,
            "device_index": self.device_index,
            "sample_rate": self.sample_rate,
        }
