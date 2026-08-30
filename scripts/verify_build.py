from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]


def fail(message: str) -> None:
    raise RuntimeError(message)


def load_json(relative_path: str) -> dict:
    path = PROJECT_ROOT / relative_path
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception as exc:
        fail(f"Invalid JSON at {relative_path}: {exc}")


def verify_source_contracts() -> None:
    package = load_json("package.json")
    load_json("config/ports.json")
    load_json("config/worker-runtimes.json")

    scripts = package.get("scripts") or {}
    for required_script in ("lint", "verify-build", "verify-runtime-contract"):
        if required_script not in scripts:
            fail(f"package.json is missing script: {required_script}")

    if (package.get("build") or {}).get("nsis", {}).get("deleteAppDataOnUninstall") is not False:
        fail("The uninstaller must preserve Lumina user data")

    mutable_runtime_paths = [
        "brain",
        "data/sessions",
        "python_backend/data",
        "python_backend/sessions",
        "python_backend/lumina.db",
        "python_backend/test_lite_memory_db",
        "python_backend/test_lite_memory_db_consol",
        "python_backend/voiceprint_profiles",
        "test_memory.db",
    ]
    mutable_runtime_paths.extend(
        str(path.relative_to(PROJECT_ROOT))
        for path in (PROJECT_ROOT / "python_backend" / "characters").glob("*/data")
    )
    present = [
        path
        for path in mutable_runtime_paths
        if (PROJECT_ROOT / path).is_file()
        or (
            (PROJECT_ROOT / path).is_dir()
            and any(item.is_file() for item in (PROJECT_ROOT / path).rglob("*"))
        )
    ]
    if present:
        fail(f"Mutable runtime data is present in source paths: {', '.join(present)}")

    requirements = (PROJECT_ROOT / "python_backend" / "requirements.txt").read_text(
        encoding="utf-8"
    )
    for external_database_package in ("asyncpg", "pgvector"):
        if external_database_package in requirements:
            fail(
                f"Default requirements must not require external database package: "
                f"{external_database_package}"
            )

    subprocess.run(
        [sys.executable, str(PROJECT_ROOT / "scripts" / "verify_worker_runtimes.py"), "--contract-only"],
        cwd=PROJECT_ROOT,
        check=True,
    )


def main() -> None:
    verify_source_contracts()
    print("[build-verify] source contracts OK")


if __name__ == "__main__":
    main()
