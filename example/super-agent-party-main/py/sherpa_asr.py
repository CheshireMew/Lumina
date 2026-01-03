# sherpa_asord.py
from pathlib import Path
import sherpa_onnx
import soundfile as sf
from io import BytesIO
from py.get_setting import DEFAULT_ASR_DIR
import platform

# ---------- 设备选择 ----------
def _nvidia_gpu_count() -> int:
    try:
        import pynvml
        pynvml.nvmlInit()
        return pynvml.nvmlDeviceGetCount()
    except Exception:
        return 0

def _best_provider() -> str:
    if _nvidia_gpu_count() > 0:
        return 'cuda'
    if platform.system() == 'Darwin' and platform.machine() == 'arm64':
        return 'coreml'
    return 'cpu'

DEVICE = _best_provider()
DEFAULT_MODEL_NAME = "sherpa-onnx-sense-voice-zh-en-ja-ko-yue"

# ---------- 懒加载 recognizer ----------
_recognizer = None

def _get_recognizer(model_name: str = DEFAULT_MODEL_NAME):
    global _recognizer
    if _recognizer is None:          # 第一次调用时才初始化
        model_dir = Path(DEFAULT_ASR_DIR) / model_name
        model = model_dir / "model.int8.onnx"
        tokens = model_dir / "tokens.txt"
        if not model.is_file() or not tokens.is_file():
            raise ValueError(f"Sherpa 模型文件未找到，目录={model_dir}")

        _recognizer = sherpa_onnx.OfflineRecognizer.from_sense_voice(
            model=str(model),
            tokens=str(tokens),
            num_threads=4,
            provider=DEVICE,
            use_itn=True,
            debug=False,
        )
    return _recognizer

# ---------- 识别接口 ----------
async def sherpa_recognize(audio_bytes: bytes, model_name: str = None):
    recognizer = _get_recognizer(model_name or DEFAULT_MODEL_NAME)
    try:
        with BytesIO(audio_bytes) as audio_file:
            audio, sample_rate = sf.read(audio_file, dtype="float32", always_2d=True)
            audio = audio[:, 0]
            stream = recognizer.create_stream()
            stream.accept_waveform(sample_rate, audio)
            recognizer.decode_stream(stream)
            return stream.result.text
    except Exception as e:
        raise RuntimeError(f"Sherpa ASR 处理失败: {e}")