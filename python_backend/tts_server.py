"""
TTS Server - Modularized with Driver Plugins
"""
import logging
import json
import os
import re
import asyncio
import httpx
from typing import Optional, Dict
from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
from pydantic import BaseModel

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
    allow_origins=["*"],
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
            # Construct path: python_backend/plugins/drivers/tts
            base_dir = os.path.dirname(os.path.abspath(__file__))
            drivers_dir = os.path.join(base_dir, "plugins", "drivers", "tts")
            
            logger.info(f"Scanning for TTS plugins in: {drivers_dir}")
            loaded_drivers = PluginLoader.load_plugins(drivers_dir, BaseTTSDriver)
            
            for driver in loaded_drivers:
                self.drivers[driver.id] = driver
                logger.info(f"Registered TTS Driver: {driver.name} ({driver.id})")
                
        except Exception as e:
            logger.error(f"Failed to load dynamic TTS drivers: {e}")

        # Load Config
        saved_provider = app_settings.tts.provider 
        if not saved_provider or saved_provider not in self.drivers:
             # Fallback logic if preferred is missing
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
    
    # Initialization moved to lifecycle.py
    # await manager.register_drivers()
    logger.info(f"TTS Service Ready.")

@app.on_event("shutdown")
async def shutdown_event():
    if http_client: await http_client.aclose()

@app.post("/generate")
async def generate_tts(request: TTSRequest):
    """
    Unified Endpoint delegating to active driver.
    """
    from services.container import services
    manager = services.get_tts()

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
        
        # 2. Remove emojis (Basic Range)
        clean_text = re.sub(r'[\U00010000-\U0010ffff]', '', clean_text) 
        
        # 3. Fix All-Caps words (LUMINA -> Lumina) to prevent spelling out
        def fix_caps(m):
            return m.group(0)[0] + m.group(0)[1:].lower()
        clean_text = re.sub(r'\b([A-Z]{2,})\b', fix_caps, clean_text)
        
        # 4. Remove symbols like '&' and normalize whitespace
        clean_text = re.sub(r'[&]', ' ', clean_text)
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
async def synthesize_proxy(request: TTSRequest):
    return await generate_tts(request)

@app.get("/models/list")
async def list_models():
    """List available drivers and their status."""
    from services.container import services
    manager = services.get_tts()
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
async def switch_model(req: SwitchRequest):
    driver_id = req.driver_id or req.model_name
    if not driver_id:
         raise HTTPException(status_code=400, detail="Missing driver_id or model_name")
    
    from services.container import services
    manager = services.get_tts()
    
    if driver_id not in manager.drivers:
        raise HTTPException(404, "Driver not found")
    await manager.activate(driver_id)
    return {"status": "ok", "active": driver_id}

@app.get("/tts/voices")
async def list_voices(engine: Optional[str] = None):
    """
    Proxy to get voices from specific engine or active driver.
    Compatibility endpoint for frontend.
    """
    from services.container import services
    manager = services.get_tts()

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
    
    # Fallback for drivers without voices list (like GPT-SoVITS dynamic?)
    # or return empty list
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
