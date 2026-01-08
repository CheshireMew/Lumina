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
memory_clients: Dict = {}
soul_client = None
dreaming_service = None
heartbeat_service_instance = None
config_timestamps: Dict = {}


def inject_dependencies(clients: Dict, soul, dreamer, heartbeat, timestamps: Dict):
    """由 main.py 调用，注入全局依赖"""
    global memory_clients, soul_client, dreaming_service, heartbeat_service_instance, config_timestamps
    memory_clients = clients
    soul_client = soul
    dreaming_service = dreamer
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
    """获取GalGame状态"""
    try:
        from soul_manager import SoulManager
        soul = SoulManager(character_id)
        return soul.state.get("galgame", {})
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
        
        # 注入动态 system prompt
        try:
            soul_client.profile["system_prompt"] = soul_client.render_system_prompt()
        except Exception as e:
            logger.warning(f"[API] Failed to render system prompt: {e}")
        
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


@router.post("/soul/switch_character")
async def switch_character(request: SwitchCharacterRequest):
    """切换到指定角色"""
    global soul_client, memory_clients, dreaming_service, config_timestamps, heartbeat_service_instance
    
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
        
        # 3. 更新 Heartbeat Service 和 Hippocampus
        if heartbeat_service_instance:
            heartbeat_service_instance.soul = soul_client
            # ⚡ 同步更新 Hippocampus 的 character_id 用于隔离消化
            if heartbeat_service_instance.hippocampus:
                heartbeat_service_instance.hippocampus.character_id = character_id.lower()
                logger.info(f"[API] Hippocampus character_id updated to '{character_id.lower()}'")
            logger.info(f"[API] Heartbeat service updated")

        logger.info(f"[API] Character switch complete for '{character_id}'")
        
        return {
            "status": "success",
            "character_id": character_id,
            "character_name": character_name,
            "system_prompt": soul_client.render_system_prompt()
        }
    except Exception as e:
        logger.error(f"[API] Failed to switch character: {e}")
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/dream/wake_up")
async def trigger_dreaming(background_tasks: BackgroundTasks):
    """触发做梦/整合周期"""
    # Legacy Dreaming Removed.
    return {"status": "disabled", "message": "Legacy Dreaming Service is disabled. Memory digestion is now real-time via Hippocampus."}


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
