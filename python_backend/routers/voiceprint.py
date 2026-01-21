"""
Voiceprint Management Router (Main Process)

[Architecture 6.0] Scheme C Migration
Voiceprint management APIs moved from STT Worker to Main Process.
- list/toggle/delete: Direct SurrealDB operations
- upload: Proxy to STT Worker for embedding generation
"""
import logging
import httpx
import base64
from fastapi import APIRouter, UploadFile, File, HTTPException, Query
from typing import Optional
from app_config import config
from services.infra.bus_factory import get_lifecycle_bus

logger = logging.getLogger("VoiceprintRouter")
router = APIRouter(prefix="/plugins/voiceprint", tags=["Voiceprint"])

# SurrealDB table name
TABLE = "voiceprint_profiles"


async def _get_db():
    """Get connected lifecycle bus for DB operations."""
    bus = get_lifecycle_bus()
    if not getattr(bus, "_is_connected", False):
        await bus.connect()
    return bus.db


@router.get("/list")
async def list_profiles():
    """List all voiceprint profiles from SurrealDB."""
    try:
        db = await _get_db()
        results = await db.select(TABLE)
        
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
    try:
        db = await _get_db()
        record_id = f"{TABLE}:{name}"
        
        import datetime
        await db.query(
            f"UPDATE {record_id} SET enabled = $enabled, updated_at = $now",
            {"enabled": enabled, "now": datetime.datetime.now(datetime.timezone.utc).isoformat()}
        )
        
        return {"status": "ok", "name": name, "enabled": enabled}
    except Exception as e:
        logger.error(f"Failed to toggle profile {name}: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.delete("/{name}")
async def delete_profile(name: str):
    """Delete a voiceprint profile."""
    try:
        db = await _get_db()
        record_id = f"{TABLE}:{name}"
        
        await db.delete(record_id)
        
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
    
    try:
        # 1. Read audio file
        audio_bytes = await file.read()
        
        # 2. Proxy to STT Worker for embedding generation
        stt_port = config.network.stt_port
        url = f"http://127.0.0.1:{stt_port}/internal/voiceprint/generate-embedding"
        
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
        
        # 3. Save to SurrealDB
        db = await _get_db()
        record_id = f"{TABLE}:{name}"
        
        import datetime
        now = datetime.datetime.now(datetime.timezone.utc).isoformat()
        
        data = {
            "id": record_id,
            "name": name,
            "enabled": True,
            "embedding": embedding_b64,
            "created_at": now,
            "updated_at": now,
        }
        
        await db.query(f"UPDATE {record_id} MERGE $data", {"data": data})
        
        logger.info(f"✅ Voiceprint registered: {name}")
        return {"status": "ok", "name": name, "message": f"Registered {name}"}
        
    except httpx.ConnectError:
        raise HTTPException(status_code=503, detail="STT Worker offline")
    except Exception as e:
        logger.error(f"Failed to upload voiceprint: {e}")
        raise HTTPException(status_code=500, detail=str(e))
