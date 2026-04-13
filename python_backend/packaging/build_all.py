import os
import subprocess
import shutil
import sys
from pathlib import Path

def run_build(spec_file: str, dist_dir: Path, build_dir: Path):
    print(f"Building {spec_file}...")
    subprocess.run([
        sys.executable, "-m", "PyInstaller",
        "--clean",
        "--noconfirm",
        "--distpath", str(dist_dir),
        "--workpath", str(build_dir),
        spec_file
    ], check=True)
    print(f"Build success for {spec_file}")

def main():
    # Ensure dependencies are installed
    # subprocess.run([sys.executable, "-m", "pip", "install", "pyinstaller", "auto-py-to-exe"], check=True)
    
    base_dir = Path(__file__).parent.resolve()
    os.chdir(base_dir)
    
    project_root = base_dir.parent.parent
    dist_dir = project_root / "dist_backend"
    build_dir = base_dir / "build"

    if dist_dir.exists():
        print(f"Cleaning {dist_dir}...")
        shutil.rmtree(dist_dir)

    run_build("backend.spec", dist_dir, build_dir)
        
    print("\nBackend runtime built successfully.")
    print(f"Output: {dist_dir}")

if __name__ == "__main__":
    main()
