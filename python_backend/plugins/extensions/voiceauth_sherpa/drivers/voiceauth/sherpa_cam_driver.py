import logging
import os
import numpy as np
import sherpa_onnx
import torch
from typing import Dict, Tuple, Any, Optional
from pathlib import Path
from app_config import MODELS_DIR

from core.interfaces.driver import BaseVoiceAuthDriver

logger = logging.getLogger("SherpaCAMDriver")

class SherpaCAMDriver(BaseVoiceAuthDriver):
    def __init__(self):
        super().__init__(
            id="sherpa-cam",
            name="Sherpa 3D-Speaker (CAM++)",
            description="Efficient Chinese-optimized speaker verification using Alibaba's CAM++ model."
        )
        self.extractor: Optional[sherpa_onnx.SpeakerEmbeddingExtractor] = None
        # New standardized path: models/voiceauth/sherpa-cam/model.onnx
        self.model_dir = MODELS_DIR / "voiceauth" / "sherpa-cam"
        self.model_filename = "3dspeaker_campplus.onnx"
        self.download_url = "https://github.com/k2-fsa/sherpa-onnx/releases/download/speaker-recongition-models/3dspeaker_speech_campplus_sv_zh_en_16k-common_advanced.onnx"

    async def load(self):
        if self.extractor: return
        
        target_path = self.model_dir / self.model_filename
        
        # 1. Auto-Download
        if not target_path.exists():
            logger.info(f"VoiceAuth model not found. Downloading to {target_path}...")
            self.model_dir.mkdir(parents=True, exist_ok=True)
            
            try:
                # Use model_manager.download_file_with_retry if available, or simple logic.
                # Since we are inside a driver, let's try to import model_manager, 
                # otherwise fallback to simple download.
                try:
                    from python_backend.model_manager import model_manager
                    success = model_manager.download_file_with_retry(self.download_url, str(target_path))
                except ImportError:
                    # Fallback if model_manager not importable directly
                    import urllib.request
                    logger.info(f"Downloading from {self.download_url}")
                    urllib.request.urlretrieve(self.download_url, str(target_path))
                    success = True
                
                if not success:
                    raise RuntimeError("Download failed")
                    
                logger.info("VoiceAuth model downloaded successfully.")
                
            except Exception as e:
                logger.error(f"Failed to download VoiceAuth model: {e}")
                # Try legacy path as fallback?
                # legacy_path = Path("voiceprint_profiles/3dspeaker_campplus.onnx")
                # if legacy_path.exists():
                #     logger.warning("Using legacy model file as fallback.")
                #     target_path = legacy_path
                # else:
                raise e

        # 2. Load Extractor
        try:
            provider = "cuda" if torch.cuda.is_available() else "cpu"
            logger.info(f"Loading Sherpa-ONNX VoiceAuth on {provider}...")
            
            config = sherpa_onnx.SpeakerEmbeddingExtractorConfig(
                model=str(target_path),
                debug=False,
                provider=provider,
                num_threads=max(1, os.cpu_count() - 1)
            )
            self.extractor = sherpa_onnx.SpeakerEmbeddingExtractor(config)
            logger.info("SherpaCAMDriver Loaded Successfully")
        except Exception as e:
            logger.error(f"Failed to load SherpaCAMDriver: {e}")
            raise e

    def extract_embedding(self, audio: np.ndarray, sample_rate: int = 16000) -> np.ndarray:
        if not self.extractor:
             logger.warning("Extractor not loaded, attempting lazy load...")
             # Cannot await in sync method easily? 
             # For now, assume loaded or fail.
             # Ideally manager ensures load() is called.
             return np.array([])

        # Ensure Float32 Monochannel
        if audio.ndim > 1: audio = audio[:, 0]
        audio = audio.astype(np.float32)
        
        stream = self.extractor.create_stream()
        stream.accept_waveform(sample_rate=sample_rate, waveform=audio)
        stream.input_finished()
        
        embedding = self.extractor.compute(stream)
        return np.array(embedding)

    def verify(self, audio: np.ndarray, profiles: Dict[str, np.ndarray], threshold: float) -> Tuple[bool, str, float]:
        if not self.extractor or not profiles:
            return False, "", 0.0

        # Extract Input Embedding
        test_embedding = self.extract_embedding(audio)
        if test_embedding.size == 0: return False, "", 0.0
        
        best_score = -1.0
        best_name = ""
        
        test_norm = np.linalg.norm(test_embedding)
        if test_norm == 0: return False, "", 0.0

        # Compare against ALL profiles
        for name, target_embedding in profiles.items():
            target_norm = np.linalg.norm(target_embedding)
            if target_norm == 0: continue
            
            # Cosine Similarity
            dot = np.dot(target_embedding, test_embedding)
            score = float(dot / (target_norm * test_norm))
            
            if score > best_score:
                best_score = score
                best_name = name
        
        # Check Threshold
        is_match = best_score >= threshold
        
        # Logging for debugging
        if is_match or best_score > 0.3: # Only log relevant attempts
            logger.info(f"Voice Verify: Best match '{best_name}' ({best_score:.4f}) >= {threshold}? {is_match}")
            
        return is_match, best_name, best_score
