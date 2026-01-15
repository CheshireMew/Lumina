import os
import json
import sys
from pathlib import Path

# Add python_backend to path to ease imports if needed
BACKEND_DIR = Path(__file__).parent.parent
sys.path.append(str(BACKEND_DIR))

CHARACTERS_DIR = BACKEND_DIR / "characters"

def load_json(path: Path):
    if not path.exists(): return {}
    with open(path, 'r', encoding='utf-8') as f:
        return json.load(f)

def save_json(path: Path, data: dict):
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, 'w', encoding='utf-8') as f:
        json.dump(data, f, indent=2, ensure_ascii=False)

def migrate_bilibili(char_id: str, old_config: dict, data_dir: Path):
    if "bilibili" not in old_config: return
    
    print(f"[{char_id}] Migrating Bilibili Config...")
    target_path = data_dir / "mcp-bilibili.json"
    
    # Extract
    bilibili_conf = old_config.pop("bilibili") # Remove from old
    
    # Save to new
    # Merge if exists? usually strictly overwrite or merge defaults
    curr_data = load_json(target_path)
    curr_data.update(bilibili_conf)
    
    save_json(target_path, curr_data)
    print(f"[{char_id}] 鉁?Moved billibili -> data/mcp-bilibili.json")

def migrate_galgame(char_id: str, old_config: dict, data_dir: Path):
    if "galgame_mode_enabled" not in old_config: return
    
    print(f"[{char_id}] Migrating Galgame Switch...")
    target_path = data_dir / "galgame-manager.json"
    
    enabled = old_config.pop("galgame_mode_enabled")
    
    curr_data = load_json(target_path)
    curr_data["enabled"] = enabled
    
    save_json(target_path, curr_data)
    print(f"[{char_id}] 鉁?Moved galgame_mode_enabled ({enabled}) -> data/galgame-manager.json")

def migrate_evolution(char_id: str, old_config: dict, data_dir: Path):
    if "soul_evolution_enabled" not in old_config: return
    
    print(f"[{char_id}] Migrating Evolution Switch...")
    target_path = data_dir / "evolution_engine.json"
    
    enabled = old_config.pop("soul_evolution_enabled")
    
    curr_data = load_json(target_path)
    # Check key? EvolutionEngine might expect "evolution_enabled" or just we check if plugin loaded?
    # Plugin handles loading. If enabled=False, maybe we should stop it?
    # But usually System Plugins are usually actively loaded.
    # Let's just store the config for now. Plugin can read it.
    curr_data["enabled"] = enabled
    
    save_json(target_path, curr_data)
    print(f"[{char_id}] 鉁?Moved soul_evolution_enabled ({enabled}) -> data/evolution_engine.json")


def main():
    print(f"Starting Phase 9 Configuration Decoupling in: {CHARACTERS_DIR}")
    
    if not CHARACTERS_DIR.exists():
        print("Characters dir not found.")
        return

    for item in CHARACTERS_DIR.iterdir():
        if not item.is_dir(): continue
        
        char_id = item.name
        config_path = item / "config.json"
        data_dir = item / "data"
        
        if not config_path.exists(): continue
        
        try:
            config = load_json(config_path)
            changed = False
            
            # 1. Bilibili
            if "bilibili" in config:
                migrate_bilibili(char_id, config, data_dir)
                changed = True
                
            # 2. Galgame
            if "galgame_mode_enabled" in config:
                migrate_galgame(char_id, config, data_dir)
                changed = True
                
            # 3. Evolution
            if "soul_evolution_enabled" in config:
                migrate_evolution(char_id, config, data_dir)
                changed = True
                
            if changed:
                save_json(config_path, config)
                print(f"[{char_id}] 馃捑 Updated config.json")
            else:
                print(f"[{char_id}] No changes needed.")
                
        except Exception as e:
            print(f"[{char_id}] Error: {e}")

if __name__ == "__main__":
    main()
