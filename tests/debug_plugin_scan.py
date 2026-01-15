
import sys
import os
import logging
from pathlib import Path
import yaml
import importlib.util

# Setup Logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("DebugPluginScan")

def load_from_manifest(path: Path):
    print(f"[-] Scanning {path}...")
    try:
        with open(path, 'r', encoding="utf-8") as f:
            data = yaml.safe_load(f)
        
        if not data or 'id' not in data:
            print(f"[!] Invalid manifest at {path}")
            return None
            
        print(f"[+] Manifest parsed. ID: {data.get('id')}")
        
        # Check Isolation
        if data.get("isolation_mode") == "process":
            print("[*] Plugin is Process Isolated. Skipping class import check.")
            return True

        # Check Entrypoint
        entrypoint = data.get("entrypoint")
        print(f"[*] Entrypoint: {entrypoint}")
        
        try:
            mod_name, cls_name = entrypoint.split(":")
        except ValueError:
            print(f"[!] Invalid entrypoint format '{entrypoint}'")
            return None
            
        # Try Import
        file_path = path.parent / f"{mod_name}.py"
        if not file_path.exists():
            print(f"[!] Module file not found: {file_path}")
            return None
            
        print(f"[-] Importing module from {file_path}...")
        spec = importlib.util.spec_from_file_location(mod_name, file_path)
        if not spec or not spec.loader:
            print(f"[!] Failed to create module spec for {file_path}")
            return None
            
        module = importlib.util.module_from_spec(spec)
        sys.modules[mod_name] = module
        spec.loader.exec_module(module)
        print("[+] Module imported successfully")
        
        if not hasattr(module, cls_name):
            print(f"[!] Class '{cls_name}' not found in module '{mod_name}'")
            return None
            
        cls = getattr(module, cls_name)
        print(f"[+] Class found: {cls}")
        
        try:
            instance = cls()
            print(f"[+] Instantiation successful: {instance.name} (ID: {instance.id})")
            
            # MOCK CONTEXT for Initialize
            class MockContext:
                def register_service(self, name, svc):
                    print(f"    [Mock] Registered service: {name}")
                def get_data_dir(self, pid):
                    p = Path("temp_data")
                    p.mkdir(exist_ok=True)
                    return p
            
            print("[-] Calling initialize()...")
            instance.initialize(MockContext())
            print("[+] Initialize successful! (Router Setter Logic Check Passed)")
            
        except Exception as e:
            print(f"[!] Instantiation/Init FAILED: {e}")
            import traceback
            traceback.print_exc()
            return None
            
        return True

    except Exception as e:
        print(f"[!] General Failure: {e}")
        import traceback
        traceback.print_exc()
        return None

def main():
    current_dir = os.path.dirname(os.path.abspath(__file__))
    # Assuming tests/ is at root, so .. is root, then python_backend/plugins/system
    plugins_root = Path(current_dir).parent / "python_backend" / "plugins" / "system"
    
    print(f"Plugins Root: {plugins_root}")
    
    voiceprint_dir = plugins_root / "voiceprint"
    if not voiceprint_dir.exists():
        print(f"[!] Voiceprint directory NOT FOUND at {voiceprint_dir}")
        return
        
    manifest_path = voiceprint_dir / "manifest.yaml"
    if not manifest_path.exists():
         print(f"[!] Manifest NOT FOUND at {manifest_path}")
         return

    print("="*60)
    load_from_manifest(manifest_path)
    print("="*60)

if __name__ == "__main__":
    main()
