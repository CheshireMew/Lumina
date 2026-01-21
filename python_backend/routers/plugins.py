import logging
from fastapi import APIRouter, HTTPException, UploadFile, File
from pydantic import BaseModel
from typing import List, Optional, Dict, Any, Union

from services.plugin_service import PluginService

logger = logging.getLogger("PluginAPI")
router = APIRouter(prefix="/plugins", tags=["Plugins"])

# --- Models ---
class ConfigUpdate(BaseModel):
    key: str
    value: Any

class ProviderUpdate(BaseModel):
    provider_id: str

class ToggleRequest(BaseModel):
    id: str # Renamed for clarity
    enabled: Optional[bool] = None

class PluginConfigRequest(BaseModel):
    id: str
    key: str
    value: Any

# --- Helper ---
def _get_service():
    from services.container import services
    return services.get_plugin_service()

# --- Endpoints ---

@router.get("/list")
async def list_plugins():
    svc = _get_service()
    return await svc.list_all_plugins()

@router.get("/slots")
async def list_plugin_slots():
    svc = _get_service()
    return {"slots": await svc.get_all_ui_slots()}


@router.post("/config/group")
async def config_plugin_group(update: ConfigUpdate):
    svc = _get_service()
    gid = svc.update_group_assignment(update.key, str(update.value).strip())
    return {"status": "ok", "group_id": gid}

@router.post("/config/category")
async def config_plugin_category(update: ConfigUpdate):
    svc = _get_service()
    try:
        cat = svc.update_category_assignment(update.key, str(update.value).strip())
        return {"status": "ok", "category": cat}
    except ValueError as e:
        raise HTTPException(400, str(e))

@router.post("/config/group_behavior")
async def config_group_behavior(update: ConfigUpdate):
    svc = _get_service()
    try:
        beh = svc.update_group_behavior(update.key, str(update.value).strip())
        return {"status": "ok", "behavior": beh}
    except ValueError as e:
        raise HTTPException(400, str(e))

@router.post("/config/system")
@router.post("/config/plugin") # Unified Endpoint
async def config_plugin(req: PluginConfigRequest):
    svc = _get_service()
    try:
        return await svc.update_config(req.id, req.key, req.value)
    except Exception as e:
        logger.error(f"Config update failed: {e}")
        raise HTTPException(500, str(e))

@router.post("/toggle/system")
@router.post("/toggle") # Unified Endpoint
async def toggle_plugin(req: ToggleRequest):
    svc = _get_service()
    try:
        # Support both 'id' and legacy 'provider_id' if needed, but we renamed in Model
        return await svc.toggle_plugin(req.id, req.enabled)
    except ValueError as e:
        raise HTTPException(404, str(e))
    except RuntimeError as e:
        raise HTTPException(500, str(e))

@router.post("/reload/{plugin_id}")
async def reload_plugin(plugin_id: str):
    """
    Hot reload a plugin without restarting the backend.
    Clears Python module cache and re-loads the plugin from disk.
    """
    svc = _get_service()
    try:
        import asyncio
        success = await asyncio.to_thread(svc.system_plugin_manager.reload_plugin, plugin_id)
        if success:
            return {"status": "success", "id": plugin_id, "message": "Plugin reloaded successfully."}
        else:
            return {"status": "error", "id": plugin_id, "message": "Reload failed. Check logs for details."}
    except Exception as e:
        logger.error(f"Reload failed for {plugin_id}: {e}")
        raise HTTPException(500, str(e))

@router.post("/config/search")
async def set_search_provider(update: ProviderUpdate):
    if update.provider_id not in ["brave", "duckduckgo", "none"]:
        raise HTTPException(400, "Invalid provider")
    
    # 1. Update Config
    from app_config import config as app_config
    app_config.search.provider = update.provider_id
    app_config.save()
    
    # 2. Schema 5 Fix: Auto-Enable the selected skill
    if update.provider_id != "none":
        svc = _get_service()
        try:
            # Force enable without toggling off others (skills can coexist, but this one MUST be on)
            await svc.toggle_plugin(update.provider_id, True)
        except Exception as e:
            logger.warning(f"Failed to auto-enable search provider {update.provider_id}: {e}")

    return {"status": "ok", "provider": update.provider_id}

@router.post("/config/brave-key")
async def set_brave_key(update: ConfigUpdate):
    from app_config import config as app_config
    # [Refactor] Use Generic Settings
    if "brave" not in app_config.plugins.settings:
        app_config.plugins.settings["brave"] = {}
    app_config.plugins.settings["brave"]["api_key"] = str(update.value)
    app_config.save()
    return {"status": "ok"}

@router.post("/upload")
async def upload_plugin(file: UploadFile = File(...)):
    svc = _get_service()
    try:
        return await svc.install_plugin_from_zip(file.file, file.filename)
    except ValueError as e:
        raise HTTPException(400, str(e))
    except Exception as e:
        logger.error(f"Upload failed: {e}")
        raise HTTPException(500, str(e))

# --- Registry (Integration) ---

# --- Models ---
from enum import Enum

class GroupPolicy(str, Enum):
    EXCLUSIVE = "exclusive"
    INDEPENDENT = "independent"

class RegistryPluginItem(BaseModel):
    id: str
    name: Optional[str] = ""
    version: Optional[str] = "0.0.0"
    description: Optional[str] = ""
    category: Optional[str] = "system"
    enabled: bool = False
    active: bool = False # Real-time running state
    active_in_group: bool = False # For mutual exclusion groups
    group_id: Optional[str] = None
    group_policy: GroupPolicy = GroupPolicy.INDEPENDENT
    capabilities: List[str] = [] # e.g. ["stt.provider", "tts.provider", "search.provider"]
    runtime_target: str = "main"
    ui_slots: List[Dict[str, Any]] = []
    config_schema: Optional[Dict[str, Any]] = None
    current_config: Optional[Dict[str, Any]] = None

class RegisterRequest(BaseModel):
    worker_id: str
    host: str = "127.0.0.1"
    port: int
    plugins: List[RegistryPluginItem]

@router.post("/registry")
async def register_worker_capabilities(req: RegisterRequest):
    """
    [Architecture 3.0] Internal endpoint for Keep-Alive/Registration.
    [Deprecated] Scheme C uses Direct DB Write via WorkerStatusReporter.
    """
    logger.warning(f"⚠️ [Deprecation] Worker {req.worker_id} is using legacy /registry HTTP endpoint. Migrate to Direct DB Write.")
    # svc = _get_service()
    # Serialize Pydantic models to dicts for service layer
    # plugins_data = [p.model_dump() for p in req.plugins]
    # await svc.register_capabilities(req.worker_id, plugins_data, host=req.host, port=req.port)
    return {"status": "registered (deprecated)"}

# [Architecture 2.0] Reverse Proxy for Remote Plugins
from fastapi import Request, Response
import httpx

@router.api_route("/{plugin_id}/{path:path}", methods=["GET", "POST", "PUT", "DELETE"])
async def proxy_plugin_request(plugin_id: str, path: str, request: Request):
    """
    Forward requests to remote plugins (e.g. running on STT/TTS Server).
    Example: GET /plugins/voiceprint/list -> STT_Server/plugins/voiceprint/list
    """
    svc = _get_service()
    
    # Resolve Plugin ID
    plugin = svc.system_plugin_manager.get_plugin(plugin_id)
    if not plugin:
         # Try "system." prefix fallback
         plugin = svc.system_plugin_manager.get_plugin(f"system.{plugin_id}")
    
    if not plugin:
        raise HTTPException(404, f"Plugin {plugin_id} not found")

    # Check Target
    manifest = getattr(plugin, '_manifest', None)
    target = getattr(manifest, 'runtime_target', 'main')
    
    if target == 'main':
         # If it falls through here, it means no local route matched.
         # This implies the local plugin didn't register the route or it doesn't exist.
         raise HTTPException(404, f"Local route /{path} not found for {plugin_id}")
         
    # [Architecture 5.2] Dynamic Service Discovery
    from services.infra.service_discovery import discovery
    
    # Resolving fallback ports for startup race conditions
    fallback_port = None
    from app_config import config
    
    if target == 'stt_server':
         fallback_port = config.network.stt_port
    elif target == 'tts_server':
         fallback_port = config.network.tts_port

    try:
        # Resolve base URL (e.g. http://192.168.1.5:8001)
        base_url = discovery.get_url(target, fallback_port=fallback_port)
        url = f"{base_url}/plugins/{plugin_id}/{path}"
    except ValueError:
        # Worker not found and no fallback
        raise HTTPException(502, f"Worker {target} unreachable (Not Discovered)")
    
    try:
        async with httpx.AsyncClient() as client:
             # Headers
             headers = dict(request.headers)
             headers.pop("host", None)
             headers.pop("content-length", None) 
             
             # Body
             content = await request.body()
             
             resp = await client.request(
                 method=request.method,
                 url=url,
                 headers=headers,
                 content=content,
                 params=request.query_params,
                 timeout=10.0
             )
             
             return Response(content=resp.content, status_code=resp.status_code, headers=dict(resp.headers))
    except Exception as e:
        logger.error(f"Proxy Error to {url}: {e}")
        raise HTTPException(502, f"Remote Plugin Error: {e}")
