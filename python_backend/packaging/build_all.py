import os
import subprocess
import shutil
import sys
import json
import hashlib
from datetime import datetime, timezone
from pathlib import Path

def run_build(spec_file: str, dist_dir: Path, build_dir: Path, env: dict[str, str] | None = None):
    print(f"Building {spec_file}...")
    subprocess.run([
        sys.executable, "-m", "PyInstaller",
        "--clean",
        "--noconfirm",
        "--distpath", str(dist_dir),
        "--workpath", str(build_dir),
        spec_file
    ], check=True, env={**os.environ, **(env or {})})
    print(f"Build success for {spec_file}")


def load_worker_runtime_contract(project_root: Path) -> dict:
    contract_path = project_root / "config" / "worker-runtimes.json"
    return json.loads(contract_path.read_text(encoding="utf-8"))


def write_runtime_metadata(target_dir: Path, runtime_def: dict):
    target_dir.mkdir(parents=True, exist_ok=True)
    manifest = {
        "id": runtime_def["id"],
        "version": runtime_def["version"],
        "type": runtime_def["type"],
        "displayName": runtime_def["displayName"],
        "minHostVersion": runtime_def["minHostVersion"],
        "minRuntimeVersion": runtime_def["minRuntimeVersion"],
        "autoStart": runtime_def["autoStart"],
        "optional": runtime_def["optional"],
        "platform": runtime_def["platform"],
        "arch": runtime_def["arch"],
        "capabilities": runtime_def.get("capabilities", []),
        "healthEndpoint": runtime_def.get("healthEndpoint"),
    }
    version = {
        "runtimeId": runtime_def["id"],
        "version": runtime_def["version"],
        "minHostVersion": runtime_def["minHostVersion"],
        "minRuntimeVersion": runtime_def["minRuntimeVersion"],
    }
    (target_dir / "manifest.json").write_text(
        json.dumps(manifest, indent=2, ensure_ascii=False),
        encoding="utf-8",
    )
    (target_dir / "version.json").write_text(
        json.dumps(version, indent=2, ensure_ascii=False),
        encoding="utf-8",
    )


def write_hashes(target_dir: Path):
    hashes = {}
    for path in sorted(target_dir.rglob("*")):
        if not path.is_file() or path.name == "hashes.json":
            continue
        relative_path = path.relative_to(target_dir).as_posix()
        hasher = hashlib.sha256()
        with path.open("rb") as handle:
            for chunk in iter(lambda: handle.read(1024 * 1024), b""):
                hasher.update(chunk)
        hashes[relative_path] = hasher.hexdigest()

    (target_dir / "hashes.json").write_text(
        json.dumps(
            {
                "algorithm": "sha256",
                "generatedAt": datetime.now(timezone.utc).isoformat(timespec="seconds").replace("+00:00", "Z"),
                "files": hashes,
            },
            indent=2,
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )


def reset_runtime_dir(dist_dir: Path, runtime_id: str) -> Path:
    target_dir = dist_dir / "runtimes" / runtime_id
    if target_dir.exists():
        shutil.rmtree(target_dir)
    target_dir.mkdir(parents=True, exist_ok=True)
    return target_dir


def runtime_def(contract: dict, runtime_id: str) -> dict:
    return next(runtime for runtime in contract["runtimes"] if runtime["id"] == runtime_id)


def stage_runtime_copy(
    project_root: Path,
    dist_dir: Path,
    build_dir: Path,
    contract: dict,
    runtime_id: str,
    module_names: list[str],
):
    definition = runtime_def(contract, runtime_id)
    target_dir = reset_runtime_dir(dist_dir, runtime_id)
    runtime_dir = target_dir / "runtime"
    runtime_dist_dir = dist_dir / "_runtime_build" / runtime_id
    runtime_build_dir = build_dir / runtime_id

    write_runtime_metadata(target_dir, definition)
    run_build(
        "backend.spec",
        runtime_dist_dir,
        runtime_build_dir,
        env={"LUMINA_BUILD_TARGET": runtime_id},
    )
    shutil.copytree(runtime_dist_dir / "lumina_backend", runtime_dir)

    module_root = target_dir / "capability_modules"
    module_root.mkdir(parents=True, exist_ok=True)
    source_root = project_root / "python_backend" / "capability_modules"
    for module_name in module_names:
        shutil.copytree(source_root / module_name, module_root / module_name)

    requirements_file = project_root / "python_backend" / f"requirements-{runtime_id.split('-', 1)[0]}.txt"
    if requirements_file.exists():
        shutil.copy2(requirements_file, target_dir / requirements_file.name)

    data_models = target_dir / "data" / "models"
    data_models.mkdir(parents=True, exist_ok=True)
    write_hashes(target_dir)


def stage_voiceprint_runtime(project_root: Path, dist_dir: Path, contract: dict):
    definition = runtime_def(contract, "voiceprint-runtime")
    target_dir = reset_runtime_dir(dist_dir, "voiceprint-runtime")
    write_runtime_metadata(target_dir, definition)

    module_root = target_dir / "capability_modules"
    module_root.mkdir(parents=True, exist_ok=True)
    source_root = project_root / "python_backend" / "capability_modules"
    for module_name in ("voiceprint", "voiceauth_sherpa"):
        shutil.copytree(source_root / module_name, module_root / module_name)

    shutil.copy2(
        project_root / "python_backend" / "requirements-voiceprint.txt",
        target_dir / "requirements-voiceprint.txt",
    )
    (target_dir / "data" / "models").mkdir(parents=True, exist_ok=True)
    write_hashes(target_dir)


def stage_vision_runtime(project_root: Path, dist_dir: Path, contract: dict):
    definition = runtime_def(contract, "vision-runtime")
    target_dir = reset_runtime_dir(dist_dir, "vision-runtime")
    write_runtime_metadata(target_dir, definition)
    shutil.copy2(
        project_root / "python_backend" / "requirements-vision.txt",
        target_dir / "requirements-vision.txt",
    )
    (target_dir / "data" / "models").mkdir(parents=True, exist_ok=True)
    write_hashes(target_dir)


def stage_worker_runtimes(project_root: Path, dist_dir: Path, build_dir: Path, contract: dict):
    stage_runtime_copy(project_root, dist_dir, build_dir, contract, "stt-runtime", ["stt_sensevoice"])
    stage_runtime_copy(project_root, dist_dir, build_dir, contract, "tts-runtime", ["tts_edge"])
    stage_voiceprint_runtime(project_root, dist_dir, contract)
    stage_vision_runtime(project_root, dist_dir, contract)
    runtime_build = dist_dir / "_runtime_build"
    if runtime_build.exists():
        shutil.rmtree(runtime_build)


def prepare_dist_dir(dist_dir: Path):
    if not dist_dir.exists():
        return

    print(f"Cleaning {dist_dir}...")
    try:
        shutil.rmtree(dist_dir)
    except PermissionError:
        stale_dir = dist_dir.with_name(
            f"{dist_dir.name}.stale.{datetime.now().strftime('%Y%m%d%H%M%S')}"
        )
        print(f"Dist directory is locked. Moving it aside to {stale_dir}...")
        dist_dir.rename(stale_dir)

def main():
    # Ensure dependencies are installed
    # subprocess.run([sys.executable, "-m", "pip", "install", "pyinstaller", "auto-py-to-exe"], check=True)
    
    base_dir = Path(__file__).parent.resolve()
    os.chdir(base_dir)
    
    project_root = base_dir.parent.parent
    dist_dir = project_root / "dist_backend"
    build_dir = base_dir / "build"

    prepare_dist_dir(dist_dir)

    run_build("backend.spec", dist_dir, build_dir)
    contract = load_worker_runtime_contract(project_root)
    stage_worker_runtimes(project_root, dist_dir, build_dir, contract)
        
    print("\nBackend runtime built successfully.")
    print(f"Output: {dist_dir}")

if __name__ == "__main__":
    main()
