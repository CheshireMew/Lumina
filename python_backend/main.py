"""
Lumina Memory Server - Modular Entry
Refactored from memory_server.py
"""
import os
import sys
import json
import uuid
import logging
import asyncio
import uvicorn
import time
from services.container import services as service_instance
from collections import defaultdict
from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app_config import ConfigManager

# Initialize Config
app_settings = ConfigManager()
# service_instance.config = app_settings # Moved to lifespan


# 确保可以导入本地模块
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from vision_service import router as vision_router # Vision API
from routers import gateway # Gateway
from services.vision_service import vision_service, VisionService # Vision
from services.mcp_host import MCPHost


# 配置日志 (Using shared setup)
from logger_setup import setup_logger, request_id_ctx
logger = setup_logger("memory_server.log")

# ========== 全局状态 (Using ServiceContainer) ==========

# from services.lifecycle import lifespan # Imported below
from services.lifecycle import lifespan

# ========== 创建应用 ==========
app = FastAPI(
    title="Lumina Memory Server",
    description="模块化记忆管理服务",
    version="2.0.0",
    lifespan=lifespan
)

@app.get("/health")
async def health_check():
    return {"status": "ok", "service": "memory"}

# ========== Middleware & Exception Handlers ==========
# (Kept secure middleware from previous steps)

from fastapi.responses import JSONResponse
from fastapi.requests import Request

@app.middleware("http")
async def security_middleware(request: Request, call_next):
    """
    Security Middleware:
    1. Reject non-localhost access to restricted endpoints (/debug, /llm-mgmt)
    """
    path = request.url.path
    client_host = request.client.host if request.client else ""
    
    # Restricted Zones
    RESTRICTED_PREFIXES = ["/debug", "/llm-mgmt", "/admin"]
    
    if any(path.startswith(p) for p in RESTRICTED_PREFIXES):
        # Strict Localhost Check (IPv4 & IPv6)
        if client_host not in ["127.0.0.1", "::1", "localhost"]:
             logger.warning(f"Blocked external access to {path} from {client_host}")
             return JSONResponse(status_code=403, content={"detail": "Access Denied: Localhost only."})

    return await call_next(request)

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

@app.exception_handler(ValueError)
async def value_error_handler(request: Request, exc: ValueError):
    """Business Logic / Validation Errors -> 400"""
    logger.warning(f"⚠️ Bad Request on {request.url}: {exc}") # No stack trace for usage errors
    return JSONResponse(
        status_code=400,
        content={"message": "Bad Request", "detail": str(exc)},
    )

@app.exception_handler(PermissionError)
async def permission_error_handler(request: Request, exc: PermissionError):
    """Security Errors -> 403"""
    logger.warning(f"🚫 Forbidden Access on {request.url}: {exc}")
    return JSONResponse(
        status_code=403,
        content={"message": "Forbidden", "detail": str(exc)},
    )

@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    """Catch-all for 500s"""
    logger.critical(f"🔥 Global Panic on {request.url}: {exc}", exc_info=True)
    return JSONResponse(
        status_code=500,
        content={"message": "Internal Server Error", "detail": str(exc) if app_settings.is_dev else "Internal Error"},
    )

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"] if app_settings.is_dev else [
        "http://127.0.0.1", "http://localhost",
        "http://localhost:5173", "http://127.0.0.1:5173",
        "tauri://localhost", "electron://altair"
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ========== 注册路由 ==========
from routers import (
    debug, 
    memory, 
    soul, 
    config, 
    gateway, 
    plugins, 
    llm_mgmt, 
    characters, 
    completions,
    admin,
    plugin_assets
)
from fastapi.staticfiles import StaticFiles

# [Removed] chat.router - DEPRECATED, use completions.router
app.include_router(memory.router)
app.include_router(soul.router)
# app.include_router(debug.router) # Keep debug for brain_dump? Yes, task says clean up endpoints, not file.
app.include_router(debug.router) 
app.include_router(config.router)
app.include_router(gateway.router)
app.include_router(plugins.router)
app.include_router(llm_mgmt.router)
app.include_router(characters.router)
app.include_router(completions.router)
app.include_router(admin.router) # Free LLM / V1 API
app.include_router(vision_router) # Vision API
app.include_router(plugin_assets.router, prefix="/api") # /api/plugins/{id}/assets/...


# Removed deprecated chat.router (duplicate, use /v1/chat/completions)

# Gateway
service_instance.gateway = gateway.gateway_service

# Live2D Static Files
current_dir = os.path.dirname(os.path.abspath(__file__))
live2d_path = os.path.join(current_dir, "live2d")

# Fallback for Development (../public/live2d)
if not os.path.exists(live2d_path):
    dev_path = os.path.join(current_dir, "..", "public", "live2d")
    if os.path.exists(dev_path):
        live2d_path = dev_path

if os.path.exists(live2d_path):
    app.mount("/live2d", StaticFiles(directory=live2d_path), name="live2d")
    logger.info(f"Mounted Live2D static files from {live2d_path}")
else:
    logger.warning(f"Live2D directory not found. Checked: {live2d_path}")


# ========== Root Endpoint ==========
@app.get("/")
async def root():
    return {
        "service": "Lumina Memory Server",
        "version": "2.0.0",
        "status": "running",
        "endpoints": {
            "config": "/configure, /health",
            "memory": "/add, /search, /search/hybrid, /all",
            "characters": "/characters/*",
            "soul": "/soul/*, /galgame/*, /dream/*",
            "debug": "/debug/brain_dump, /debug/processing_status, /debug/surreal/*"
        }
    }


if __name__ == "__main__":
    from app_config import config
    
    host = "127.0.0.1" if config.network.bind_localhost_only else config.network.host
    logger.info(f"🚀 Starting Server on {host}:{config.network.memory_port} (Localhost Only: {config.network.bind_localhost_only})")
    
    uvicorn.run(app, host=host, port=config.network.memory_port)
