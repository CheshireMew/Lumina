import os
import logging
import numpy as np
import shutil
import sys
try:
    import sherpa_onnx
except ImportError:
    sherpa_onnx = None

from model_manager import model_manager

logger = logging.getLogger("SenseVoiceEngine")

# Simple classes to match Faster-Whisper interface
class Segment:
    def __init__(self, text: str):
        self.text = text

class TranscriptionInfo:
    def __init__(self, language: str):
        self.language = language


class SenseVoiceEngine:
    def __init__(self):
        self.recognizer = None
        # Default SenseVoiceSmall model from Sherpa-ONNX releases
        self.model_subdir = "sense-voice" 
        self.model_dir = os.path.join(model_manager.base_dir, self.model_subdir)
        
    def initialize(self):
        """Initialize the engine, downloading model if necessary"""
        if sherpa_onnx is None:
            logger.error("sherpa-onnx not installed. Cannot use SenseVoice.")
            raise ImportError("sherpa-onnx not installed")

        self.ensure_model_exists()
        
        logger.info(f"Loading SenseVoice model from {self.model_dir}...")
        try:
            tokens_path = os.path.join(self.model_dir, "tokens.txt")
            # Sherpa-ONNX model names can vary. The zip typically contains 'model.int8.onnx' or 'model.onnx'
            model_path = os.path.join(self.model_dir, "model.int8.onnx")
            
            if not os.path.exists(model_path):
                model_path = os.path.join(self.model_dir, "model.onnx")
            
            if not os.path.exists(model_path) or not os.path.exists(tokens_path):
                raise FileNotFoundError(f"Key model files missing in {self.model_dir}")

            logger.info(f"Model path: {model_path}")

            # Check for optional rule files for emotion/event tags
            rule_fsts_path = os.path.join(self.model_dir, "rule.fst")
            rule_far_path = os.path.join(self.model_dir, "rule.far")
            
            # Use the correct sherpa-onnx factory method for SenseVoice
            # Note: rule parameter enables emotion/event tag output
            self.recognizer = sherpa_onnx.OfflineRecognizer.from_sense_voice(
                model=model_path,
                tokens=tokens_path,
                num_threads=2,
                use_itn=True,
                debug=False,
                provider="cpu"
            )
            
            logger.info("SenseVoice engine initialized successfully.")
            
        except Exception as e:
            logger.error(f"Failed to initialize SenseVoice: {e}")
            raise e

    def ensure_model_exists(self):
        """Use model_manager to download the model if missing"""
        if os.path.exists(self.model_dir) and any(f.endswith(".onnx") for f in os.listdir(self.model_dir)):
            return

        logger.info("SenseVoice model not found. Downloading...")
        
        target_path = model_manager.setup_model_env(self.model_subdir)
        
        # Latest verified SenseVoice release (2025-09-09)
        download_url = "https://github.com/k2-fsa/sherpa-onnx/releases/download/asr-models/sherpa-onnx-sense-voice-zh-en-ja-ko-yue-int8-2025-09-09.tar.bz2"
        archive_path = os.path.join(target_path, "model.tar.bz2")
        
        logger.info(f"Downloading SenseVoice (2025-09-09) from GitHub: {download_url}")
        
        try:
            if model_manager.download_file_with_retry(download_url, archive_path):
                download_success = True
            else:
                logger.error("Download failed")
                download_success = False
        except Exception as e:
            logger.error(f"Download exception: {e}")
            download_success = False
        
        if download_success:
            import tarfile
            try:
                logger.info("Extracting SenseVoice model...")
                with tarfile.open(archive_path, 'r:bz2') as tar:
                    tar.extractall(target_path)
                
                # Move files from extracted subfolder
                extracted_folder = os.path.join(target_path, "sherpa-onnx-sense-voice-zh-en-ja-ko-yue-int8-2025-09-09")
                if os.path.exists(extracted_folder):
                    for item in os.listdir(extracted_folder):
                        src = os.path.join(extracted_folder, item)
                        dst = os.path.join(target_path, item)
                        if os.path.exists(dst):
                            if os.path.isdir(dst):
                                shutil.rmtree(dst)
                            else:
                                os.remove(dst)
                        shutil.move(src, dst)
                    os.rmdir(extracted_folder)
                
                os.remove(archive_path)
                logger.info("SenseVoice model extraction complete.")
            except Exception as e:
                logger.error(f"Failed to extract model: {e}")
                if os.path.exists(archive_path):
                    os.remove(archive_path)

    def transcribe(self, audio_data: np.ndarray, beam_size: int = 1, **kwargs):
        """
        Transcribe audio data with SenseVoice.
        Returns: (segments, info) - matching Faster-Whisper interface
        Args:
            audio_data: float32, expected 16kHz
            beam_size: ignored for SenseVoice (greedy search only)
        """
        if self.recognizer is None:
            self.initialize()
            
        # Ensure float32
        if audio_data.dtype != np.float32:
            audio_data = audio_data.astype(np.float32)
            
        # Create stream for this segment
        stream = self.recognizer.create_stream()
        
        # Accept waveform
        # Sherpa-ONNX expects sample_rate=16000
        stream.accept_waveform(16000, audio_data)
        
        # Decode
        self.recognizer.decode_stream(stream)
        
        text = stream.result.text.strip()
        
        # Parse emotion tags from SenseVoice output
        # SenseVoice outputs tags like: <HAPPY>, <SAD>, <ANGRY>, <NEUTRAL>, etc.
        import re
        emotion_tags = re.findall(r'<([A-Z]+)>', text)
        emotion = emotion_tags[0] if emotion_tags else None
        
        # Remove emotion tags from text for cleaner output (optional)
        # clean_text = re.sub(r'<[A-Z]+>', '', text).strip()
        # For now, keep the tags in the text so users can see them
        
        # Return format matching Faster-Whisper: (segments, info)
        segments = [Segment(text)] if text else []
        info = TranscriptionInfo(language="auto")
        # Add emotion info if available
        if emotion:
            info.emotion = emotion
        
        return segments, info
