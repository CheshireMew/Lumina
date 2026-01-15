import os
import logging
import numpy as np
import shutil
import zipfile
try:
    import sherpa_onnx
except ImportError:
    sherpa_onnx = None

from python_backend.model_manager import model_manager

logger = logging.getLogger("ParaformerEngine")

# Simple classes to match Faster-Whisper interface
class Segment:
    def __init__(self, text: str):
        self.text = text

class TranscriptionInfo:
    def __init__(self, language: str):
        self.language = language


class ParaformerEngine:
    def __init__(self, language="zh"):
        self.recognizer = None
        self.language = language # 'zh' or 'en'
        
        # Define model configurations (verified sherpa-onnx releases)
        if self.language == "en":
             # English Paraformer
             self.model_subdir = "paraformer-en"
             self.download_url = "https://github.com/k2-fsa/sherpa-onnx/releases/download/asr-models/sherpa-onnx-paraformer-en-2024-03-09.tar.bz2"
             self.extracted_folder_name = "sherpa-onnx-paraformer-en-2024-03-09"
        else:
             # Chinese Paraformer
             self.model_subdir = "paraformer-zh"
             self.download_url = "https://github.com/k2-fsa/sherpa-onnx/releases/download/asr-models/sherpa-onnx-paraformer-zh-2024-03-09.tar.bz2"
             self.extracted_folder_name = "sherpa-onnx-paraformer-zh-2024-03-09"

        self.model_dir = os.path.join(model_manager.base_dir, self.model_subdir)

    def initialize(self):
        """Initialize the engine, downloading model if necessary"""
        if sherpa_onnx is None:
            logger.error("sherpa-onnx not installed. Cannot use Paraformer.")
            raise ImportError("sherpa-onnx not installed")

        self.ensure_model_exists()
        
        logger.info(f"Loading Paraformer ({self.language}) model from {self.model_dir}...")
        try:
            model_path = os.path.join(self.model_dir, "model.int8.onnx")
            if not os.path.exists(model_path):
                 model_path = os.path.join(self.model_dir, "model.onnx")

            tokens_path = os.path.join(self.model_dir, "tokens.txt")
            
            if not os.path.exists(model_path) or not os.path.exists(tokens_path):
                raise FileNotFoundError(f"Key model files missing in {self.model_dir}")

            logger.info(f"Model path: {model_path}")

            # Initialize Paraformer using the correct API
            self.recognizer = sherpa_onnx.OfflineRecognizer.from_paraformer(
                paraformer=model_path,
                tokens=tokens_path,
                num_threads=2,
                sample_rate=16000,
                feature_dim=80,
                decoding_method="greedy_search",
                debug=False,
                provider="cpu"
            )
            
            logger.info(f"Paraformer-{self.language} engine initialized successfully.")
            
        except Exception as e:
            logger.error(f"Failed to initialize Paraformer: {e}")
            raise e

    def ensure_model_exists(self):
        """Use model_manager to download the model if missing"""
        if os.path.exists(self.model_dir) and any(f.endswith(".onnx") for f in os.listdir(self.model_dir)):
            return

        logger.info(f"Paraformer-{self.language} model not found. Downloading...")
        
        target_path = model_manager.setup_model_env(self.model_subdir)
        
        # Verified download from sherpa-onnx official releases
        archive_path = os.path.join(target_path, "model.tar.bz2")
        
        logger.info(f"Downloading Paraformer-{self.language} from GitHub: {self.download_url}")
        
        try:
            if model_manager.download_file_with_retry(self.download_url, archive_path):
                download_success = True
            else:
                logger.error("Download failed")
                download_success = False
        except Exception as e:
            logger.error(f"Download exception: {e}")
            download_success = False
        
        if download_success:
            try:
                import tarfile
                logger.info("Extracting Paraformer model...")
                with tarfile.open(archive_path, 'r:bz2') as tar:
                    tar.extractall(target_path)
                
                # Move files from subfolder
                extracted_root = os.path.join(target_path, self.extracted_folder_name)
                if os.path.exists(extracted_root):
                    for f in os.listdir(extracted_root):
                        src = os.path.join(extracted_root, f)
                        dst = os.path.join(target_path, f)
                        if os.path.exists(dst):
                            if os.path.isdir(dst): shutil.rmtree(dst)
                            else: os.remove(dst)
                        shutil.move(src, dst)
                    os.rmdir(extracted_root)
                
                os.remove(archive_path)
                logger.info("Model extraction complete.")
            except Exception as e:
                logger.error(f"Failed to extract model: {e}")
                if os.path.exists(archive_path):
                    os.remove(archive_path)
        
        model_manager.restore_model_env()

    def transcribe(self, audio_data: np.ndarray, beam_size: int = 1, **kwargs):
        """
        Transcribe audio data.
        Returns: (segments, info) - matching Faster-Whisper interface
        Note: beam_size is ignored for Paraformer (greedy search only)
        """
        if self.recognizer is None:
            self.initialize()
            
        if audio_data.dtype != np.float32:
            audio_data = audio_data.astype(np.float32)
            
        stream = self.recognizer.create_stream()
        stream.accept_waveform(16000, audio_data)
        self.recognizer.decode_stream(stream)
        
        text = stream.result.text.strip()
        
        # Return format matching Faster-Whisper: (segments, info)
        segments = [Segment(text)] if text else []
        info = TranscriptionInfo(language=self.language)
        
        return segments, info
