"""
Character Management Router
Includes: /characters, /characters/{id}/config, DELETE /characters/{id}

Refactored: Removed inject_dependencies
"""
import os
import json
import shutil
import logging
from pathlib import Path
from typing import Dict
from fastapi import APIRouter, HTTPException

logger = logging.getLogger("CharacterRouter")

router = APIRouter(prefix="/characters", tags=["Characters"])


def _get_soul_client():
    from services.container import services
    return services.soul_client


@router.get("")
async def list_characters():
    """List all available characters"""
    try:
        # Use relative path to python_backend
        chars_dir = Path(__file__).parent.parent / "characters"
        characters = []
        
        if chars_dir.exists():
            for char_dir in chars_dir.iterdir():
                if char_dir.is_dir():
                    config_path = char_dir / "config.json"
                    if config_path.exists():
                        try:
                            with open(config_path, 'r', encoding='utf-8') as f:
                                config = json.load(f)
                                characters.append(config)
                        except Exception as e:
                            logger.error(f"[API] Error loading character config for {char_dir.name}: {e}")
                            continue
        
        return {"characters": characters}
    except Exception as e:
        logger.error(f"[API] Error listing characters: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/models")
async def list_models():
    """List available Live2D models via Avatar Server"""
    try:
        from services.container import services
        # Try to get avatar_server plugin
        if services.system_plugin_manager:
            plugin = services.system_plugin_manager.get_plugin("system.avatar_server")
            if plugin and hasattr(plugin, "scan_models"):
                 return {"models": plugin.scan_models()}
                 
        return {"models": []}
    except Exception as e:
        logger.error(f"[API] Error listing models: {e}")
        return {"models": []}


@router.get("/{character_id}/config")
async def get_character_config(character_id: str):
    """Get character config"""
    try:
        soul_client = _get_soul_client()
        if soul_client and soul_client.character_id == character_id:
             return soul_client.config

        from soul_manager import SoulManager
        soul = SoulManager(character_id)
        return soul.config
    except Exception as e:
        logger.error(f"[API] Error getting character config: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/{character_id}/config")
async def update_character_config(character_id: str, config: dict):
    """Update character config"""
    soul_client = _get_soul_client()
    try:
        logger.info(f"[API] update_character_config for: {character_id}")
        
        from soul_manager import SoulManager
        soul = SoulManager(character_id)
        
        # Ensure directory exists
        if not soul.base_dir.exists():
            logger.info(f"[API] {character_id} directory missing, creating...")
            soul.base_dir.mkdir(parents=True, exist_ok=True)
            
        soul.config.update(config)
        soul.save_config()
        
        # Sync with global soul_client if it's the active character
        if soul_client and soul_client.character_id == character_id:
             soul_client.config.update(config)
             logger.info(f"[API] Synced config to active soul_client")

        logger.info(f"[API] Config saved for {character_id}")
        return {"status": "ok", "character_id": character_id}
    except Exception as e:
        logger.error(f"[API] Error updating character config: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.delete("/{character_id}")
async def delete_character(character_id: str):
    """Delete character"""
    try:
        # Prevent deleting default character
        if character_id == "hiyori":
             raise HTTPException(status_code=400, detail="Cannot delete default character 'hiyori'")
             
        char_dir = Path(__file__).parent.parent / "characters" / character_id
        
        if char_dir.exists() and char_dir.is_dir():
            shutil.rmtree(char_dir)
            logger.info(f"[API] Deleted character directory: {char_dir}")
            
            return {"status": "ok", "message": f"Character {character_id} deleted"}
        else:
            return {"status": "skipped", "message": "Character not found"}
            
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"[API] Error deleting character: {e}")
        raise HTTPException(status_code=500, detail=str(e))
