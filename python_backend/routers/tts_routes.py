
import logging
import re
from typing import Any, Optional, Dict
from fastapi import APIRouter, HTTPException, Depends, Request
from fastapi.responses import StreamingResponse
from pydantic import BaseModel

from routers.deps import get_tts_service
from app_config import config as app_settings

logger = logging.getLogger("TTS_API")
router = APIRouter()

# --- Models ---
class TTSRequest(BaseModel):
    text: str
    voice: str = "zh-CN-XiaoxiaoNeural"
    emotion: Optional[str] = None
    engine: str = "edge-tts"
    rate: str = "+0%"
    pitch: str = "+0Hz"

class SwitchRequest(BaseModel):
    driver_id: Optional[str] = None
    model_name: Optional[str] = None

class PluginConfigRequest(BaseModel):
    id: str
    key: str
    value: Any

class LifecyclePayload(BaseModel):
    type: str
    plugin_id: str
    config: Optional[Dict] = None

# --- Endpoints ---

@router.post("/generate")
async def generate_tts(request: TTSRequest, manager: Any = Depends(get_tts_service)):
    """Unified Endpoint delegating to active driver."""
    if not manager.active_driver:
        raise HTTPException(status_code=503, detail="No active TTS driver")
        
    driver = manager.active_driver
    if request.engine:
        # 1. Direct Lookup
        if request.engine in manager.drivers:
            driver = manager.drivers[request.engine]
        # 2. Lazy Alias (e.g. "edge-tts" -> "driver.tts.edge-tts")
        elif f"driver.tts.{request.engine}" in manager.drivers:
            driver = manager.drivers[f"driver.tts.{request.engine}"]
        # 3. Fallback (e.g. "edge" -> "driver.tts.edge-tts") hack if needed
            
        if driver != manager.active_driver:
             await driver.load()

    try:
        # Backend Text Cleaning
        clean_text = re.sub(r'\[[^\]]*\]', '', request.text)
        clean_text = re.sub(r'[()\[\]（）【】]', '', clean_text)
        # Fix: Use non-raw string properly or standard filtering
        # The previous huge range block was prone to errors. 
        # Let's remove specific ranges known to be emoji/symbols
        clean_text = re.sub(r'[^\w\s,.?!;:"\'-]', '', clean_text, flags=re.UNICODE) 
        
        def fix_caps(m): return m.group(0)[0] + m.group(0)[1:].lower()
        clean_text = re.sub(r'\b([A-Z]{2,})\b', fix_caps, clean_text)
        clean_text = re.sub(r'[&]', ' ', clean_text)
        clean_text = re.sub(r'[*#`~]', '', clean_text)
        clean_text = re.sub(r'\s+', ' ', clean_text).strip()
        
        generator = driver.generate_stream(
            text=clean_text, 
            voice=request.voice,
            emotion=request.emotion,
            rate=request.rate,
            pitch=request.pitch
        )
        return StreamingResponse(generator, media_type="audio/mpeg")
    except Exception as e:
        logger.error(f"TTS Generation Failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/tts/synthesize")
async def synthesize_proxy(request: TTSRequest, manager: Any = Depends(get_tts_service)):
    return await generate_tts(request, manager)

@router.get("/models/list")
async def list_models(manager: Any = Depends(get_tts_service)):
    """List available drivers and their status."""
    return {
        "active": manager.active_driver_id,
        "engines": [
            {
                "id": d.id, 
                "name": d.name, 
                "desc": d.description,
                "enabled": True,
                "type": "plugin",
                "config_schema": d.config_schema
            }
            for d in manager.drivers.values()
        ]
    }

@router.post("/models/switch")
async def switch_model(req: SwitchRequest, request: Request, manager: Any = Depends(get_tts_service)):
    driver_id = req.driver_id or req.model_name
    if not driver_id:
         raise HTTPException(status_code=400, detail="Missing driver_id or model_name")
    
    if driver_id not in manager.drivers:
        raise HTTPException(404, "Driver not found")
    await manager.activate(driver_id)
    
    # [Scheme D] Active Notification
    if hasattr(request.app.state, "reporter") and request.app.state.reporter:
        # Use background task to avoid blocking response? 
        # Actually force_report is async, usually fast. Let's await to be sure it's sent.
        await request.app.state.reporter.force_report()
        
    return {"status": "ok", "active": driver_id}

@router.get("/tts/voices")
async def list_voices(engine: Optional[str] = None, manager: Any = Depends(get_tts_service)):
    target_driver = manager.active_driver
    if engine and engine in manager.drivers:
        target_driver = manager.drivers[engine]
    
    if not target_driver: return []
        
    if hasattr(target_driver, "get_voices"):
        try:
            return await target_driver.get_voices()
        except Exception as e:
            logger.error(f"Error fetching voices from {target_driver.id}: {e}")
            return []
    return []

@router.get("/health/reset_pool")
async def reset_connection_pool():
    # This was previously holding dead loop code. 
    # Now it just signals a reset if needed.
    # We might need access to global http_client from tts_server via services?
    # Or just returning ok is fine for now as internal keepalive.
    return {"status": "ok"}

@router.post("/plugins/config")
async def update_plugin_config(req: PluginConfigRequest, manager: Any = Depends(get_tts_service)):
    """Unified Config Endpoint for Workers"""
    logger.info(f"⚙️ [Worker Config] {req.id} -> {req.key}={req.value}")
    
    if req.id in manager.drivers:
        driver = manager.drivers[req.id]
        driver.config[req.key] = req.value
        return {"status": "ok", "config": driver.config}

    return {"status": "error", "message": f"Plugin {req.id} not found on this worker"}

# --- Scheme D: Lifecycle Broadcast ---
@router.post("/system/lifecycle")
async def handle_lifecycle(payload: LifecyclePayload, request: Request, manager: Any = Depends(get_tts_service)):
    """
    [Scheme D] The 'Shout' Receiver.
    Reacts to Plugin Lifecycle events from the Main Process immediately.
    """
    # [Security] Localhost only
    if request.client.host not in ["127.0.0.1", "::1", "localhost"]:
        raise HTTPException(status_code=403, detail="Access Denied")
    logger.info(f"📢 [Lifecycle] Received: {payload.type} -> {payload.plugin_id}")
    did = payload.plugin_id
    
    if payload.type == "disabled":
        if manager.active_driver and manager.active_driver.id == did:
            logger.warning(f"🛑 Active driver {did} disabled remotely. Unloading...")
            manager.active_driver = None
            manager.active_driver_id = "none"
            
    elif payload.type == "enabled":
        app_settings.load_configs()
        target = app_settings.tts.provider
        if target == did:
            logger.info(f"🟢 Configured driver {did} enabled remotely. Loading...")
            if did in manager.drivers:
                await manager.activate(did)
            else:
                logger.warning(f"Driver {did} enabled but not found in local registry.")

    # [Scheme D] Immediate Registry Update for SSOT Reconciliation
    if hasattr(request.app.state, "reporter") and request.app.state.reporter:
        await request.app.state.reporter.force_report()
        logger.info("🚀 Force-pushed lifecycle result to Registry")

    return {"status": "ok"}
