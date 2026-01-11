"""
配置相关路由
包含: /configure, /health
"""
import os
import json
import time
import logging
from typing import Dict
from collections import defaultdict
from fastapi import APIRouter, HTTPException

from schemas.requests import ConfigRequest
# from dreaming_legacy import DreamingService (Archived)

logger = logging.getLogger("ConfigRouter")

router = APIRouter(tags=["Config"])

# 全局引用（由 main.py 注入）
# 全局引用（由 main.py 注入）
soul_client = None
heartbeat_service_instance = None
config_timestamps: Dict = defaultdict(float)
dreaming_service_instance = None

CONFIG_COOLDOWN = 30  # 30秒冷却时间


def inject_dependencies(soul, heartbeat, timestamps: Dict, dreaming=None):
    """由 main.py 调用，注入全局依赖"""
    global soul_client, heartbeat_service_instance, config_timestamps, dreaming_service_instance
    soul_client = soul
    heartbeat_service_instance = heartbeat
    config_timestamps = timestamps
    dreaming_service_instance = dreaming


def get_dependencies():
    """返回当前依赖状态，供 main.py 更新"""
    return {

        "soul_client": soul_client,
        "heartbeat_service_instance": heartbeat_service_instance,
        "config_timestamps": config_timestamps,
        "dreaming_service_instance": dreaming_service_instance
    }


@router.post("/configure")
async def configure_memory(config: ConfigRequest):
    """配置 Memory 服务"""
    global config_timestamps, soul_client, heartbeat_service_instance
    
    # 延迟导入避免循环依赖
    from soul_manager import SoulManager
    # from lite_memory import LiteMemory (Removed)
    # from dreaming_legacy import DreamingService (Removed)
    
    character_id = config.character_id
    
    logger.info(f"=== /configure Request Received ===")
    logger.info(f"Character: {character_id}, BaseURL: {config.base_url}, Model: {config.model}")
    
    # 防抖检查
    current_time = time.time()
    last_config_time = config_timestamps[character_id]
    if current_time - last_config_time < CONFIG_COOLDOWN:
        elapsed = int(current_time - last_config_time)
        logger.warning(f"⚠️ Duplicate /configure blocked (last configured {elapsed}s ago)")
        return {
            "status": "skipped", 
            "message": f"Configuration recently updated {elapsed}s ago. Wait {CONFIG_COOLDOWN}s between configurations."
        }
    
    try:
        # 更新时间戳
        config_timestamps[character_id] = current_time
        
        # 关闭所有现有 memory clients（释放 Qdrant 锁） - NO LONGER NEEDED for Surreal
        # if memory_clients: ...
            
        # 初始化新的 LiteMemory - REMOVED
        # logger.info(f"Initializing LiteMemory for {character_id}...")
        # memory_clients[character_id] = LiteMemory(config.model_dump(), character_id=character_id)
        
        # 初始化 Dreaming Service - REMOVED/DISABLED
        # dreaming_service = ...
        
        # Soul & Heartbeat Reload
        logger.info(f"Switching SoulManager to '{character_id}'...")
        soul_client = SoulManager(character_id=character_id)
        
        # Update Soul Config with Heartbeat Settings (if provided)
        if config.heartbeat_enabled is not None:
            soul_client.config["heartbeat_enabled"] = config.heartbeat_enabled
        if config.proactive_threshold_minutes is not None:
            soul_client.config["proactive_threshold_minutes"] = config.proactive_threshold_minutes
        if config.galgame_mode_enabled is not None:
            soul_client.config["galgame_mode_enabled"] = config.galgame_mode_enabled
        if config.soul_evolution_enabled is not None:
            soul_client.config["soul_evolution_enabled"] = config.soul_evolution_enabled
        soul_client.save_config()
        
        # Update Heartbeat Service (In-place)
        if heartbeat_service_instance:
            logger.info("Updating Heartbeat Service for new character...")
            heartbeat_service_instance.soul = soul_client

        # ⚡ Update Dreaming Service LLM Config
        if dreaming_service_instance:
            dreaming_service_instance.update_llm_config(
                api_key=config.api_key,
                base_url=config.base_url,
                model=config.model
            )
        
        # 保存配置
        try:
            config_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "memory_config.json")
            with open(config_path, 'w', encoding='utf-8') as f:
                json.dump(config.model_dump(), f, indent=4)
            logger.info(f"Saved config to {config_path}")
        except Exception as e:
            logger.warning(f"Failed to save config file: {e}")

        logger.info(f"✅ Memory configured successfully for '{character_id}' (Surreal)")
        return {"status": "ok", "message": f"Memory configured for {character_id}"}
    except Exception as e:
        logger.error(f"INIT ERROR: {e}")
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/health")
async def health_check():
    """健康检查"""
    return {
        "status": "healthy",

        "soul_client": soul_client is not None
    }
