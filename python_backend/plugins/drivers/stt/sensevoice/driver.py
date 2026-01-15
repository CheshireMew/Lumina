import os
import logging
import numpy as np
import shutil
from typing import Dict, Any

from python_backend.core.plugins.interface import ASRPlugin
from python_backend.model_manager import model_manager

# Lazy import fallback
try:
    import sherpa_onnx
except ImportError:
    sherpa_onnx = None

logger = logging.getLogger("SenseVoicePlugin")

class Plugin(ASRPlugin):
    def __init__(self):
        self.recognizer = None
        self.model_subdir = "sense-voice"
        self._name = "stt:sensevoice"
        self._version = "1.0.0"

    @property
    def name(self) -> str:
        return self._name

    @property
    def version(self) -> str:
        return self._version

    def load(self, config: Dict[str, Any]) -> bool:
        """
        鍒濆鍖?SenseVoice 寮曟搸
        """
        if sherpa_onnx is None:
            logger.error("sherpa-onnx not installed. Cannot use SenseVoice.")
            return False

        try:
            self._ensure_model_exists()
            model_dir = os.path.join(model_manager.base_dir, self.model_subdir)
            
            tokens_path = os.path.join(model_dir, "tokens.txt")
            model_path = os.path.join(model_dir, "model.int8.onnx")
            
            if not os.path.exists(model_path):
                model_path = os.path.join(model_dir, "model.onnx")
            
            logger.info(f"Loading SenseVoice model from {model_path}")
            
            self.recognizer = sherpa_onnx.OfflineRecognizer.from_sense_voice(
                model=model_path,
                tokens=tokens_path,
                num_threads=2,
                use_itn=True,
                debug=False,
                provider="cpu"
            )
            return True
        except Exception as e:
            logger.error(f"Failed to load SenseVoice plugin: {e}")
            return False

    def _ensure_model_exists(self):
        """鍒╃敤 model_manager 涓嬭浇妯″瀷"""
        model_dir = os.path.join(model_manager.base_dir, self.model_subdir)
        if os.path.exists(model_dir) and any(f.endswith(".onnx") for f in os.listdir(model_dir)):
            return

        logger.info("SenseVoice model not found. Downloading...")
        target_path = model_manager.setup_model_env(self.model_subdir)
        
        # SenseVoice release (2025-09-09)
        download_url = "https://github.com/k2-fsa/sherpa-onnx/releases/download/asr-models/sherpa-onnx-sense-voice-zh-en-ja-ko-yue-int8-2025-09-09.tar.bz2"
        archive_path = os.path.join(target_path, "model.tar.bz2")
        
        if model_manager.download_file_with_retry(download_url, archive_path):
            import tarfile
            with tarfile.open(archive_path, 'r:bz2') as tar:
                tar.extractall(target_path)
            
            # 绉诲姩鏂囦欢
            extracted_folder = os.path.join(target_path, "sherpa-onnx-sense-voice-zh-en-ja-ko-yue-int8-2025-09-09")
            if os.path.exists(extracted_folder):
                for item in os.listdir(extracted_folder):
                    shutil.move(os.path.join(extracted_folder, item), os.path.join(target_path, item))
                os.rmdir(extracted_folder)
            os.remove(archive_path)
        else:
            raise RuntimeError("Failed to download SenseVoice model")

    async def transcribe(self, audio_data: bytes, language: str = "zh") -> str:
        if self.recognizer is None:
            raise RuntimeError("SenseVoice plugin not loaded")
        
        # Convert bytes to float32 numpy array
        # assuming 16kHz, 16bit, mono as per interface spec convention
        audio_array = np.frombuffer(audio_data, dtype=np.int16).astype(np.float32) / 32768.0
        
        stream = self.recognizer.create_stream()
        stream.accept_waveform(16000, audio_array)
        self.recognizer.decode_stream(stream)
        
        result_text = stream.result.text.strip()
        
        # Optional: Clean up emotion tags if needed, or keep them
        # result_text = re.sub(r'<[A-Z]+>', '', result_text).strip()
        
        return result_text
