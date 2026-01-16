
import os
import logging
from pathlib import Path
from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import FileResponse, JSONResponse

router = APIRouter()
logger = logging.getLogger("PluginAssets")

# Base paths
BACKEND_DIR = Path(__file__).parent.parent
PLUGINS_SYSTEM = BACKEND_DIR / "plugins" / "system"
PLUGINS_EXTENSIONS = BACKEND_DIR / "plugins" / "extensions"

@router.get("/plugins/{plugin_id}/assets/{file_path:path}")
async def get_plugin_asset(plugin_id: str, file_path: str):
    """
    Serve static assets for a plugin.
    
    Path resolution:
    1. Try plugins/system/{safe_name}/assets/{file_path}
    2. Try plugins/extensions/{safe_name}/assets/{file_path}
    """
    
    # Security: Sanitization
    safe_name = plugin_id.split(".")[-1] # basic cleanup
    if ".." in plugin_id or "/" in plugin_id or "\\" in plugin_id:
         # If ID is complex like "system.dev.tool", split(".")[-1] gives "tool"
         # If ID is "tool", gives "tool".
         # However, we must ensure we don't traverse directories with the ID itself if it was malformed.
         # The safe_name extraction is checking against the directory structure convention.
         pass

    # Logic: Find the plugin directory
    # 1. System
    sys_path = PLUGINS_SYSTEM / safe_name / "assets" / file_path
    if _is_safe_path(PLUGINS_SYSTEM, sys_path) and sys_path.exists():
        return FileResponse(sys_path)
    
    # 2. Extensions (Try raw ID too if safe_name fails? Usually directories match ID suffix or ID itself)
    # Let's assume directories in extensions/ match safe_name for now. 
    ext_path = PLUGINS_EXTENSIONS / safe_name / "assets" / file_path
    if _is_safe_path(PLUGINS_EXTENSIONS, ext_path) and ext_path.exists():
        return FileResponse(ext_path)

    # 3. Fallback: Try exact ID matches in extensions/ (If folder is named 'system.galgame' not 'galgame')
    # Some folders might include the namespace.
    ext_path_id = PLUGINS_EXTENSIONS / plugin_id / "assets" / file_path
    if _is_safe_path(PLUGINS_EXTENSIONS, ext_path_id) and ext_path_id.exists():
        return FileResponse(ext_path_id)

    raise HTTPException(status_code=404, detail="Asset not found")

def _is_safe_path(base: Path, target: Path) -> bool:
    """Ensure target is within base to prevent traversal."""
    try:
        # resolve() deals with .. and symbolic links
        return base.resolve() in target.resolve().parents
    except Exception:
        return False
