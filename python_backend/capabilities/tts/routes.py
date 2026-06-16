
import logging
import re
from typing import Any, Optional, Dict
from fastapi import APIRouter, HTTPException, Depends, Request
from fastapi.responses import StreamingResponse
from pydantic import BaseModel

from routers.deps import get_tts_service
from app_config import config as app_settings
from core.protocols.lipp import LippProtocol, LippLifecycleRequest, LippConfigRequest

logger = logging.getLogger("TTS_API")
router = APIRouter()

# --- Models (Domain Specific) ---
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

class ProviderConfigRequest(BaseModel):
    id: str
    key: str
    value: Any

class LifecyclePayload(BaseModel):
    type: str
    plugin_id: str
    config: Optional[Dict] = None

# --- LIPP Handlers ---

async def tts_lifecycle_handler(payload: LippLifecycleRequest):
    """LIPP Lifecycle Implementation"""
    manager = tts_globals.tts_manager
    if not manager: return
    
    logger.info(f"📢 [LIPP] Lifecycle: {payload.action} -> {payload.target_id}")
    did = payload.target_id
    
    if payload.action == "disable":
        if manager.active_driver and manager.active_driver.id == did:
            logger.warning(f"🛑 Active driver {did} disabled remotely. Unloading...")
            manager.active_driver = None
            manager.active_driver_id = "none"
            
    elif payload.action == "enable":
        app_settings.load_configs()
        target = app_settings.get_selected_provider("tts")
        if target == did:
            logger.info(f"🟢 Configured driver {did} enabled remotely. Loading...")
            if did in manager.drivers:
                await manager.activate(did)

async def tts_config_handler(payload: LippConfigRequest):
    """LIPP Config Implementation"""
    manager = tts_globals.tts_manager
    
    logger.info(f"⚙️ [LIPP] Config: {payload.target_id} -> {payload.key}={payload.value}")
    
    if payload.target_id in manager.drivers:
        driver = manager.drivers[payload.target_id]
        driver.config[payload.key] = payload.value
        return {"config": driver.config}
        
    raise ValueError(f"Driver {payload.target_id} not found")

async def tts_health_check():
    from core.protocols.lipp import LippHealthResponse
    return LippHealthResponse(status="ok")

# --- Mount LIPP Router ---

lipp_router = LippProtocol.create_router(
    service_name="worker:tts",
    lifecycle_handler=tts_lifecycle_handler,
    config_handler=tts_config_handler,
    health_handler=tts_health_check,
    capabilities=["tts"]
)
router.include_router(lipp_router)

# --- Domain Endpoints ---

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

@router.post("/synthesize")
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
        await request.app.state.reporter.force_report()
        
    return {"status": "ok", "active": driver_id}

@router.get("/voices")
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
    # If we need to reset http_client
    # if tts_globals.http_client: ...
    return {"status": "ok"}

# [Legacy Adapters REMOVED - 2026-01-24]
# /provider/config and /system/lifecycle endpoints were removed.
# All clients should use LIPP endpoints (/lipp/v1/*) or Main Process proxy.
