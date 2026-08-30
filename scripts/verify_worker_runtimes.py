from __future__ import annotations

import json
import hashlib
import sys
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]
DIST_BACKEND = PROJECT_ROOT / "dist_backend"
CONTRACT_PATH = PROJECT_ROOT / "config" / "worker-runtimes.json"
PORTS_PATH = PROJECT_ROOT / "config" / "ports.json"

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


def verify_contract(runtime: dict) -> None:
    runtime_id = runtime.get("id")
    if not runtime_id:
        fail("runtime contract entry is missing id")
    if runtime.get("type") == "runtime" and not runtime.get("entryExecutable"):
        fail(f"{runtime_id} is executable but has no entryExecutable")
    if runtime.get("autoStart") and not runtime.get("entryExecutable"):
        fail(f"{runtime_id} autoStart requires entryExecutable")
    required = set(runtime.get("requiredFiles") or [])
    entry = runtime.get("entryExecutable")
    if entry and entry not in required:
        fail(f"{runtime_id} entryExecutable is not a required file: {entry}")

    for source in runtime.get("sources") or []:
        source_entry = source.get("entryExecutable") or entry
        source_required = set(source.get("requiredFiles") or required)
        if runtime.get("type") == "runtime" and not source_entry:
            fail(f"{runtime_id}/{source.get('name')} has no executable entry")
        if source_entry and source_entry not in source_required:
            fail(
                f"{runtime_id}/{source.get('name')} entryExecutable is not required: "
                f"{source_entry}"
            )


def verify_capability_contracts(contract: dict) -> None:
    runtimes = {
        runtime["id"]: runtime
        for runtime in contract.get("runtimes") or []
        if runtime.get("id")
    }
    configured_ports = json.loads(PORTS_PATH.read_text(encoding="utf-8"))
    capabilities: set[str] = set()
    runtime_port_keys: dict[str, str] = {}

    for item in contract.get("capabilityContracts") or []:
        capability = str(item.get("capability") or "")
        if not capability:
            fail("capability contract is missing capability")
        if capability in capabilities:
            fail(f"duplicate capability contract: {capability}")
        capabilities.add(capability)

        runtime_target = str(item.get("runtimeTarget") or "")
        port_key = str(item.get("portKey") or "")
        control_base_path = str(item.get("controlBasePath") or "")
        if not runtime_target or not port_key or not control_base_path.startswith("/"):
            fail(f"{capability} has an incomplete runtime/control contract")
        if port_key not in configured_ports:
            fail(f"{capability} references unknown port key: {port_key}")
        previous_port_key = runtime_port_keys.setdefault(runtime_target, port_key)
        if previous_port_key != port_key:
            fail(f"{runtime_target} has conflicting port keys")

        runtime_id = item.get("runtimeId")
        if runtime_id:
            runtime = runtimes.get(runtime_id)
            if runtime is None:
                fail(f"{capability} references unknown runtime: {runtime_id}")
            if capability not in (runtime.get("capabilities") or []):
                fail(f"{runtime_id} does not declare capability: {capability}")

    if not capabilities:
        fail("contract defines no capability contracts")
    declared_runtime_capabilities = {
        capability
        for runtime in runtimes.values()
        for capability in runtime.get("capabilities") or []
    }
    missing_contracts = declared_runtime_capabilities - capabilities
    if missing_contracts:
        fail(
            "runtime capabilities missing public contracts: "
            + ", ".join(sorted(missing_contracts))
        )


def verify_runtime(runtime: dict) -> None:
    runtime_id = runtime["id"]
    runtime_dir = DIST_BACKEND / "runtimes" / runtime_id
    if not runtime_dir.exists():
        fail(f"missing runtime directory: {runtime_id}")

    for required in runtime.get("requiredFiles") or []:
        if not (runtime_dir / required).exists():
            fail(f"{runtime_id} missing required file: {required}")

    metadata = {}
    for metadata_file in ("manifest.json", "version.json", "hashes.json"):
        path = runtime_dir / metadata_file
        if not path.exists():
            fail(f"{runtime_id} missing {metadata_file}")
        metadata[metadata_file] = json.loads(path.read_text(encoding="utf-8"))

    manifest = metadata["manifest.json"]
    version = metadata["version.json"]
    if manifest.get("id") != runtime_id or manifest.get("version") != runtime["version"]:
        fail(f"{runtime_id} manifest identity/version does not match contract")
    if version.get("runtimeId") != runtime_id or version.get("version") != runtime["version"]:
        fail(f"{runtime_id} version metadata does not match contract")

    hashes = metadata["hashes.json"]
    if hashes.get("algorithm") != "sha256" or not isinstance(hashes.get("files"), dict):
        fail(f"{runtime_id} hashes.json is not a sha256 file map")
    for relative_path, expected in hashes["files"].items():
        target = runtime_dir / relative_path
        if not target.is_file():
            fail(f"{runtime_id} hash references missing file: {relative_path}")
        actual = hashlib.sha256(target.read_bytes()).hexdigest()
        if actual != expected:
            fail(f"{runtime_id} hash mismatch: {relative_path}")

    unhashed_required = [
        item
        for item in runtime.get("requiredFiles") or []
        if item != "hashes.json" and item not in hashes["files"]
    ]
    if unhashed_required:
        fail(f"{runtime_id} required files are not hashed: {', '.join(unhashed_required)}")


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
    verify_capability_contracts(contract)
    for runtime in contract["runtimes"]:
        verify_contract(runtime)
    if "--contract-only" in sys.argv:
        print("[runtime-verify] contract OK")
        return
    verify_main_runtime()
    for runtime in contract["runtimes"]:
        verify_runtime(runtime)
    print("[runtime-verify] OK")


if __name__ == "__main__":
    main()
