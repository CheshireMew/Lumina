import logging

from fastapi import APIRouter, HTTPException
from fastapi.responses import FileResponse
from pathlib import Path
from core.security.safe_path import SafePath, SecurityException
from services.container import services

logger = logging.getLogger("PluginAssets")
router = APIRouter(prefix="/plugins/assets", tags=["Plugin Assets"])

@router.get("/{plugin_id}/{file_path:path}")
async def get_plugin_asset(plugin_id: str, file_path: str):
    """
    Serve static assets for a specific ACTIVE plugin.
    Enforces security:
    1. Plugin must be enabled.
    2. Path must be within plugin's directory.
    """
    
    # 1. Resolve Plugin
    # We use SystemPluginManager to find the plugin object
    # (And conceptually MCPs in future, but they are remote)
    spm = services.system_plugin_manager
    if not spm:
        raise HTTPException(503, "Plugin Manager unavailable")
        
    plugin = spm.get_plugin(plugin_id)
    if not plugin:
        raise HTTPException(404, "Plugin not found or not active")
        
    if not plugin.enabled:
        raise HTTPException(403, "Plugin is disabled")

    # 2. Resolve Path
    manifest = getattr(plugin, '_manifest', None) or getattr(plugin, 'manifest', None)
    
    # [Security] Strict Validation of Manifest
    if callable(manifest):
        try:
            manifest = manifest()
        except Exception:
            raise HTTPException(404, "Failed to resolve manifest")

    if not manifest:
        # Prevent accessing properties on incomplete objects
        raise HTTPException(404, "Invalid plugin manifest")

    if not hasattr(manifest, 'path') or not manifest.path:
        raise HTTPException(404, "Plugin has no asset directory")
        
    plugin_root = Path(manifest.path).resolve()

    # 3. Security Check (SafePath)
    # [Security] SafePath ensures we don't escape plugin_root
    try:
        requested_path = SafePath.resolve_child(plugin_root, file_path)
    except SecurityException:
        logger.warning(f"🚨 Path Traversal Attempt: {plugin_id} -> {file_path}")
        raise HTTPException(403, "Access denied")
        
    if not requested_path.exists() or not requested_path.is_file():
        raise HTTPException(404, "File not found")
        
    return FileResponse(requested_path)
