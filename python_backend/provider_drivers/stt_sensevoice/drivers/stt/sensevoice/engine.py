import os
import logging
import numpy as np
import subprocess
import shutil
try:
    import sherpa_onnx
except ImportError:
    sherpa_onnx = None

try:
    from model_manager import model_manager
except ImportError:
    from python_backend.model_manager import model_manager

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
        self.active_provider = None
        self.cuda_unavailable_reason = None
        # Default SenseVoiceSmall model from Sherpa-ONNX releases
        self.model_subdir = "sense-voice" 
        self.models_root = os.environ.get("LUMINA_STT_MODELS_DIR") or model_manager.base_dir
        self.model_dir = os.path.join(self.models_root, self.model_subdir)
        
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
            os.path.join(self.model_dir, "rule.fst")
            os.path.join(self.model_dir, "rule.far")
            
            provider = self._select_provider()
            try:
                self.recognizer = self._create_recognizer(model_path, tokens_path, provider)
                self.active_provider = provider
            except Exception as exc:
                if provider != "cuda":
                    raise
                logger.warning("CUDA STT initialization failed; falling back to CPU: %s", exc)
                self.recognizer = self._create_recognizer(model_path, tokens_path, "cpu")
                self.active_provider = "cpu"
            
            logger.info("SenseVoice engine initialized successfully with provider=%s.", self.active_provider)
            
        except Exception as e:
            logger.error(f"Failed to initialize SenseVoice: {e}")
            raise e

    def _create_recognizer(self, model_path: str, tokens_path: str, provider: str):
        # Use the correct sherpa-onnx factory method for SenseVoice.
        return sherpa_onnx.OfflineRecognizer.from_sense_voice(
            model=model_path,
            tokens=tokens_path,
            num_threads=2,
            use_itn=True,
            debug=False,
            provider=provider,
        )

    def _select_provider(self) -> str:
        requested = self._resolve_requested_provider()
        if requested == "cpu":
            return "cpu"

        if self._cuda_runtime_available():
            return "cuda"

        message = self.cuda_unavailable_reason or "CUDA is not available"
        if requested == "cuda":
            logger.warning("Configured STT provider is CUDA, but %s; falling back to CPU.", message)
        else:
            logger.info("CUDA STT provider unavailable (%s); using CPU.", message)
        return "cpu"

    def _resolve_requested_provider(self) -> str:
        raw = os.environ.get("LUMINA_STT_PROVIDER") or os.environ.get("LUMINA_STT_DEVICE")
        if raw is None:
            try:
                from app_config import config as app_settings
                raw = getattr(app_settings.stt, "device", None)
            except Exception:
                raw = None

        value = str(raw or "auto").strip().lower()
        if value in {"gpu", "cuda:0"}:
            return "cuda"
        if value in {"cpu", "cuda", "auto"}:
            return value

        logger.warning("Unknown STT device/provider '%s'; using auto detection.", raw)
        return "auto"

    def _cuda_runtime_available(self) -> bool:
        self.cuda_unavailable_reason = None
        if sherpa_onnx is None:
            self.cuda_unavailable_reason = "sherpa-onnx is not installed"
            return False

        version = str(getattr(sherpa_onnx, "__version__", ""))
        package_dir = os.path.dirname(getattr(sherpa_onnx, "__file__", ""))
        cuda_provider_dll = os.path.join(package_dir, "lib", "onnxruntime_providers_cuda.dll")
        if "+cuda" not in version and not os.path.exists(cuda_provider_dll):
            self.cuda_unavailable_reason = f"sherpa-onnx {version or 'unknown'} is not a CUDA build"
            return False

        visible_devices = os.environ.get("CUDA_VISIBLE_DEVICES")
        if visible_devices is not None and visible_devices.strip() in {"", "-1"}:
            self.cuda_unavailable_reason = "CUDA_VISIBLE_DEVICES disables all GPUs"
            return False

        nvidia_smi = shutil.which("nvidia-smi")
        if not nvidia_smi:
            self.cuda_unavailable_reason = "nvidia-smi was not found"
            return False

        try:
            result = subprocess.run(
                [nvidia_smi, "-L"],
                capture_output=True,
                text=True,
                timeout=3,
                check=False,
            )
        except Exception as exc:
            self.cuda_unavailable_reason = f"nvidia-smi check failed: {exc}"
            return False

        if result.returncode != 0:
            reason = (result.stderr or result.stdout or "no NVIDIA GPU reported").strip()
            self.cuda_unavailable_reason = reason
            return False

        if not result.stdout.strip():
            self.cuda_unavailable_reason = "nvidia-smi did not report any GPU"
            return False

        return True

    def ensure_model_exists(self):
        """Use model_manager to download the model if missing"""
        if os.path.exists(self.model_dir) and any(f.endswith(".onnx") for f in os.listdir(self.model_dir)):
            return

        logger.info("SenseVoice model not found. Downloading...")
        
        target_path = os.path.join(self.models_root, self.model_subdir)
        os.makedirs(target_path, exist_ok=True)
        
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
                # Safe extraction (Zip Slip mitigation)
                def is_safe_path(base, path):
                    base = os.path.abspath(base)
                    path = os.path.abspath(path)
                    return os.path.commonprefix([base, path]) == base

                with tarfile.open(archive_path, 'r:bz2') as tar:
                    for member in tar.getmembers():
                        member_path = os.path.join(target_path, member.name)
                        if not is_safe_path(target_path, member_path):
                            logger.warning(f"Blocked unsafe file path during extraction: {member.name}")
                            continue
                        tar.extract(member, target_path)
                
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
        info.provider = self.active_provider
        
        return segments, info
