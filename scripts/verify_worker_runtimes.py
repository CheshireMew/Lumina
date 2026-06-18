from __future__ import annotations

import json
import sys
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]
DIST_BACKEND = PROJECT_ROOT / "dist_backend"
CONTRACT_PATH = PROJECT_ROOT / "config" / "worker-runtimes.json"

MAIN_FORBIDDEN_NAMES = {
    "torch",
    "torchvision",
    "torchaudio",
    "transformers",
    "sentence_transformers",
    "cv2",
    "llvmlite",
    "numba",
    "sherpa_onnx",
    "faster_whisper",
    "edge_tts",
}

MAIN_FORBIDDEN_PATHS = {
    "capabilities/stt",
    "capabilities/tts",
    "capabilities/vision",
    "services/managers/stt.py",
    "services/managers/tts.py",
    "services/managers/audio.py",
    "services/managers/audio_devices.py",
    "services/managers/vad_processor.py",
}


def fail(message: str) -> None:
    print(f"[runtime-verify] {message}", file=sys.stderr)
    raise SystemExit(1)


def load_contract() -> dict:
    return json.loads(CONTRACT_PATH.read_text(encoding="utf-8"))


def verify_runtime(runtime: dict) -> None:
    runtime_id = runtime["id"]
    runtime_dir = DIST_BACKEND / "runtimes" / runtime_id
    if not runtime_dir.exists():
        fail(f"missing runtime directory: {runtime_id}")

    for required in runtime.get("requiredFiles") or []:
        if not (runtime_dir / required).exists():
            fail(f"{runtime_id} missing required file: {required}")

    for metadata_file in ("manifest.json", "version.json", "hashes.json"):
        path = runtime_dir / metadata_file
        if not path.exists():
            fail(f"{runtime_id} missing {metadata_file}")
        json.loads(path.read_text(encoding="utf-8"))


def verify_main_runtime() -> None:
    main_dir = DIST_BACKEND / "lumina_backend"
    if not main_dir.exists():
        fail("missing core runtime output: dist_backend/lumina_backend")

    lower_paths = [path.as_posix().lower() for path in main_dir.rglob("*")]
    for forbidden_path in MAIN_FORBIDDEN_PATHS:
        if any(path.endswith(forbidden_path) or f"/{forbidden_path}" in path for path in lower_paths):
            fail(f"core runtime contains capability implementation: {forbidden_path}")

    for forbidden in MAIN_FORBIDDEN_NAMES:
        needle = f"/{forbidden.lower()}"
        if any(needle in path or path.endswith(f"/{forbidden.lower()}.py") for path in lower_paths):
            fail(f"core runtime contains forbidden dependency: {forbidden}")


def main() -> None:
    contract = load_contract()
    verify_main_runtime()
    for runtime in contract["runtimes"]:
        verify_runtime(runtime)
    print("[runtime-verify] OK")


if __name__ == "__main__":
    main()
