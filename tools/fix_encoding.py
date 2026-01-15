import os
import sys
from pathlib import Path

try:
    import ftfy
except ImportError:
    print("❌ Error: 'ftfy' is not installed.")
    print("Please install it using: pip install ftfy")
    sys.exit(1)

def fix_file(file_path):
    try:
        # Read as binary first
        with open(file_path, 'rb') as f:
            raw_data = f.read()

        # Attempt to decode as utf-8, falling back if necessary (though usually we want to force read to fix)
        # Using ftfy.fix_text logic
        # We read as utf-8 (or 'latin-1' if it's really messed up) to get a string, then let ftfy fix the logic.
        
        try:
            content = raw_data.decode('utf-8')
        except UnicodeDecodeError:
            # If standard UTF-8 fail, it might be heavily corrupted or pure GBK
            try:
                content = raw_data.decode('gbk')
            except:
                content = raw_data.decode('latin-1')

        # The Magic: ftfy fixes the mojibake
        fixed_content = ftfy.fix_text(content)

        if content != fixed_content:
            print(f"🔧 Fixing: {file_path}")
            # Write back as clean UTF-8
            with open(file_path, 'w', encoding='utf-8') as f:
                f.write(fixed_content)
            return True
        return False

    except Exception as e:
        print(f"⚠️  Skipping {file_path}: {e}")
        return False

def scan_and_fix(root_dir):
    print(f"🔍 Scanning directory: {root_dir}")
    count = 0
    # Extensions to check
    extensions = {'.py', '.md', '.json', '.txt', '.yaml', '.yml'}
    
    # Common directories to ignore
    ignore_dirs = {
        '.git', '__pycache__', 'venv', 'node_modules', 
        'build_backend', 'dist', 'dist_backend', 'dist-electron', 
        'example', 'models', 'release', 'bin', 'obj', '.vs', 'GPT-SoVITS', 'Repositories'
    }

    for root, dirs, files in os.walk(root_dir):
        # Allow checking if any part of the path is in ignore list to catch subdirs
        # But os.walk 'dirs' modification allows pruning the tree efficiently
        dirs[:] = [d for d in dirs if d not in ignore_dirs]
        
        # Also check if we are currently inside an ignored dir (in case it wasn't pruned correctly or for safety)
        # (The pruning above handles immediate children, but this is a double check if root starts inside)
        if any(ignored in Path(root).parts for ignored in ignore_dirs):
            continue

        for file in files:
            p = Path(root) / file
            if p.suffix in extensions:
                if fix_file(str(p)):
                    count += 1
    
    print(f"✅ Done. Fixed {count} files.")

if __name__ == "__main__":
    # Default to parent directory of this script (project root)
    project_root = Path(__file__).parent.parent
    scan_and_fix(project_root)
