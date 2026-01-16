"""
Character Management Router
Includes: /characters, /characters/{id}/config, DELETE /characters/{id}

Refactored: Removes SoulManager dependency. Uses direct file operations for config management.
"""
import os
import json
import shutil
import logging
from pathlib import Path
from typing import Dict, Any
from fastapi import APIRouter, HTTPException

logger = logging.getLogger("CharacterRouter")

router = APIRouter(prefix="/characters", tags=["Characters"])


def _get_soul_service():
    from services.container import services
    return services.soul


def _load_char_config(character_id: str) -> Dict[str, Any]:
    """Helper to load config directly from disk without SoulManager"""
    try:
        # Use relative path to python_backend
        base_dir = Path(__file__).parent.parent / "characters" / character_id
        config_path = base_dir / "config.json"
        
        if not config_path.exists():
             raise FileNotFoundError(f"Config not found for {character_id}")
             
        with open(config_path, 'r', encoding='utf-8') as f:
            return json.load(f)
    except Exception as e:
        logger.error(f"Failed to load config for {character_id}: {e}")
        raise

def _save_char_config(character_id: str, new_config: Dict[str, Any]):
    """Helper to save config directly to disk"""
    try:
        base_dir = Path(__file__).parent.parent / "characters" / character_id
        base_dir.mkdir(parents=True, exist_ok=True)
        config_path = base_dir / "config.json"
        
        # Merge if exists
        current_config = {}
        if config_path.exists():
            with open(config_path, 'r', encoding='utf-8') as f:
                current_config = json.load(f)
        
        current_config.update(new_config)
        
        with open(config_path, 'w', encoding='utf-8') as f:
            json.dump(current_config, f, indent=4, ensure_ascii=False)
            
    except Exception as e:
        logger.error(f"Failed to save config for {character_id}: {e}")
        raise


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
                                # Ensure ID is present
                                if "id" not in config:
                                    config["id"] = char_dir.name
                                if "character_id" not in config:
                                    config["character_id"] = char_dir.name
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
        # Try to use helper
        config = _load_char_config(character_id)
        return config
    except FileNotFoundError:
         # Fallback default?
         return {"identity": {"name": character_id}}
    except Exception as e:
        logger.error(f"[API] Error getting character config: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/{character_id}/config")
async def update_character_config(character_id: str, config: dict):
    """Update character config"""
    soul_service = _get_soul_service()
    try:
        logger.info(f"[API] update_character_config for: {character_id}")
        
        # Save to Disk
        _save_char_config(character_id, config)
        
        logger.info(f"[API] Config saved for {character_id}")
        return {"status": "ok", "character_id": character_id}
    except Exception as e:
        logger.error(f"[API] Error updating character config: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/{character_id}/activate")
async def activate_character(character_id: str):
    """Switch active character"""
    soul_service = _get_soul_service()
    try:
        if not soul_service:
            raise HTTPException(status_code=503, detail="Soul Service unavailable")
            
        soul_service.set_active_character(character_id)
        return {
            "status": "ok", 
            "message": f"Switched to {character_id}",
            "character_id": character_id
        }
    except FileNotFoundError:
        raise HTTPException(status_code=404, detail="Character not found")
    except Exception as e:
        logger.error(f"[API] Error switching character: {e}")
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
