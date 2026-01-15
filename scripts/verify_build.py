
import json
import os
import sys
from pathlib import Path

def main():
    print("🔍 Starting Build Verification...")
    
    # Locate steps from root
    # script is in /scripts/verify_build.py
    # root is /
    root_dir = Path(__file__).parent.parent
    package_json_path = root_dir / "package.json"
    
    if not package_json_path.exists():
        print(f"❌ package.json not found at {package_json_path}")
        sys.exit(1)
        
    try:
        with open(package_json_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
            
        build_config = data.get("build", {})
        resources = build_config.get("extraResources", [])
        
        errors = 0
        
        print(f"📂 Scanning {len(resources)} extraResources...")
        
        for res in resources:
            # Handle string or object 'from'/'to'
            if isinstance(res, str):
                source = res
            else:
                source = res.get("from")
                
            if not source:
                continue
                
            # Resolve relative to root
            full_path = root_dir / source
            
            if full_path.exists():
                print(f"  ✅ Found: {source}")
            else:
                print(f"  ❌ MISSING: {source} (Abs: {full_path})")
                errors += 1
                
        if errors > 0:
            print(f"\n🚫 Verification FAILED with {errors} missing resources.")
            sys.exit(1)
        else:
            print("\n✅ Verification PASSED. All resources exist.")
            sys.exit(0)
            
    except Exception as e:
        print(f"❌ Error parsing package.json: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()
