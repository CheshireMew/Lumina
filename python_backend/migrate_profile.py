"""
数据迁移脚本：将 core_profile.json 拆分为新的文件结构
"""
import json
import os
from pathlib import Path
from datetime import datetime

def migrate_profile():
    """迁移 core_profile.json 到新结构"""
    
    # 1. 读取旧文件
    old_profile_path = Path("python_backend/core_profile.json")
    if not old_profile_path.exists():
        print("[Migration] ❌ core_profile.json not found!")
        return
    
    with open(old_profile_path, 'r', encoding='utf-8') as f:
        old_data = json.load(f)
    
    print("[Migration] ✅ Loaded core_profile.json")
    
    # 2. 创建新目录结构
    character_id = "hiyori"  # 默认角色
    char_dir = Path(f"python_backend/characters/{character_id}")
    char_dir.mkdir(parents=True, exist_ok=True)
    print(f"[Migration] ✅ Created directory: {char_dir}")
    
    # 3. 生成 config.json (用户配置)
    config_data = {
        "character_id": character_id,
        "name": character_id,
        "display_name": "日和",
        "description": "女朋友",
        "system_prompt": "你是一名18岁的傲娇的活泼可爱的女孩子。",
        "live2d_model": "Hiyori (Default)",
        "voice_config": "GPT-SoVITS (Local / Emotional)"
    }
    
    config_path = char_dir / "config.json"
    with open(config_path, 'w', encoding='utf-8') as f:
        json.dump(config_data, f, indent=2, ensure_ascii=False)
    print(f"[Migration] ✅ Created {config_path}")
    
    # 4. 生成 soul.json (AI演化的性格)
    soul_data = {
        "character_id": character_id,
        "personality": old_data.get("personality", {}),
        "state": {
            "current_mood": old_data.get("state", {}).get("current_mood", "neutral")
        },
        "last_updated": datetime.now().isoformat()
    }
    
    soul_path = char_dir / "soul.json"
    with open(soul_path, 'w', encoding='utf-8') as f:
        json.dump(soul_data, f, indent=2, ensure_ascii=False)
    print(f"[Migration] ✅ Created {soul_path}")
    
    # 5. 生成 state.json (GalGame状态)
    state_data = {
        "character_id": character_id,
        "galgame": {
            "relationship": old_data.get("relationship", {
                "level": 1,
                "progress": 0.0,
                "current_stage_label": "陌生人"
            }),
            "energy_level": old_data.get("state", {}).get("energy_level", 100.0),
            "last_interaction": old_data.get("state", {}).get("last_interaction", datetime.now().isoformat())
        }
    }
    
    state_path = char_dir / "state.json"
    with open(state_path, 'w', encoding='utf-8') as f:
        json.dump(state_data, f, indent=2, ensure_ascii=False)
    print(f"[Migration] ✅ Created {state_path}")
    
    # 6. 创建 user_settings.json (全局设置)
    user_settings_data = {
        "user_name": "Master",
        "active_character_id": character_id,
        "ui_settings": {
            "context_window": 15,
            "auto_summarization": True,
            "live2d_high_dpi": False,
            "chat_mode": "voice"
        }
    }
    
    user_settings_path = Path("python_backend/user_settings.json")
    with open(user_settings_path, 'w', encoding='utf-8') as f:
        json.dump(user_settings_data, f, indent=2, ensure_ascii=False)
    print(f"[Migration] ✅ Created {user_settings_path}")
    
    # 7. 备份旧文件
    backup_path = old_profile_path.with_suffix('.json.backup')
    with open(backup_path, 'w', encoding='utf-8') as f:
        json.dump(old_data, f, indent=2, ensure_ascii=False)
    print(f"[Migration] ✅ Backed up to {backup_path}")
    
    print("\n[Migration] ✨ Migration completed successfully!")
    print(f"\n新文件结构:")
    print(f"  {char_dir}/")
    print(f"    ├── config.json   (用户配置)")
    print(f"    ├── soul.json     (AI性格)")
    print(f"    └── state.json    (GalGame状态)")
    print(f"  {user_settings_path} (全局设置)")
    
    return True

if __name__ == "__main__":
    migrate_profile()
