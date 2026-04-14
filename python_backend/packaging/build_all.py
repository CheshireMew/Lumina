import os
import subprocess
import shutil
import sys
import json
import hashlib
from datetime import UTC, datetime
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


def load_capability_contract(project_root: Path) -> dict:
    contract_path = project_root / "config" / "capability-packages.json"
    return json.loads(contract_path.read_text(encoding="utf-8"))


def write_package_metadata(target_dir: Path, package_def: dict):
    target_dir.mkdir(parents=True, exist_ok=True)
    manifest = {
        "id": package_def["id"],
        "version": package_def["version"],
        "type": package_def["type"],
        "displayName": package_def["displayName"],
        "minHostVersion": package_def["minHostVersion"],
        "minPackageVersion": package_def["minPackageVersion"],
        "autoStart": package_def["autoStart"],
        "optional": package_def["optional"],
        "platform": package_def["platform"],
        "arch": package_def["arch"],
        "capabilities": package_def.get("capabilities", []),
        "healthEndpoint": package_def.get("healthEndpoint"),
    }
    version = {
        "packageId": package_def["id"],
        "version": package_def["version"],
        "minHostVersion": package_def["minHostVersion"],
        "minPackageVersion": package_def["minPackageVersion"],
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
                "generatedAt": datetime.now(UTC).isoformat(timespec="seconds").replace("+00:00", "Z"),
                "files": hashes,
            },
            indent=2,
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )


def reset_package_dir(dist_dir: Path, package_id: str) -> Path:
    target_dir = dist_dir / "packages" / package_id
    if target_dir.exists():
        shutil.rmtree(target_dir)
    target_dir.mkdir(parents=True, exist_ok=True)
    return target_dir


def package_def(contract: dict, package_id: str) -> dict:
    return next(package for package in contract["packages"] if package["id"] == package_id)


def stage_live2d_assets(project_root: Path, dist_dir: Path, contract: dict):
    definition = package_def(contract, "live2d-assets")
    target_dir = reset_package_dir(dist_dir, "live2d-assets")

    write_package_metadata(target_dir, definition)
    shutil.copytree(project_root / "public" / "live2d", target_dir / "live2d")
    (target_dir / "libs").mkdir(parents=True, exist_ok=True)
    shutil.copy2(
        project_root / "public" / "libs" / "live2dcubismcore.min.js",
        target_dir / "libs" / "live2dcubismcore.min.js",
    )
    write_hashes(target_dir)


def stage_runtime_copy(
    project_root: Path,
    dist_dir: Path,
    build_dir: Path,
    contract: dict,
    package_id: str,
    plugin_names: list[str],
):
    definition = package_def(contract, package_id)
    target_dir = reset_package_dir(dist_dir, package_id)
    runtime_dir = target_dir / "runtime"
    package_dist_dir = dist_dir / "_package_build" / package_id
    package_build_dir = build_dir / package_id

    write_package_metadata(target_dir, definition)
    run_build(
        "backend.spec",
        package_dist_dir,
        package_build_dir,
        env={"LUMINA_BUILD_TARGET": package_id},
    )
    shutil.copytree(package_dist_dir / "lumina_backend", runtime_dir)

    plugin_root = target_dir / "plugins" / "extensions"
    plugin_root.mkdir(parents=True, exist_ok=True)
    source_root = project_root / "python_backend" / "plugins" / "extensions"
    for plugin_name in plugin_names:
        shutil.copytree(source_root / plugin_name, plugin_root / plugin_name)

    requirements_file = project_root / "python_backend" / f"requirements-{package_id.split('-', 1)[0]}.txt"
    if requirements_file.exists():
        shutil.copy2(requirements_file, target_dir / requirements_file.name)

    data_models = target_dir / "data" / "models"
    data_models.mkdir(parents=True, exist_ok=True)
    write_hashes(target_dir)


def stage_voiceprint_runtime(project_root: Path, dist_dir: Path, contract: dict):
    definition = package_def(contract, "voiceprint-runtime")
    target_dir = reset_package_dir(dist_dir, "voiceprint-runtime")
    write_package_metadata(target_dir, definition)

    plugin_root = target_dir / "plugins" / "extensions"
    plugin_root.mkdir(parents=True, exist_ok=True)
    source_root = project_root / "python_backend" / "plugins" / "extensions"
    for plugin_name in ("voiceprint", "voiceauth_sherpa"):
        shutil.copytree(source_root / plugin_name, plugin_root / plugin_name)

    shutil.copy2(
        project_root / "python_backend" / "requirements-voiceprint.txt",
        target_dir / "requirements-voiceprint.txt",
    )
    (target_dir / "data" / "models").mkdir(parents=True, exist_ok=True)
    write_hashes(target_dir)


def stage_vision_runtime(project_root: Path, dist_dir: Path, contract: dict):
    definition = package_def(contract, "vision-runtime")
    target_dir = reset_package_dir(dist_dir, "vision-runtime")
    write_package_metadata(target_dir, definition)
    shutil.copy2(
        project_root / "python_backend" / "requirements-vision.txt",
        target_dir / "requirements-vision.txt",
    )
    (target_dir / "data" / "models").mkdir(parents=True, exist_ok=True)
    write_hashes(target_dir)


def stage_core_runtime_metadata(dist_dir: Path, contract: dict):
    definition = package_def(contract, "core-runtime")
    target_dir = reset_package_dir(dist_dir, "core-runtime")
    write_package_metadata(target_dir, definition)
    write_hashes(target_dir)


def stage_capability_packages(project_root: Path, dist_dir: Path, build_dir: Path, contract: dict):
    stage_core_runtime_metadata(dist_dir, contract)
    stage_live2d_assets(project_root, dist_dir, contract)
    stage_runtime_copy(project_root, dist_dir, build_dir, contract, "stt-runtime", ["stt_sensevoice"])
    stage_runtime_copy(project_root, dist_dir, build_dir, contract, "tts-runtime", ["tts_edge"])
    stage_voiceprint_runtime(project_root, dist_dir, contract)
    stage_vision_runtime(project_root, dist_dir, contract)
    package_build = dist_dir / "_package_build"
    if package_build.exists():
        shutil.rmtree(package_build)


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
    contract = load_capability_contract(project_root)
    stage_capability_packages(project_root, dist_dir, build_dir, contract)
        
    print("\nBackend runtime built successfully.")
    print(f"Output: {dist_dir}")

if __name__ == "__main__":
    main()
