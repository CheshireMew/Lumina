import logging
from fastapi import APIRouter, Depends, HTTPException, UploadFile, File
from pydantic import BaseModel
from typing import List, Optional, Dict, Any
from core.schemas.plugin import PluginListResponse
from core.runtime import MAIN_RUNTIME_TARGET, normalize_runtime_target
from routers.deps import get_config_controller, get_plugin_service
from services.provider_aliases import normalize_provider_id


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

# --- Endpoints ---

@router.get("/list", response_model=PluginListResponse)
async def list_plugins(svc=Depends(get_plugin_service)):
    return {"items": await svc.list_all_plugins()}

@router.get("/slots")
async def list_plugin_slots(svc=Depends(get_plugin_service)):
    return {"slots": await svc.get_all_ui_slots()}


@router.get("/capabilities")
async def list_capabilities(svc=Depends(get_plugin_service)):
    return {"items": await svc.get_capability_catalog()}


@router.get("/debug/state")
async def plugin_debug_state(svc=Depends(get_plugin_service)):
    return await svc.get_debug_snapshot()


@router.get("/marketplace")
async def plugin_marketplace_snapshot(svc=Depends(get_plugin_service)):
    return await svc.get_marketplace_snapshot()


@router.post("/config/group")
async def config_plugin_group(update: ConfigUpdate, svc=Depends(get_plugin_service)):
    gid = svc.update_group_assignment(update.key, str(update.value).strip())
    return {"status": "ok", "group_id": gid}

@router.post("/config/category")
async def config_plugin_category(update: ConfigUpdate, svc=Depends(get_plugin_service)):
    try:
        cat = svc.update_category_assignment(update.key, str(update.value).strip())
        return {"status": "ok", "category": cat}
    except ValueError as e:
        raise HTTPException(400, str(e))

@router.post("/config/group_behavior")
async def config_group_behavior(update: ConfigUpdate, svc=Depends(get_plugin_service)):
    try:
        beh = svc.update_group_behavior(update.key, str(update.value).strip())
        return {"status": "ok", "behavior": beh}
    except ValueError as e:
        raise HTTPException(400, str(e))

@router.post("/config/plugin")
async def config_plugin(req: PluginConfigRequest, svc=Depends(get_plugin_service)):
    try:
        return await svc.update_config(req.id, req.key, req.value)
    except Exception as e:
        logger.error(f"Config update failed: {e}")
        raise HTTPException(500, str(e))

@router.post("/toggle")
async def toggle_plugin(req: ToggleRequest, svc=Depends(get_plugin_service)):
    try:
        # Support both 'id' and legacy 'provider_id' if needed, but we renamed in Model
        return await svc.toggle_plugin(req.id, req.enabled)
    except ValueError as e:
        raise HTTPException(404, str(e))
    except RuntimeError as e:
        raise HTTPException(500, str(e))

@router.post("/reload/{plugin_id}")
async def reload_plugin(plugin_id: str, svc=Depends(get_plugin_service)):
    """
    Hot reload a plugin without restarting the backend.
    Clears Python module cache and re-loads the plugin from disk.
    """
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
async def set_search_provider(update: ProviderUpdate, svc=Depends(get_plugin_service), config_service=Depends(get_config_controller)):
    catalog = await svc.get_capability_catalog()
    search_capability = next((item for item in catalog if item.get("capability") == "tool.search"), None)
    valid_ids = {provider["plugin_id"] for provider in (search_capability or {}).get("providers", [])}
    valid_ids.add("none")
    target_provider_id = normalize_provider_id("tool.search", update.provider_id)

    if target_provider_id not in valid_ids:
        raise HTTPException(400, "Invalid provider")
    
    config_service.set_selected_provider("tool.search", target_provider_id)
    
    # 2. Schema 5 Fix: Auto-Enable the selected skill
    if target_provider_id != "none":
        try:
            # Force enable without toggling off others (skills can coexist, but this one MUST be on)
            await svc.toggle_plugin(target_provider_id, True)
        except Exception as e:
            logger.warning(f"Failed to auto-enable search provider {target_provider_id}: {e}")

    return {"status": "ok", "provider": target_provider_id}

@router.post("/config/brave-key")
async def set_brave_key(update: ConfigUpdate, config_service=Depends(get_config_controller)):
    plugin_id = "driver.tool.search.brave"
    config_service.set_plugin_setting(plugin_id, "api_key", str(update.value))
    return {"status": "ok"}

@router.post("/upload")
async def upload_plugin(file: UploadFile = File(...), svc=Depends(get_plugin_service)):
    try:
        return await svc.install_plugin_from_zip(file.file, file.filename)
    except ValueError as e:
        raise HTTPException(400, str(e))
    except Exception as e:
        logger.error(f"Upload failed: {e}")
        raise HTTPException(500, str(e))



# [Architecture 2.0] Reverse Proxy for Remote Plugins
from fastapi import Request, Response
import httpx

@router.api_route(
    "/{plugin_id}/{path:path}",
    methods=["GET", "POST", "PUT", "DELETE"],
    include_in_schema=False,
)
async def proxy_plugin_request(plugin_id: str, path: str, request: Request, svc=Depends(get_plugin_service)):
    """
    Forward requests to remote plugins (e.g. running on STT/TTS Server).
    Example: GET /plugins/voiceprint/list -> STT_Server/plugins/voiceprint/list
    """
    # Resolve Plugin ID
    plugin = svc.system_plugin_manager.get_plugin(plugin_id)
    manifest = svc.system_plugin_manager.get_manifest(plugin_id)
    if not plugin and not manifest:
         plugin = svc.system_plugin_manager.get_plugin(f"system.{plugin_id}")
         manifest = svc.system_plugin_manager.get_manifest(f"system.{plugin_id}")
    
    if not plugin and not manifest:
        raise HTTPException(404, f"Plugin {plugin_id} not found")

    target = normalize_runtime_target(getattr(manifest, 'runtime_target', MAIN_RUNTIME_TARGET) if manifest else MAIN_RUNTIME_TARGET)
    
    if target == MAIN_RUNTIME_TARGET:
         # If it falls through here, it means no local route matched.
         # This implies the local plugin didn't register the route or it doesn't exist.
         raise HTTPException(404, f"Local route /{path} not found for {plugin_id}")
         
    # [Architecture 5.2] Dynamic Service Discovery
    from services.infra.service_discovery import discovery
    
    # Resolving fallback ports for startup race conditions
    try:
        base_url = discovery.get_url(target)
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
