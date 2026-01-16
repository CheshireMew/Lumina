import os
import subprocess
import shutil
import sys
from pathlib import Path

def run_build(spec_file):
    print(f"🔨 Building {spec_file}...")
    result = subprocess.run([
        sys.executable, "-m", "PyInstaller",
        "--clean",
        "--noconfirm",
        "--distpath", "../dist_backend",
        "--workpath", "./build",
        spec_file
    ], shell=True)
    
    if result.returncode != 0:
        print(f"❌ Build failed for {spec_file}")
        sys.exit(1)
    else:
        print(f"✅ Build success for {spec_file}")

def main():
    # Ensure dependencies are installed
    # subprocess.run([sys.executable, "-m", "pip", "install", "pyinstaller", "auto-py-to-exe"], check=True)
    
    base_dir = Path(__file__).parent.resolve()
    os.chdir(base_dir)
    
    # Specs to build
    specs = ["backend.spec", "stt.spec", "tts.spec"]
    
    # Clean previous dist
    dist_dir = base_dir.parent / "dist_backend"
    if dist_dir.exists():
        print(f"🧹 Cleaning {dist_dir}...")
        shutil.rmtree(dist_dir)
        
    for spec in specs:
        run_build(spec)
        
    print("\n🎉 All backend services built successfully!")
    print(f"📂 Output: {dist_dir}")

if __name__ == "__main__":
    main()
