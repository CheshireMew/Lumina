import logging
from typing import Any, Dict, List, Optional

try:
    import sounddevice as sd
except ModuleNotFoundError:
    sd = None

logger = logging.getLogger(__name__)


class AudioDeviceSelector:
    def __init__(self, sample_rate: int, frame_size: int):
        self.sample_rate = sample_rate
        self.frame_size = frame_size

    def list_input_devices(self, check_available: bool = False) -> List[Dict[str, Any]]:
        devices: List[Dict[str, Any]] = []
        if sd is None:
            logger.warning("sounddevice is not installed; audio input devices are unavailable.")
            return devices

        try:
            device_list = sd.query_devices()
            for index, device in enumerate(device_list):
                if device["max_input_channels"] <= 0:
                    continue

                if check_available and not self._can_open_device(index):
                    continue

                hostapi_name = sd.query_hostapis(device["hostapi"])["name"]
                devices.append(
                    {
                        "index": index,
                        "name": device["name"],
                        "channels": device["max_input_channels"],
                        "sample_rate": int(device["default_samplerate"]),
                        "hostapi": hostapi_name,
                        "host_api": device["hostapi"],
                    }
                )

            logger.info(f"Found {len(devices)} audio input devices.")
        except Exception as e:
            logger.error(f"Device enumeration failed: {e}")

        return devices

    def select_by_name(self, device_name: str) -> Optional[Dict[str, Any]]:
        for device in self.list_input_devices(check_available=True):
            if device["name"] == device_name:
                return device
        return None

    def select_by_index(self, device_index: int) -> Optional[Dict[str, Any]]:
        for device in self.list_input_devices(check_available=True):
            if device["index"] == device_index:
                return device
        return None

    def get_device_info(self, device_index: int):
        return self._require_sounddevice().query_devices(device_index)

    def create_input_stream(self, device_index, callback):
        sounddevice = self._require_sounddevice()
        return sounddevice.InputStream(
            device=device_index,
            samplerate=16000,
            channels=1,
            dtype="float32",
            blocksize=self.frame_size,
            callback=callback,
        )

    def _can_open_device(self, device_index: int) -> bool:
        if sd is None:
            return False
        try:
            test_stream = sd.InputStream(
                device=device_index,
                channels=1,
                samplerate=self.sample_rate,
                blocksize=self.frame_size,
                dtype="float32",
            )
            test_stream.close()
            return True
        except Exception as e:
            try:
                device = sd.query_devices(device_index)
                logger.debug(f"Skipping device {device_index} ({device['name']}): {e}")
            except Exception:
                logger.debug(f"Skipping device {device_index}: {e}")
            return False

    def _require_sounddevice(self):
        if sd is None:
            raise RuntimeError("sounddevice is required for audio capture but is not installed.")
        return sd
