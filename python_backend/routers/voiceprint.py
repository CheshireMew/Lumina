"""
Voiceprint Management Router (Main Process)

[Architecture 6.0] Scheme C Migration
Voiceprint management APIs moved from STT Worker to Main Process.
- list/toggle/delete: direct database-backed profile operations
- upload: Proxy to STT Worker for embedding generation
"""
import logging
import httpx
from fastapi import APIRouter, UploadFile, File, HTTPException, Query
from app_config import config
from core.runtime import resolve_capability_base_url
from services.voiceprint_store import (
    delete_profile as delete_voiceprint_profile,
    list_profiles as list_voiceprint_profiles,
    set_profile_enabled,
    upsert_profile,
)

logger = logging.getLogger("VoiceprintRouter")
router = APIRouter(prefix="/capabilities/voiceprint", tags=["Voiceprint"])


def _voiceprint_package_status():
    from services.container import services

    registry = services.get_capability_package_registry()
    return registry.resolve("voiceprint-runtime")


def _ensure_voiceprint_available():
    snapshot = _voiceprint_package_status()
    if snapshot is not None and snapshot.status != "ready":
        raise HTTPException(
            status_code=503,
            detail={
                "state": snapshot.status,
                "packageId": "voiceprint-runtime",
                "message": "声纹能力未安装，可在需要时安装",
            },
        )

@router.get("/list")
async def list_profiles():
    """List all voiceprint profiles."""
    _ensure_voiceprint_available()
    try:
        results = await list_voiceprint_profiles()
        profiles = []
        for row in results if isinstance(results, list) else []:
            profiles.append({
                "name": row.get("name"),
                "enabled": row.get("enabled", True),
                "created_at": row.get("created_at"),
            })
        
        return {"profiles": profiles}
    except Exception as e:
        logger.error(f"Failed to list profiles: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/toggle/{name}")
async def toggle_profile(name: str, enabled: bool = Query(...)):
    """Toggle a voiceprint profile's enabled status."""
    _ensure_voiceprint_available()
    try:
        await set_profile_enabled(name, enabled)
        return {"status": "ok", "name": name, "enabled": enabled}
    except Exception as e:
        logger.error(f"Failed to toggle profile {name}: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.delete("/{name}")
async def delete_profile(name: str):
    """Delete a voiceprint profile."""
    _ensure_voiceprint_available()
    try:
        await delete_voiceprint_profile(name)
        return {"status": "ok", "name": name}
    except Exception as e:
        logger.error(f"Failed to delete profile {name}: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/upload")
async def upload_voiceprint(name: str, file: UploadFile = File(...)):
    """
    Upload audio to register a new voiceprint.
    Proxies to STT Worker for embedding generation.
    """
    if ".." in name or "/" in name or "\\" in name:
        raise HTTPException(status_code=400, detail="Invalid profile name")
    _ensure_voiceprint_available()
    
    try:
        # 1. Read audio file
        audio_bytes = await file.read()
        
        # 2. Proxy to STT Worker for embedding generation
        stt_base_url = resolve_capability_base_url(config, "stt")
        if not stt_base_url:
            raise HTTPException(status_code=503, detail="STT worker unavailable")
        url = f"{stt_base_url}/internal/voiceprint/generate-embedding"
        
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.post(
                url,
                files={"audio": (file.filename or "audio.wav", audio_bytes, file.content_type or "audio/wav")}
            )
            
            if response.status_code != 200:
                raise HTTPException(status_code=response.status_code, detail=response.text)
            
            result = response.json()
            embedding_b64 = result.get("embedding")
            
            if not embedding_b64:
                raise HTTPException(status_code=500, detail="No embedding returned from STT Worker")
        
        await upsert_profile(name, embedding_b64, enabled=True)
        
        logger.info(f"✅ Voiceprint registered: {name}")
        return {"status": "ok", "name": name, "message": f"Registered {name}"}
        
    except httpx.ConnectError:
        raise HTTPException(status_code=503, detail="STT Worker offline")
    except Exception as e:
        logger.error(f"Failed to upload voiceprint: {e}")
        raise HTTPException(status_code=500, detail=str(e))
