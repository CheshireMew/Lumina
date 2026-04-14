from __future__ import annotations

import json
import sys
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]
DIST_BACKEND = PROJECT_ROOT / "dist_backend"
CONTRACT_PATH = PROJECT_ROOT / "config" / "capability-packages.json"

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
    print(f"[capability-verify] {message}", file=sys.stderr)
    raise SystemExit(1)


def load_contract() -> dict:
    return json.loads(CONTRACT_PATH.read_text(encoding="utf-8"))


def verify_package(package: dict) -> None:
    package_id = package["id"]
    package_dir = DIST_BACKEND / "packages" / package_id
    if not package_dir.exists():
        fail(f"missing package directory: {package_id}")

    for required in package.get("requiredFiles") or []:
        if not (package_dir / required).exists():
            fail(f"{package_id} missing required file: {required}")

    for metadata_file in ("manifest.json", "version.json", "hashes.json"):
        path = package_dir / metadata_file
        if not path.exists():
            fail(f"{package_id} missing {metadata_file}")
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
    for package in contract["packages"]:
        verify_package(package)
    print("[capability-verify] OK")


if __name__ == "__main__":
    main()
