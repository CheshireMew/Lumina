"""
Generic Worker Container (The Kernel)
-------------------------------------
Replaces specialized server scripts (stt_server.py, tts_server.py).
Loads a 'Capability Plugin' to determine its role.

Usage:
    python generic_worker.py --capability stt --port 8001
"""

import sys
import os
import argparse
import asyncio
import uuid
from typing import Optional

# [Windows CUDA Fix] Force Python to look for DLLs in the script directory
if os.name == 'nt':
    try:
        base_path = os.path.dirname(os.path.abspath(__file__))
        os.add_dll_directory(base_path)
    except Exception:
        pass

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from logger_setup import setup_logger, request_id_ctx, session_id_ctx
from app_config import config as app_settings
from services.container import services
from core.interfaces.capability import IWorkerCapability

# --- Infrastructure Globals ---
http_client = None
status_reporter = None
current_capability: Optional[IWorkerCapability] = None

# --- Argument Parsing ---
parser = argparse.ArgumentParser(description="Lumina Generic Worker")
parser.add_argument("--capability", type=str, required=True, help="Capability to load (stt, tts, ocr...)")
parser.add_argument("--port", type=int, help="Override port")
parser.add_argument("--host", type=str, default="127.0.0.1")
# Parse args only if run as main
args = None
if __name__ == "__main__":
    args, _ = parser.parse_known_args()

# --- Logging Setup ---
service_name = args.capability if args else "generic_worker"
logger = setup_logger(f"{service_name}_server.log")

# --- FastAPI App ---
app = FastAPI(title=f"Lumina {service_name.upper()} Service")

# --- Middleware (Standardized) ---
@app.middleware("http")
async def request_id_middleware(request: Request, call_next):
    request_id = request.headers.get("X-Request-ID", str(uuid.uuid4()))
    session_id = request.headers.get("X-Session-ID", "-")
    
    token_rid = request_id_ctx.set(request_id)
    token_sid = session_id_ctx.set(session_id)
    try:
        response = await call_next(request)
        response.headers["X-Request-ID"] = request_id
        response.headers["X-Session-ID"] = session_id
        return response
    finally:
        request_id_ctx.reset(token_rid)
        session_id_ctx.reset(token_sid)

from services.middleware.resource_cleanup import resource_cleanup_middleware
@app.middleware("http")
async def resource_cleanup_bridge(request: Request, call_next):
    return await resource_cleanup_middleware(request, call_next)

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

@app.get("/health")
async def health_check():
    return {"status": "ok", "service": service_name, "capability": current_capability.name if current_capability else "none"}

# --- Capability Config Loading ---
# We need to look up where the capability code lives.
# Convention: python_backend/capabilities/{name}
def load_capability_module(name: str) -> IWorkerCapability:
    # This logic mimics PluginLoader but specific for 'Capabilities' packages
    # For now, we manually map or dynamically import.
    # Let's try dynamic import from 'capabilities.{name}'
    try:
        import importlib
        module_path = f"capabilities.{name}"
        logger.info(f"🔌 Loading Capability Module: {module_path}")
        module = importlib.import_module(module_path)
        
        # Expecting a factory function or class 'Capability'
        if hasattr(module, "Capability"):
            return module.Capability()
        elif hasattr(module, "get_capability"):
            return module.get_capability()
        else:
            raise ImportError(f"Module {module_path} does not export 'Capability' class or 'get_capability' function")
            
    except ImportError as e:
        logger.critical(f"❌ Failed to load capability '{name}': {e}")
        sys.exit(1)

# --- Startup ---
@app.on_event("startup")
async def startup_event():
    global status_reporter, current_capability, http_client
    
    if not args:
        logger.warning("No capability arguments found (Not running as main?)")
        return

    # 1. Load Capability
    current_capability = load_capability_module(args.capability)
    logger.info(f"✨ Loaded Capability: {current_capability.name}")

    # 2. Register Routes
    current_capability.register_routes(app)
    
    # 3. Bootstrap Logic (Manager Init)
    await current_capability.on_startup(app)

    # 4. Infrastructure: Worker Status Reporter
    from services.reporting.worker_reporter import WorkerStatusReporter
    
    # Use config from app_config based on capability name if possible, or fallback
    # But generic worker needs to know which PORT it is running on.
    # We use args.port if provided, else we need a lookup.
    # For MVP, rely on args.
    
    listen_host = args.host
    listen_port = args.port
    
    # Resolve Port from Config if not passed?
    if not listen_port:
        # Fallback to Config Lookup
        if current_capability.name == "stt": listen_port = app_settings.network.stt_port
        elif current_capability.name == "tts": listen_port = app_settings.network.tts_port
        else: listen_port = 8000
    
    status_reporter = WorkerStatusReporter(
        worker_id=f"{current_capability.name}_server",
        main_port=app_settings.network.memory_port,
        state_provider=current_capability.get_state_provider(),
        interval=90,
        host=listen_host,
        port=listen_port
    )
    status_reporter.start()
    app.state.reporter = status_reporter
    logger.info(f"✅ Worker Status Reporter activated (at {listen_host}:{listen_port})")
    
    # 5. Infrastructure: Plugin State Sync
    try:
        from services.plugin_state_sync import PluginStateSync
        
        # We need the 'manager' from the capability. 
        # Interface doesn't enforce exposing the manager directly, but Sync needs it.
        # Let's assume capability has a 'manager' property or we pass the capability itself if it implements the protocols.
        # Ideally, IWorkerCapability should expose `plugin_manager` property or `enable_plugin` methods.
        # Let's verify `IWorkerCapability` later. For now assume capability.manager exists or use services container.
        
        # Convention: The capability registers its manager to `services.{name}`.
        manager = getattr(services, current_capability.name, None)
        
        if manager:
            sync_service = PluginStateSync(
                manager,
                worker_id=f"{current_capability.name}_server",
                expected_target=f"{current_capability.name}_server",
                reporter=status_reporter
            )
            services.plugin_sync = sync_service
            logger.info("[Startup] 🔄 Starting Distributed State Sync...")
            loop = asyncio.get_event_loop()
            loop.create_task(sync_service.start())
        else:
            logger.warning(f"⚠️ Capability {current_capability.name} did not register a manager in services container. PluginSync skipped.")

    except Exception as e:
        logger.error(f"❌ Failed to start PluginStateSync: {e}", exc_info=True)


@app.on_event("shutdown")
async def shutdown_event():
    if status_reporter:
        if asyncio.iscoroutinefunction(status_reporter.stop):
             await status_reporter.stop()
        else:
             status_reporter.stop()
             
    if current_capability:
        await current_capability.on_shutdown()

if __name__ == "__main__":
    import uvicorn
    listen_port = args.port
    if not listen_port:
        if args.capability == "stt": listen_port = app_settings.network.stt_port
        elif args.capability == "tts": listen_port = app_settings.network.tts_port
        else: listen_port = 8000
        
    logger.info(f"🚀 Starting Generic Worker [{args.capability}] on port {listen_port}")
    uvicorn.run(app, host=args.host, port=listen_port)
