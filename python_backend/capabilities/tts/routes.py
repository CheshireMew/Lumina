
import logging
import re
from typing import Any, Optional
from fastapi import APIRouter, HTTPException, Depends, Request
from fastapi.responses import StreamingResponse

from routers.deps import get_tts_service
from app_config import config as app_settings
from core.protocols.lipp import LippProtocol, LippLifecycleRequest, LippConfigRequest
from schemas.api_contracts import TtsModelListResponse, TtsSynthesisRequest, TtsSwitchRequest
from .runtime_state import get_tts_runtime_state

logger = logging.getLogger("TTS_API")
router = APIRouter()

# --- LIPP Handlers ---

async def tts_lifecycle_handler(payload: LippLifecycleRequest):
    """LIPP Lifecycle Implementation"""
    manager = get_tts_runtime_state().tts_manager
    if not manager: return
    
    logger.info(f"📢 [LIPP] Lifecycle: {payload.action} -> {payload.target_id}")
    did = payload.target_id
    
    if payload.action == "disable":
        if manager.is_driver_active(did):
            logger.warning(f"🛑 Active driver {did} disabled remotely. Unloading...")
            await manager.unload_active_driver()
            
    elif payload.action == "enable":
        app_settings.load_configs()
        target = app_settings.get_selected_provider("tts")
        if target == did:
            logger.info(f"🟢 Configured driver {did} enabled remotely. Loading...")
            await manager.activate(did)

async def tts_config_handler(payload: LippConfigRequest):
    """LIPP Config Implementation"""
    manager = get_tts_runtime_state().tts_manager
    
    logger.info("TTS provider config updated: %s -> %s", payload.target_id, payload.key)
    
    config = manager.update_driver_config(payload.target_id, payload.key, payload.value)
    return {"config": config}

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
async def generate_tts(request: TtsSynthesisRequest, manager: Any = Depends(get_tts_service)):
    """Unified Endpoint delegating to active driver."""
    if not manager.active_driver:
        raise HTTPException(status_code=503, detail="No active TTS driver")
        
    driver = manager.active_driver
    if request.engine:
        driver = manager.resolve_driver(request.engine)
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
async def synthesize_proxy(request: TtsSynthesisRequest, manager: Any = Depends(get_tts_service)):
    return await generate_tts(request, manager)

@router.get("/models/list", response_model=TtsModelListResponse)
async def list_models(manager: Any = Depends(get_tts_service)):
    """List available drivers and their status."""
    return {
        "active": manager.active_driver_id,
        "engines": [
            {
                "id": metadata["id"],
                "name": str(metadata.get("name") or metadata["id"]),
                "desc": str(metadata.get("description") or ""),
                "enabled": True,
                "type": "provider",
                "config_schema": metadata.get("config_schema") or {}
            }
            for _, driver in manager.iter_drivers()
            for metadata in [manager.get_driver_metadata(driver.id)]
        ]
    }

@router.post("/models/switch")
async def switch_model(req: TtsSwitchRequest, request: Request, manager: Any = Depends(get_tts_service)):
    driver_id = req.driver_id or req.model_name
    if not driver_id:
         raise HTTPException(status_code=400, detail="Missing driver_id or model_name")

    if not manager.has_driver(driver_id):
        raise HTTPException(404, "Driver not found")
    await manager.activate(driver_id)

    # [Scheme D] Active Notification
    if hasattr(request.app.state, "reporter") and request.app.state.reporter:
        await request.app.state.reporter.force_report()

    return {"status": "ok", "active": driver_id}

@router.get("/voices")
async def list_voices(engine: Optional[str] = None, manager: Any = Depends(get_tts_service)):
    target_driver = manager.active_driver
    if engine:
        try:
            target_driver = manager.resolve_driver(engine)
        except ValueError:
            return []

    if not target_driver:
        return []

    try:
        return await target_driver.list_voices()
    except Exception as e:
        logger.error(f"Error fetching voices from {target_driver.id}: {e}")
        return []
