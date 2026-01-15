"""
Config Router
Includes: /configure, /health

Refactored: Removed inject_dependencies pattern
Now uses EventBus for service access
"""
import os
import json
import time
import logging
from typing import Dict
from collections import defaultdict
from fastapi import APIRouter, HTTPException

from schemas.requests import ConfigRequest

logger = logging.getLogger("ConfigRouter")

router = APIRouter(tags=["Config"])

# Config state (local to this module, not injected)
_config_timestamps: Dict[str, float] = defaultdict(float)
CONFIG_COOLDOWN = 30  # 30s cooldown


def _get_service(name: str):
    """Helper to get service from EventBus"""
    from core.events.bus import get_event_bus
    bus = get_event_bus()
    return bus.get_service(name) if bus else None


@router.post("/configure")
async def configure_memory(config: ConfigRequest):
    """Configure Memory Service"""
    from soul_manager import SoulManager
    
    character_id = config.character_id
    
    logger.info(f"=== /configure Request Received ===")
    logger.info(f"Character: {character_id}, BaseURL: {config.base_url}, Model: {config.model}")
    
    # Debounce check
    current_time = time.time()
    last_config_time = _config_timestamps.get(character_id, 0)
    if current_time - last_config_time < CONFIG_COOLDOWN:
        elapsed = int(current_time - last_config_time)
        logger.warning(f"⚡ Duplicate /configure blocked (last configured {elapsed}s ago)")
        return {
            "status": "skipped", 
            "message": f"Configuration recently updated {elapsed}s ago. Wait {CONFIG_COOLDOWN}s between configurations."
        }
    
    try:
        # Update timestamp
        _config_timestamps[character_id] = current_time
        
        # Soul Reload
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
        
        # Get services via EventBus
        heartbeat_service = _get_service("heartbeat_service")
        dreaming_service = _get_service("dreaming_service")
        
        # Update Heartbeat Service (In-place)
        if heartbeat_service:
            logger.info("Updating Heartbeat Service for new character...")
            heartbeat_service.soul = soul_client

        # Update Dreaming Service LLM Config
        if dreaming_service:
            dreaming_service.update_llm_config(
                api_key=config.api_key,
                base_url=config.base_url,
                model=config.model
            )
        
        # Save config
        try:
            from app_config import ConfigManager
            cm = ConfigManager()
            
            if config.character_id:
                cm.memory.character_id = config.character_id
            if config.base_url:
                cm.llm.base_url = config.base_url
            if config.api_key:
                cm.llm.api_key = config.api_key
            if config.model:
                cm.llm.model = config.model
            
            cm.save()
            logger.info("✅ Saved configuration via ConfigManager")
            
        except Exception as e:
            logger.error(f"Failed to save config via ConfigManager: {e}")

        logger.info(f"✅ Memory configured successfully for '{character_id}' (Surreal)")
        return {"status": "ok", "message": f"Memory configured for {character_id}"}
    except Exception as e:
        logger.error(f"INIT ERROR: {e}")
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/health")
async def health_check():
    """Health Check"""
    from services.container import services
    return {
        "status": "healthy",
        "soul_client": services.soul_client is not None
    }

@router.get("/network")
async def get_network_config():
    """Returns network port configuration for frontend sync"""
    from app_config import config as app_config
    return {
        "memory_port": app_config.network.memory_port,
        "stt_port": app_config.network.stt_port,
        "tts_port": app_config.network.tts_port,
        "stt_url": app_config.network.stt_url,
        "tts_url": app_config.network.tts_url,
        "memory_url": app_config.network.memory_url,
        "host": app_config.network.host
    }
