"""
Soul/人格 相关路由
包含: /soul, /soul/mutate, /soul/switch_character, /galgame 等
"""
import os
import json
import logging
from typing import Dict, Optional
from pydantic import BaseModel
from fastapi import APIRouter, HTTPException, BackgroundTasks

from schemas.requests import UpdateIdentityRequest, UpdateUserNameRequest

logger = logging.getLogger("SoulRouter")

router = APIRouter(tags=["Soul"])

# 全局引用（由 main.py 注入）
# 全局引用（由 main.py 注入）
memory_clients: Dict = {}
soul_client = None
heartbeat_service_instance = None
config_timestamps: Dict = {}


def inject_dependencies(soul, heartbeat, timestamps: Dict):
    """由 main.py 调用，注入全局依赖"""
    global soul_client, heartbeat_service_instance, config_timestamps
    soul_client = soul
    heartbeat_service_instance = heartbeat
    config_timestamps = timestamps


class SwitchCharacterRequest(BaseModel):
    character_id: str


@router.get("/soul/{character_id}")
async def get_soul_data(character_id: str):
    """获取AI演化的性格数据（只读）"""
    try:
        from soul_manager import SoulManager
        soul = SoulManager(character_id)
        return soul.soul
    except Exception as e:
        logger.error(f"[API] Error getting soul data: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/galgame/{character_id}/state")
async def get_galgame_state(character_id: str):
    """获取GalGame状态 + 实时Prompt Context"""
    try:
        from soul_manager import SoulManager
        soul = SoulManager(character_id)
        
        # Base GalGame State
        data = soul.state.get("galgame", {}).copy()
        
        # Inject Real-time Context
        data["dynamic_instruction"] = soul.render_dynamic_instruction()
        data["system_prompt"] = soul.render_static_prompt()
        
        return data
    except Exception as e:
        logger.error(f"[API] Error getting galgame state: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/galgame/{character_id}/state")
async def update_galgame_state(character_id: str, state_update: dict):
    """更新GalGame状态"""
    try:
        from soul_manager import SoulManager
        soul = SoulManager(character_id)
        soul.state.setdefault("galgame", {}).update(state_update)
        soul.save_state()
        return {"status": "ok", "character_id": character_id}
    except Exception as e:
        logger.error(f"[API] Error updating galgame state: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/soul")
async def get_soul():
    """获取Soul状态（使用全局 soul_client）"""
    global soul_client
    try:
        if not soul_client:
            raise HTTPException(status_code=500, detail="Soul client not initialized")
        
        # 重新加载以获取最新数据
        soul_client.soul = soul_client._load_soul()
        soul_client.state = soul_client._load_state()
        soul_client.profile = soul_client._merge_profile()
        
        # 注入关系标签
        if "relationship" in soul_client.profile:
            stage_info = soul_client.get_relationship_stage()
            soul_client.profile["relationship"]["current_stage_label"] = stage_info["label"]
        
        # 注入 System Prompt (Static) 和 Dynamic Instruction
        try:
            soul_client.profile["system_prompt"] = soul_client.render_static_prompt()
            soul_client.profile["dynamic_instruction"] = soul_client.render_dynamic_instruction()
        except Exception as e:
            logger.warning(f"[API] Failed to render prompts: {e}")
        
        return soul_client.profile
    except Exception as e:
        logger.error(f"[API] Error in /soul endpoint: {e}")
        raise HTTPException(status_code=500, detail=str(e))
        

@router.post("/soul/mutate")
async def mutate_soul(
    pleasure: float = 0, 
    arousal: float = 0, 
    dominance: float = 0, 
    intimacy: float = 0, 
    energy: float = 0, 
    clear_pending: bool = False
):
    """Debug endpoint to manually adjust soul state"""
    global soul_client
    if pleasure or arousal or dominance:
        soul_client.mutate_mood(d_p=pleasure, d_a=arousal, d_d=dominance)
    if intimacy:
        soul_client.update_intimacy(intimacy)
    if energy:
        soul_client.update_energy(energy)
    if clear_pending:
        soul_client.set_pending_interaction(False)
    return soul_client.profile


@router.post("/heartbeat/reload")
async def reload_heartbeat():
    """重新加载心跳配置"""
    global soul_client, heartbeat_service_instance
    
    try:
        soul_client.config = soul_client._load_config()
        
        if heartbeat_service_instance:
            heartbeat_service_instance.soul = soul_client
            
        logger.info(f"[API] ❤️ Heartbeat config reloaded. Enabled: {soul_client.config.get('heartbeat_enabled')}")
        
        return {
            "status": "ok",
            "heartbeat_enabled": soul_client.config.get("heartbeat_enabled", True),
            "proactive_threshold_minutes": soul_client.config.get("proactive_threshold_minutes", 15.0)
        }
    except Exception as e:
        logger.error(f"[API] Failed to reload heartbeat: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/soul/interact")
async def register_interaction():
    """
    Centralized Endpoint to signal User Activity.
    Called by Frontend whenever user sends a message (regardless of LLM provider).
    Resets the Heartbeat Service's idle timer.
    """
    global soul_client
    try:
        if soul_client:
            soul_client.update_last_interaction()
            return {
                "status": "ok", 
                "timestamp": soul_client.state.get("last_interaction"),
                "message": "Heartbeat reset"
            }
        else:
            raise HTTPException(status_code=503, detail="Soul Service not ready")
    except Exception as e:
        logger.error(f"[API] Interaction update failed: {e}")
        # Don't bloat frontend with 500s for a background signal
        return {"status": "error", "detail": str(e)}


@router.post("/soul/switch_character")
async def switch_character(request: SwitchCharacterRequest):
    """切换到指定角色"""
    global soul_client, memory_clients, config_timestamps, heartbeat_service_instance
    
    try:
        from soul_manager import SoulManager
        # from lite_memory import LiteMemory (Removed)
        # from dreaming_legacy import DreamingService (Removed)
        
        character_id = request.character_id
        logger.info(f"[API] Switching to character: {character_id}")
        
        # 重置防抖时间戳
        config_timestamps[character_id] = 0.0
        
        # 1. 重新初始化 SoulManager
        soul_client = SoulManager(character_id=character_id)
        soul_client.soul = soul_client._load_soul()
        soul_client.state = soul_client._load_state()
        soul_client.profile = soul_client._merge_profile()
        
        character_name = soul_client.profile.get("identity", {}).get("name", character_id)
        logger.info(f"[API] ✅ Switched to character: {character_name}")
        
        # 3. 更新 Heartbeat Service
        if heartbeat_service_instance:
            heartbeat_service_instance.soul = soul_client
            logger.info(f"[API] Heartbeat service updated")

        logger.info(f"[API] Character switch complete for '{character_id}'")
        
        return {
            "status": "success",
            "character_id": character_id,
            "character_name": character_name,
            "system_prompt": soul_client.render_static_prompt(),
            "dynamic_instruction": soul_client.render_dynamic_instruction()
        }
    except Exception as e:
        logger.error(f"[API] Failed to switch character: {e}")
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=str(e))





@router.post("/soul/update_identity")
async def update_identity(request: UpdateIdentityRequest):
    """更新身份信息"""
    global soul_client
    try:
        soul_client.profile["identity"]["name"] = request.name
        soul_client.profile["identity"]["description"] = request.description
        soul_client.save_profile()
        logger.info(f"[API] Updated identity: name={request.name}")
        return {"status": "updated", "identity": soul_client.profile["identity"]}
    except Exception as e:
        logger.error(f"[API] Failed to update identity: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/soul/update_user_name")
async def update_user_name(request: UpdateUserNameRequest):
    """更新用户名"""
    global soul_client
    try:
        soul_client.profile["relationship"]["user_name"] = request.user_name
        soul_client.save_profile()
        logger.info(f"[API] Updated user_name: {request.user_name}")
        return {"status": "updated", "user_name": request.user_name}
    except Exception as e:
        logger.error(f"[API] Failed to update user_name: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/soul/user_name_bulk")
async def bulk_update_user_name(request: UpdateUserNameRequest):
    """
    Bulk update user_name for ALL characters on disk.
    This avoids N*HTTP requests from frontend.
    """
    try:
        new_name = request.user_name
        base_dir = "characters" # Current working dir relative or absolute?
        # Use relative to file structure or global config?
        # SoulManager uses: Path(__file__).parent / "characters" ...
        # But here we are in routers/soul.py.
        # Let's inspect SoulManager path logic again.
        # SoulManager is in python_backend/soul_manager.py
        # routers/soul.py is in python_backend/routers/soul.py
        
        # We can reuse SoulManager mechanism if efficient, or just iterate dirs.
        # Safest is to iterate dirs in `characters/` relative to project root (or python_backend).
        
        # Correct path resolution:
        # Assuming `python_backend` is root for execution? No, `main.py` is in `python_backend`.
        # `soul_manager.py` says: Path(__file__).parent / "characters" (where __file__ is soul_manager.py)
        # So `characters` is sibling to `soul_manager.py`.
        
        import os
        from pathlib import Path
        
        # Locate characters dir
        # routers/soul.py -> .. -> characters
        # But __file__ in FastAPI might be different? 
        # Safest: Use same anchor as SoulManager.
        
        backend_root = Path(__file__).parent.parent
        chars_dir = backend_root / "characters"
        
        updated_count = 0
        
        if chars_dir.exists():
            for char_dir in chars_dir.iterdir():
                if char_dir.is_dir():
                    state_path = char_dir / "state.json"
                    if state_path.exists():
                        try:
                            with open(state_path, 'r', encoding='utf-8') as f:
                                state = json.load(f)
                            
                            # Deep update
                            if "relationship" not in state:
                                state["relationship"] = {}
                            
                            if state["relationship"].get("user_name") != new_name:
                                state["relationship"]["user_name"] = new_name
                                
                                with open(state_path, 'w', encoding='utf-8') as f:
                                    json.dump(state, f, ensure_ascii=False, indent=2)
                                updated_count += 1
                        except Exception as inner_e:
                            logger.warn(f"Failed to update {char_dir.name}: {inner_e}")
        
        logger.info(f"[API] Bulk updated user_name to '{new_name}' for {updated_count} characters.")
        
        # Also update current active soul in memory
        global soul_client
        if soul_client:
             soul_client.profile.setdefault("relationship", {})["user_name"] = new_name

        return {"status": "ok", "updated_count": updated_count, "user_name": new_name}
        
    except Exception as e:
        logger.error(f"[API] Failed to bulk update user_name: {e}")
        raise HTTPException(status_code=500, detail=str(e))

