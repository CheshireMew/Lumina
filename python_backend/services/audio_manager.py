"""
Audio Manager - Backend VAD and Audio Capture
Based on Live2D-Virtual-Girlfriend architecture
Uses sounddevice + webrtcvad for precise device isolation and VAD detection
"""

import sounddevice as sd
import webrtcvad
import numpy as np
import logging
from collections import deque
from typing import Optional, Callable, Dict, List
import json

from app_config import CONFIG_ROOT

logger = logging.getLogger(__name__)

# Config file path
CONFIG_FILE = CONFIG_ROOT / "audio_config.json"


class AudioManager:
    """
    Audio Manager
    
    Core Functions:
    1. Device Enum & Selection (Persistence supported)
    2. Realtime VAD (webrtcvad + Sliding Window)
    3. Pre-buffer (Keep 0.5s audio before speech)
    4. State Machine (silence -> speech_start -> speech_continue -> speech_end)
    """
    
    def __init__(
        self,
        sample_rate: int = 16000,
        frame_duration_ms: int = 30,
        aggressiveness: int = 3,
        on_speech_start: Optional[Callable] = None,
        on_speech_end: Optional[Callable[[np.ndarray], None]] = None,
        on_vad_status_change: Optional[Callable[[str], None]] = None
    ):
        """
        Initialize Audio Manager
        
        Args:
            sample_rate: Sample Rate (webrtcvad requires 16000Hz)
            frame_duration_ms: Frame Duration (webrtcvad supports 10/20/30ms)
            aggressiveness: VAD Aggressiveness (0-3, 3 is strict)
            on_speech_start: Callback for speech start
            on_speech_end: Callback for speech end (passes full audio data)
            on_vad_status_change: VAD status change callback
            on_speech_end: Callback for speech end (passes full audio data)
            on_vad_status_change: VAD status change callback
        """
        self.sample_rate = sample_rate
        self.frame_duration_ms = frame_duration_ms
        self.frame_size = int(sample_rate * frame_duration_ms / 1000)
        self.aggressiveness = aggressiveness
        
        # Callbacks
        self.on_speech_start = on_speech_start
        self.on_speech_end = on_speech_end
        self.on_vad_status_change = on_vad_status_change
        self.on_vad_status_change = on_vad_status_change
        
        # VAD Instance
        self.vad = webrtcvad.Vad(aggressiveness)
        
        # === VAD Parameters (Adjustable) ===
        # Sliding window size: Smooths VAD results. Larger = less sensitive.
        self.window_size = 15  # Frames (Original 10)
        
        # Speech Start Threshold: Ratio of speech frames in window to trigger start.
        self.speech_start_threshold = 0.8  # 80% frames are speech
        
        # Speech End Threshold: Ratio of speech frames in window to trigger end.
        # ⚠️ Lower value = more tolerance for pauses.
        self.speech_end_threshold = 0.05  # 5% frames are speech (Original 0.15)
        
        # Min Speech Length (Frames): Audio shorter than this is discarded (Noise filter).
        self.min_speech_frames = 15  # Approx 0.45s (Original 15)
        
        # Sliding Window Buffer (For smoothing VAD)
        self.speech_buffer = deque(maxlen=self.window_size)
        
        # Pre-buffer (Keep 0.5s before speech)
        pre_buffer_frames = int(0.5 * 1000 / frame_duration_ms)  # 0.5s
        self.pre_buffer = deque(maxlen=pre_buffer_frames)
        
        # Audio Frames Accumulator
        self.audio_frames: List[np.ndarray] = []
        
        # State Flags
        self.is_speaking = False
        self.is_running = False
        
        # Audio Stream
        self.stream: Optional[sd.InputStream] = None
        self.device_index: Optional[int] = None
        self.device_name: Optional[str] = None
        
        # Load Config
        self.load_config()
        

    
    def load_config(self):
        """Load device settings from config"""
        if CONFIG_FILE.exists():
            try:
                with open(CONFIG_FILE, "r", encoding="utf-8") as f:
                    config = json.load(f)
                    self.device_name = config.get("device_name")
                    self.speech_start_threshold = config.get("speech_start_threshold", 0.6)
                    self.speech_end_threshold = config.get("speech_end_threshold", 0.05)
                    self.min_speech_frames = config.get("min_speech_frames", 15)
                    logger.info(f"Loaded audio config: Device={self.device_name}, Start={self.speech_start_threshold}, End={self.speech_end_threshold}")
            except Exception as e:
                logger.error(f"Failed to load audio config: {e}")
    
    def save_config(self):
        """Save audio config (preserves existing fields)"""
        # Read existing config
        config = {}
        if CONFIG_FILE.exists():
            try:
                with open(CONFIG_FILE, 'r', encoding='utf-8') as f:
                    config = json.load(f)
            except Exception as e:
                logger.warning(f"Config load failed: {e}. Creating new config.")
        
        # Update Fields
        config['device_name'] = self.device_name
        config['speech_start_threshold'] = self.speech_start_threshold
        config['speech_end_threshold'] = self.speech_end_threshold
        config['min_speech_frames'] = self.min_speech_frames
        
        try:
            with open(CONFIG_FILE, 'w', encoding='utf-8') as f:
                json.dump(config, f, ensure_ascii=False, indent=2)
            logger.info(f"Audio config saved.")
        except Exception as e:
            logger.error(f"Config save failed: {e}")

    def update_params(self, start_threshold: float = None, end_threshold: float = None, min_frames: int = None):
        """Update VAD Params dynamically"""
        if start_threshold is not None:
            self.speech_start_threshold = max(0.1, min(1.0, start_threshold))
        if end_threshold is not None:
            self.speech_end_threshold = max(0.01, min(1.0, end_threshold))
        if min_frames is not None:
             self.min_speech_frames = max(5, min(100, min_frames))
        
        self.save_config()
        logger.info(f"VAD Params updated: Start={self.speech_start_threshold}, End={self.speech_end_threshold}")
    
    def list_devices(self) -> List[Dict]:
        """
        List all available audio input devices.
        
        Returns:
            List of devices (index, name, channels, sample_rate)
        """
        devices = []
        try:
            device_list = sd.query_devices()
            for i, dev in enumerate(device_list):
                # Only Input Devices
                if dev['max_input_channels'] > 0:
                    # Test if available
                    try:
                        # Try open stream (no start)
                        test_stream = sd.InputStream(
                            device=i,
                            channels=1,
                            samplerate=self.sample_rate,
                            blocksize=self.frame_size,
                            dtype='float32'
                        )
                        test_stream.close()
                        
                        # Add to list
                        devices.append({
                            'index': i,
                            'name': dev['name'],
                            'channels': dev['max_input_channels'],
                            'sample_rate': int(dev['default_samplerate']),
                            'hostapi': sd.query_hostapis(dev['hostapi'])['name']
                        })
                    except Exception as e:
                        # Skip unavailable
                        logger.debug(f"Skipping device {i} ({dev['name']}): {e}")
                        continue
            
            logger.info(f"Found {len(devices)} available audio devices.")
        except Exception as e:
            logger.error(f"Device enumeration failed: {e}")
        
        return devices
    
    def set_device_by_name(self, device_name: str) -> bool:
        """
        Args:
            device_name: Device Name
            
        Returns:
            Success or not
        """

        devices = self.list_devices()
        for dev in devices:
            if dev['name'] == device_name:
                self.device_index = dev['index']
                self.device_name = device_name
                self.save_config()
                logger.info(f"Set audio device: {device_name} (Index: {self.device_index})")
                return True
        
        logger.warning(f"Device not found: {device_name}")
        return False
    
    def set_device(self, device_index: int) -> bool:
        """
        Set audio input device by index.
        
        Args:
            device_index: Device Index
            
        Returns:
            Success or not
        """
        devices = self.list_devices()
        for dev in devices:
            if dev['index'] == device_index:
                self.device_index = device_index
                self.device_name = dev['name']
                self.save_config()
                logger.info(f"Set audio device: {self.device_name} (Index: {device_index})")
                return True
        
        logger.warning(f"Invalid device index: {device_index}")
        return False

    def switch_device(self, device_name: str) -> bool:
        """
        Hot-switch audio input device while running.
        Stops current stream, switches device, and restarts if was running.
        
        Args:
            device_name: Target device name
            
        Returns:
            Success or not
        """
        was_running = self.is_running
        
        if was_running:
            logger.info(f"🔄 Hot-switching device: stopping current stream...")
            self.stop()
        
        success = self.set_device_by_name(device_name)
        
        if was_running and success:
            logger.info(f"🔄 Restarting stream with new device: {device_name}")
            self.start()
        elif was_running and not success:
            logger.warning(f"Device switch failed, restarting with previous device")
            self.start()
        
        return success
    
    def _audio_callback(self, indata: np.ndarray, frames: int, time_info, status):
        """
        Audio callback (Called by sounddevice realtime). MUST RETURN FAST.
        
        Args:
            indata: Input Audio Data (frames, channels) float32 [-1, 1]
            frames: Frame count
            time_info: Time info
            status: Status flags
        """
        if status and status.input_overflow:
            # Silent handling overflow
            pass
        
        # Convert to mono (fast)
        audio_frame = indata[:, 0].copy() if indata.ndim > 1 else indata.copy()
        
        # Fast VAD (No blocking ops!)
        result = self._process_frame(audio_frame)
        
        # Simple state notify
        if result == "speech_start" and self.on_speech_start:
            try:
                self.on_speech_start()
            except Exception:
                pass
            
            if self.on_vad_status_change:
                try:
                    self.on_vad_status_change("listening")
                except Exception:
                    pass
        
        elif result == "speech_end":
            audio_data = np.concatenate(self.audio_frames) if self.audio_frames else np.array([])
            self.audio_frames.clear()
            
            # ⚠️ Voiceprint Verification (Removed)
            should_process = True
            # [Spring Cleaning] Verification removed from Audio Loop
            
            # Only callback if verification passed
            if should_process and self.on_speech_end and len(audio_data) > 0:
                try:
                    self.on_speech_end(audio_data)
                except Exception as e:
                    logger.error(f"Error in on_speech_end callback: {e}", exc_info=True)
            
            if self.on_vad_status_change:
                try:
                    self.on_vad_status_change("idle")
                except Exception:
                    pass
    
    def _process_frame(self, frame: np.ndarray) -> str:
        """
        Process single audio frame (VAD + State Machine).
        MUST RETURN FAST.
        
        Args:
            frame: Single audio frame float32 [-1, 1]
            
        Returns:
            Status: "silence" | "speech_start" | "speech_continue" | "speech_end"
        """
        # Convert to int16 PCM (Required by webrtcvad)
        pcm = (frame.clip(-1, 1) * 32767).astype(np.int16).tobytes()
        
        # VAD Check
        try:
            is_speech = self.vad.is_speech(pcm, self.sample_rate)
        except Exception:
            is_speech = False
        
        # Extra Energy Check (Filter low energy noise)
        rms = np.sqrt(np.mean(frame**2))
        
        # [Debug] Trace Audio Levels occasionally
        # import random
        # if random.random() < 0.01:
        #     logger.debug(f"🎤 Audio Level (RMS): {rms:.4f} | VAD: {is_speech}")
            
        if rms < 0.001:  # Lowered noise gate (was 0.005, user has ~0.0039)
            is_speech = False
        
        # Update Sliding Window
        self.speech_buffer.append(is_speech)
        
        # Calculate speech ratio (Smooth VAD results)
        speech_ratio = sum(self.speech_buffer) / len(self.speech_buffer) if self.speech_buffer else 0
        
        # State Machine (Stricter thresholds)
        if not self.is_speaking and speech_ratio > 0.8:  # Up to 0.8 (was 0.7)
            # Speech Start detected
            self.is_speaking = True
            
            # Include pre-buffer to avoid losing beginning
            self.audio_frames.extend(list(self.pre_buffer))
            self.audio_frames.append(frame)
            
            return "speech_start"
        
        elif self.is_speaking and speech_ratio < 0.05:  # End threshold (more tolerant)
            # Speech End detected - Check min length
            if len(self.audio_frames) < 15:  # At least 0.45s
                # Too short, likely noise
                self.is_speaking = False
                self.audio_frames.clear()
                return "silence"
            
            self.is_speaking = False
            return "speech_end"
        
        elif self.is_speaking:
            # Continuing speech
            self.audio_frames.append(frame)
            return "speech_continue"
        
        else:
            # Silence: Maintain Pre-buffer
            self.pre_buffer.append(frame)
            return "silence"
    
    def start(self):
        """Start Audio Capture"""
        if self.is_running:
            logger.warning("Audio manager already running.")
            return
        
        # Try to restore device if name exists
        if self.device_name and self.device_index is None:
            self.set_device_by_name(self.device_name)
        
        try:
            # Print Device Info
            if self.device_index is not None:
                device_info = sd.query_devices(self.device_index)
                logger.info(f"📡 Using Device: [{self.device_index}] {device_info['name']}")
                logger.info(f"   Native Rate: {device_info['default_samplerate']} Hz")
                logger.info(f"   Forcing 16000 Hz (sounddevice will resample)")
            else:
                logger.info(f"📡 Using System Default Device (16000 Hz)")
            
            logger.info(f"Starting Capture (device={self.device_index}, rate=16000, frame_size={self.frame_size})")
            
            # sounddevice auto-resamples to 16kHz
            self.stream = sd.InputStream(
                device=self.device_index,
                samplerate=16000,  # Force 16kHz (sounddevice auto-resamples)
                channels=1,
                dtype='float32',
                blocksize=self.frame_size,
                callback=self._audio_callback
            )
            
            self.stream.start()
            self.is_running = True
            logger.info("Audio capture started.")
            
        except Exception as e:
            logger.error(f"Start capture failed: {e}", exc_info=True)
            self.is_running = False
            self.stream = None
            
            # Retry with default if invalid
            if "Invalid device" in str(e) or "PaErrorCode -9996" in str(e):
                logger.warning("Device invalid, switching to default.")
                self.device_index = None
                self.device_name = None
                try:
                    self.stream = sd.InputStream(
                        samplerate=16000,
                        channels=1,
                        dtype='float32',
                        blocksize=self.frame_size,
                        callback=self._audio_callback
                    )
                    self.stream.start()
                    self.is_running = True
                    logger.info("Switched to system default device.")
                except Exception as e2:
                    logger.error(f"Default device also failed: {e2}", exc_info=True)
    
    def stop(self):
        """
        [Architecture 3.1] Eager Revocation.
        Stop Audio Capture immediately and clear all safety buffers.
        """
        if not self.is_running:
            return
        
        try:
            logger.info("🛑 [Revocation] Eagerly stopping audio stream...")
            if self.stream:
                self.stream.stop()
                self.stream.close()
                self.stream = None
            
            self.is_running = False
            self.is_speaking = False
            
            # Wipe buffers for privacy/safety
            self.audio_frames.clear()
            self.pre_buffer.clear()
            self.speech_buffer.clear()
            
            logger.debug("✅ Audio stream eagerly revoked and buffers wiped.")
        except Exception as e:
            logger.error(f"Stop capture failed: {e}", exc_info=True)
    
    def get_status(self) -> Dict:
        """Get Current Status"""
        return {
            "is_running": self.is_running,
            "is_speaking": self.is_speaking,
            "device_name": self.device_name,
            "device_index": self.device_index,
            "sample_rate": self.sample_rate
        }
