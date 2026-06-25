import sys
from pathlib import Path
from types import SimpleNamespace


PROJECT_ROOT = Path(__file__).parents[3]
sys.path.append(str(PROJECT_ROOT / "python_backend"))

from provider_drivers.stt_sensevoice.drivers.stt.sensevoice import engine as engine_module
from provider_drivers.stt_sensevoice.drivers.stt.sensevoice.engine import SenseVoiceEngine


def make_engine() -> SenseVoiceEngine:
    engine = SenseVoiceEngine.__new__(SenseVoiceEngine)
    engine.recognizer = None
    engine.active_provider = None
    engine.cuda_unavailable_reason = None
    return engine


def fake_cuda_sherpa(tmp_path):
    package_dir = tmp_path / "sherpa_onnx"
    package_dir.mkdir()
    return SimpleNamespace(
        __version__="1.13.3+cuda",
        __file__=str(package_dir / "__init__.py"),
    )


def test_select_provider_uses_cuda_when_runtime_and_gpu_are_available(monkeypatch, tmp_path):
    engine = make_engine()

    monkeypatch.setenv("LUMINA_STT_DEVICE", "auto")
    monkeypatch.setattr(engine_module, "sherpa_onnx", fake_cuda_sherpa(tmp_path))
    monkeypatch.setattr(engine_module.shutil, "which", lambda name: "nvidia-smi")
    monkeypatch.setattr(
        engine_module.subprocess,
        "run",
        lambda *args, **kwargs: SimpleNamespace(returncode=0, stdout="GPU 0: Test GPU", stderr=""),
    )

    assert engine._select_provider() == "cuda"


def test_select_provider_falls_back_to_cpu_when_gpu_is_missing(monkeypatch, tmp_path):
    engine = make_engine()

    monkeypatch.setenv("LUMINA_STT_DEVICE", "auto")
    monkeypatch.setattr(engine_module, "sherpa_onnx", fake_cuda_sherpa(tmp_path))
    monkeypatch.setattr(engine_module.shutil, "which", lambda name: None)

    assert engine._select_provider() == "cpu"
    assert engine.cuda_unavailable_reason == "nvidia-smi was not found"


def test_initialize_retries_cpu_when_cuda_recognizer_fails(monkeypatch, tmp_path):
    engine = make_engine()
    engine.model_dir = str(tmp_path)
    (tmp_path / "model.int8.onnx").write_bytes(b"model")
    (tmp_path / "tokens.txt").write_text("tokens", encoding="utf-8")
    calls = []

    class FakeOfflineRecognizer:
        @staticmethod
        def from_sense_voice(**kwargs):
            calls.append(kwargs["provider"])
            if kwargs["provider"] == "cuda":
                raise RuntimeError("CUDA provider failed")
            return object()

    fake_sherpa = fake_cuda_sherpa(tmp_path)
    fake_sherpa.OfflineRecognizer = FakeOfflineRecognizer

    monkeypatch.setattr(engine_module, "sherpa_onnx", fake_sherpa)
    monkeypatch.setattr(engine, "ensure_model_exists", lambda: None)
    monkeypatch.setattr(engine, "_select_provider", lambda: "cuda")

    engine.initialize()

    assert calls == ["cuda", "cpu"]
    assert engine.active_provider == "cpu"
    assert engine.recognizer is not None
