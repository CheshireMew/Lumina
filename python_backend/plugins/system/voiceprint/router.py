
from fastapi import APIRouter, UploadFile, File, HTTPException, Depends
from typing import List, Dict, Any, TYPE_CHECKING
import logging
import shutil
import os
import tempfile
import numpy as np
import soundfile as sf
from services.container import services

if TYPE_CHECKING:
    from plugins.system.voiceprint.manager import VoiceprintManager

# Plugin-specific router
# Using a relative prefix allows it to be mounted anywhere, but SystemPluginManager usually mounts it at root
# However, lifecycle.py uses app.include_router(plugin.router), so the prefix defined here MATTERS.
# The previous manual mount was fine.
router = APIRouter(prefix="/plugins/voiceprint", tags=["Voiceprint"])
logger = logging.getLogger("VoiceprintRouter")

def get_voiceprint_manager() -> "VoiceprintManager":
    # Access via Plugin Manager
    if not services.system_plugin_manager:
        raise HTTPException(status_code=503, detail="System Plugin Manager not initialized")
    
    plugin = services.system_plugin_manager.get_plugin("system.voiceprint")
    if not plugin:
        raise HTTPException(status_code=404, detail="Voiceprint plugin not found or disabled")
    
    # Cast check
    # Local import to avoid circular dependency at module level
    from plugins.system.voiceprint.manager import VoiceprintManager as VM
    if not isinstance(plugin, VM): 
         raise HTTPException(status_code=500, detail="Plugin type mismatch")
         
    return plugin

@router.get("/list")
async def list_profiles():
    mgr = get_voiceprint_manager()
    profiles = []
    
    # Refresh logic inside manager is safer
    mgr.reload_profiles()

    for name, embedding in mgr.profiles.items():
        enabled = mgr.profile_status.get(name, True)
        path = mgr.profiles_dir / f"{name}.npy"
        created_at = 0
        if path.exists():
            created_at = path.stat().st_mtime * 1000
            
        profiles.append({
            "name": name,
            "enabled": enabled,
            "created_at": created_at
        })
        
    return {"profiles": profiles}

@router.post("/upload")
async def upload_voiceprint(name: str, file: UploadFile = File(...)):
    mgr = get_voiceprint_manager()
    
    try:
        with tempfile.NamedTemporaryFile(delete=False, suffix=".wav") as tmp:
            shutil.copyfileobj(file.file, tmp)
            tmp_path = tmp.name
        
        audio, sr = sf.read(tmp_path)
        if audio.ndim > 1:
            audio = audio[:, 0]
            
        success = await mgr.register_voiceprint(audio, name)
        
        os.remove(tmp_path)
        
        if success:
            return {"status": "ok", "message": f"Registered {name}"}
        else:
            raise HTTPException(status_code=500, detail="Registration failed (Ambiguous audio?)")
            
    except Exception as e:
        logger.error(f"Upload failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/toggle/{name}")
async def toggle_profile(name: str, enabled: bool):
    mgr = get_voiceprint_manager()
    if mgr.toggle_profile(name, enabled):
        return {"status": "ok"}
    else:
        raise HTTPException(status_code=404, detail="Profile not found")

@router.delete("/{name}")
async def delete_profile(name: str):
    mgr = get_voiceprint_manager()
    
    path = mgr.profiles_dir / f"{name}.npy"
    if path.exists():
        path.unlink()
        
    if name in mgr.profiles:
        del mgr.profiles[name]
    if name in mgr.profile_status:
        del mgr.profile_status[name]
        
    mgr._update_metadata(name, enabled=False) 
    mgr.reload_profiles()
    
    return {"status": "ok"}
