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
    provider_id: str

# --- Helper ---
def _get_service():
    from services.container import services
    return PluginService(services)

# --- Endpoints ---

@router.get("/list")
async def list_plugins():
    svc = _get_service()
    return await svc.list_all_plugins()

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
async def config_system_plugin(update: ConfigUpdate):
    svc = _get_service()
    res = svc.update_system_config(update.key, update.value)
    if res["status"] == "error":
        # Maybe 404?
        pass # return as is
    return res

@router.post("/toggle/system")
async def toggle_system_plugin(req: ToggleRequest):
    svc = _get_service()
    try:
        return await svc.toggle_plugin(req.provider_id)
    except ValueError:
        raise HTTPException(404, "Plugin not found")
    except RuntimeError as e:
        raise HTTPException(500, str(e))

@router.post("/config/search")
async def set_search_provider(update: ProviderUpdate):
    # This was simple enough to keep in router? Or move to service?
    # Original kept it simple. But to be consistent, maybe Service should handle it?
    # Original logic:
    # app_config.search.provider = ...
    # I'll stick to original logic here or move to service?
    # I didn't add it to PluginService in previous step.
    # I'll re-implement it briefly here or add to service.
    # It's cleaner to just do it here if it's just config.
    if update.provider_id not in ["brave", "duckduckgo", "none"]:
        raise HTTPException(400, "Invalid provider")
    
    from app_config import config as app_config
    app_config.search.provider = update.provider_id
    app_config.save()
    return {"status": "ok", "provider": update.provider_id}

@router.post("/config/brave-key")
async def set_brave_key(update: ConfigUpdate):
    from app_config import config as app_config
    app_config.brave.api_key = str(update.value)
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
