"""
TTS Server - Modularized with Driver Plugins
"""
import logging
import json
import os
import re
import asyncio
import httpx
from fastapi import FastAPI, HTTPException, Request, Depends
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
from typing import Optional, Dict, Any
from routers.deps import get_tts_service

# Plugin System
from core.interfaces.driver import BaseTTSDriver
# Concrete drivers will be loaded dynamically

from app_config import config as app_settings

# Configure Logging
from logger_setup import setup_logger, request_id_ctx
logger = setup_logger("tts_server.log")
import uuid

app = FastAPI(title="Lumina TTS Service")

@app.get("/health")
async def health_check():
    return {"status": "ok", "service": "tts"}

@app.middleware("http")
async def request_id_middleware(request: Request, call_next):
    request_id = request.headers.get("X-Request-ID", str(uuid.uuid4()))
    token = request_id_ctx.set(request_id)
    try:
        response = await call_next(request)
        response.headers["X-Request-ID"] = request_id
        return response
    finally:
        request_id_ctx.reset(token)

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://127.0.0.1", "http://localhost",
        "http://localhost:5173", "http://127.0.0.1:5173",
        "tauri://localhost", "electron://altair"
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

class TTSRequest(BaseModel):
    text: str
    voice: str = "zh-CN-XiaoxiaoNeural"
    emotion: Optional[str] = None
    engine: str = "edge-tts"
    rate: str = "+0%"
    pitch: str = "+0Hz"

class SwitchRequest(BaseModel):
    driver_id: Optional[str] = None
    model_name: Optional[str] = None # Alias for frontend compatibility

# ========== Plugin Manager ==========

class TTSPluginManager:
    def __init__(self):
        self.drivers: Dict[str, BaseTTSDriver] = {}
        self.active_driver_id: str = "edge-tts"
        self.active_driver: Optional[BaseTTSDriver] = None

    async def register_drivers(self, auto_activate: bool = True):
        # Dynamic Loading via PluginLoader
        try:
            from services.plugin_loader import PluginLoader
            from pathlib import Path
            
            base_dir = Path(__file__).parent.resolve()
            
            # 1. Built-in Drivers (Legacy: python_backend/plugins/drivers/tts)
            drivers_dir = base_dir / "plugins" / "drivers" / "tts"
            if drivers_dir.exists():
                logger.info(f"Scanning Built-in TTS Drivers: {drivers_dir}")
                loaded = PluginLoader.load_plugins(str(drivers_dir), BaseTTSDriver)
                for d in loaded: self.drivers[d.id] = d
            
            # 2. Extension Drivers (python_backend/plugins/extensions/*/drivers/tts)
            extensions_root = base_dir / "plugins" / "extensions"
            
            if extensions_root.exists():
                logger.info(f"Scanning Extensions for TTS Drivers in: {extensions_root}")
                for ext_path in extensions_root.iterdir():
                    if ext_path.is_dir():
                         ext_drivers_dir = ext_path / "drivers" / "tts"
                         if ext_drivers_dir.exists():
                             logger.info(f"Scanning Extension Drivers: {ext_drivers_dir}")
                             ext_loaded = PluginLoader.load_plugins(str(ext_drivers_dir), BaseTTSDriver)
                             for d in ext_loaded:
                                 logger.info(f"📦 Loaded Extension Driver from {ext_path.name}: {d.id} ({d.name})")
                                 self.drivers[d.id] = d
            
        except Exception as e:
            logger.error(f"Failed to load dynamic TTS drivers: {e}")

        # Load Config
        saved_provider = app_settings.tts.provider 
        if not saved_provider or saved_provider not in self.drivers:
             # Fallback logic
             if "edge-tts" in self.drivers: saved_provider = "edge-tts"
             elif self.drivers: saved_provider = list(self.drivers.keys())[0]
        
        if saved_provider and auto_activate:
             await self.activate(saved_provider)

    async def activate(self, driver_id: str):
        if not self.drivers:
            logger.critical("No TTS Drivers available! Service running in degraded mode.")
            self.active_driver = None
            self.active_driver_id = "none"
            return

        if driver_id not in self.drivers:
            # Fallback to the first available driver
            fallback = list(self.drivers.keys())[0]
            logger.warning(f"Driver {driver_id} not found, falling back to {fallback}")
            driver_id = fallback
            
        logger.info(f"Activating TTS Driver: {driver_id}")
        driver = self.drivers[driver_id]
        await driver.load()
        self.active_driver = driver
        self.active_driver_id = driver_id

# Global Instance Removed - Use ServiceContainer
# manager = TTSPluginManager()
http_client: Optional[httpx.AsyncClient] = None

@app.on_event("startup")
async def startup_event():
    global http_client
    http_client = httpx.AsyncClient(timeout=httpx.Timeout(60.0, connect=10.0))
    
    # Initialization
    from services.container import services
    
    # 1. Create Manager
    manager = TTSPluginManager()
    
    # 2. Register with Container (So Depends(get_tts_service) works)
    services.register_tts(manager)
    
    # 3. Initialize Drivers
    await manager.register_drivers()
    logger.info(f"TTS Service Ready. Active Driver: {manager.active_driver_id}")

@app.on_event("shutdown")
async def shutdown_event():
    if http_client: await http_client.aclose()

@app.post("/generate")
async def generate_tts(request: TTSRequest, manager: Any = Depends(get_tts_service)):
    """
    Unified Endpoint delegating to active driver.
    """
    # manager injected via DI

    if not manager.active_driver:
        raise HTTPException(status_code=503, detail="No active TTS driver")
        
    # Optional: Override driver per request if 'engine' param is valid
    driver = manager.active_driver
    if request.engine and request.engine in manager.drivers:
        driver = manager.drivers[request.engine]
        # Ensure loaded?
        # Ideally load() is idempotent or cheap if already loaded.
        # But for 'switch', we call activate. Here we just use temporary instance?
        # Drivers are stateful (hold models).
        # We should probably check if it's separate from active
        if driver != manager.active_driver:
             # Just-in-time load for valid request
             await driver.load()

    try:
        # Backend Text Cleaning
        # 1. Remove [emotion] tags and brackets
        # 1. Remove [emotion] tags and brackets
        clean_text = re.sub(r'\[[^\]]*\]', '', request.text)
        # Fix: Properly close character set and use standard Chinese brackets
        clean_text = re.sub(r'[()\[\]（）【】]', '', clean_text)
        
        # 2. Remove emojis and symbols (Expanded Range)
        # Covers: Spec. chars, Dingbats, Emoji, Transport, Symbols
        clean_text = re.sub(r'[\U00010000-\U0010ffff\u2600-\u26ff\u2700-\u27bf\u1f300-\u1f9ff\u1f600-\u1f64f]', '', clean_text) 
        
        # 3. Fix All-Caps words (LUMINA -> Lumina) to prevent spelling out
        def fix_caps(m):
            return m.group(0)[0] + m.group(0)[1:].lower()
        clean_text = re.sub(r'\b([A-Z]{2,})\b', fix_caps, clean_text)
        
        # 4. Remove symbols like '&' and normalize whitespace
        clean_text = re.sub(r'[&]', ' ', clean_text)
        
        # 5. Remove Markdown symbols (*, #, `, ~)
        # Avoid reading out "asterisks" or "hashtags"
        clean_text = re.sub(r'[*#`~]', '', clean_text)
        
        clean_text = re.sub(r'\s+', ' ', clean_text).strip()
        
        # Stream response
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
        
@app.post("/tts/synthesize")
async def synthesize_proxy(request: TTSRequest, manager: Any = Depends(get_tts_service)):
    # Proxy also needs DI if it calls generate_tts? 
    # Actually generate_tts expects 'request' and 'manager'.
    # Proxy logic:
    return await generate_tts(request, manager)

@app.get("/models/list")
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
                "type": "plugin"
            }
            for d in manager.drivers.values()
        ]
    }

@app.post("/models/switch")
async def switch_model(req: SwitchRequest, manager: Any = Depends(get_tts_service)):
    driver_id = req.driver_id or req.model_name
    if not driver_id:
         raise HTTPException(status_code=400, detail="Missing driver_id or model_name")
    
    if driver_id not in manager.drivers:
        raise HTTPException(404, "Driver not found")
    await manager.activate(driver_id)
    return {"status": "ok", "active": driver_id}

@app.get("/tts/voices")
async def list_voices(engine: Optional[str] = None, manager: Any = Depends(get_tts_service)):
    """
    Proxy to get voices from specific engine or active driver.
    """
    target_driver = manager.active_driver
    if engine and engine in manager.drivers:
        target_driver = manager.drivers[engine]
    
    if not target_driver:
        return []
        
    # Check if driver has get_voices method
    if hasattr(target_driver, "get_voices"):
        try:
            voices = await target_driver.get_voices()
            return voices
        except Exception as e:
            logger.error(f"Error fetching voices from {target_driver.id}: {e}")
            return []
    
    return []

@app.get("/health/reset_pool")
async def reset_connection_pool():
    global http_client
    if http_client:
        await http_client.aclose()
        http_client = httpx.AsyncClient(timeout=None)
        return {"status": "ok"}
if __name__ == "__main__":
    import uvicorn
    # Load network config from settings
    port = app_settings.network.tts_port
    host = app_settings.network.host
    uvicorn.run(app, host=host, port=port)
