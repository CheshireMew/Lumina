import logging
import httpx
import asyncio
import shutil
import zipfile
import yaml
import os
from pathlib import Path
from typing import List, Dict, Any, Optional

from app_config import config as app_config

logger = logging.getLogger("PluginService")

class PluginService:
    def __init__(self, services_container):
        self.services = services_container

    @property
    def system_plugin_manager(self):
        return getattr(self.services, 'system_plugin_manager', None)

    @property
    def heartbeat_service(self):
        bus = self.services.event_bus
        return bus.get_service("heartbeat_service") if bus else None

    @property
    def mcp_host(self):
        return getattr(self.services, 'mcp_host', None)

    async def list_all_plugins(self) -> List[Dict[str, Any]]:
        """
        Returns a consolidated list of all system capabilities.
        Aggregate from Config, STT/TTS Servers, System Plugins, etc.
        """
        plugins = []

        # 1. System Plugins
        if self.system_plugin_manager:
            try:
                plugins.extend(self.system_plugin_manager.list_plugins())
            except Exception as e:
                logger.error(f"Failed to list system plugins: {e}")

        # 2. TTS Engines
        try:
            async with httpx.AsyncClient(timeout=2.0) as client:
                resp = await client.get(f"{app_config.network.tts_url}/models/list")
                if resp.status_code == 200:
                    data = resp.json()
                    active_id = data.get("active")
                    engines = data.get("engines", [])
                    
                    for eng in engines:
                        pid = eng['id']
                        # Dynamic Schema assignment
                        schema = None
                        if pid == "edge-tts":
                            schema = {
                                "key": "voice_config",
                                "fields": [
                                    {"key": "voiceId", "label": "Voice", "type": "select", "optionSource": "edgeVoices"},
                                    {"key": "rate", "label": "Rate", "type": "text", "default": "+0%"},
                                    {"key": "pitch", "label": "Pitch", "type": "text", "default": "+0Hz"}
                                ]
                            }
                        elif pid == "gpt-sovits":
                            schema = {
                                "key": "voice_config",
                                "fields": [
                                    {"key": "voiceId", "label": "Voice Model", "type": "select", "optionSource": "gptVoices"}
                                ]
                            }

                        plugins.append({
                            "id": pid,
                            "category": "tts",
                            "name": eng["name"],
                            "description": eng["desc"],
                            "enabled": True,
                            "active_in_group": (pid == active_id),
                            "config_schema": schema,
                            "func_tag": "Voice Synthesis",
                            "is_driver": True,
                            "driver_id": pid,
                            "service_url": f"{app_config.network.tts_url}/models/switch",
                            "group_id": "driver.tts"
                        })
        except Exception as e:
            logger.warning(f"Failed to fetch TTS plugins: {e}")
            plugins.append({
                 "id": "tts-error", "category": "tts", "name": "TTS Service Unavailable", 
                 "description": str(e), "enabled": False, "func_tag": "Voice Synthesis"
            })

        # 3. STT Engines
        try:
            async with httpx.AsyncClient(timeout=2.0) as client:
                resp = await client.get(f"{app_config.network.stt_url}/models/list")
                if resp.status_code == 200:
                    data = resp.json()
                    active_id = data.get("active_driver") or data.get("current_model")
                    models = data.get("models", [])
                    
                    faster_whisper_models = []
                    fw_active = False
                    current_fw_size = "base"

                    for m in models:
                        mid = m["name"]
                        is_active = (mid == active_id)

                        if m.get("engine") == "faster_whisper" or m.get("is_whisper"):
                            faster_whisper_models.append(mid)
                            if is_active: 
                                fw_active = True
                                current_fw_size = mid
                        else:
                            plugins.append({
                                "id": mid,
                                "category": "stt",
                                "name": m.get("desc", mid),
                                "description": f"Speech Recognition ({mid})",
                                "enabled": True,
                                "active_in_group": is_active,
                                "config_schema": None,
                                "func_tag": "Speech Recognition",
                                "is_driver": True,
                                "driver_id": mid,
                                "service_url": f"{app_config.network.stt_url}/models/switch",
                                "group_id": "driver.stt"
                            })

                    if faster_whisper_models:
                        fw_options = [
                            {"value": "tiny", "label": "Tiny (Very Fast)"},
                            {"value": "base", "label": "Base (Balanced)"},
                            {"value": "small", "label": "Small (Accurate)"},
                            {"value": "medium", "label": "Medium (Very Accurate)"},
                            {"value": "large-v3", "label": "Large V3 (Most Accurate, Slow)"}
                        ]
                        
                        plugins.append({
                            "id": "faster-whisper-group",
                            "category": "stt",
                            "name": "Faster Whisper",
                            "description": "Standard high-performance recognition. Select model size below.",
                            "enabled": True,
                            "active_in_group": fw_active,
                            "config_schema": {
                                "type": "select",
                                "key": "fw_model_size",
                                "label": "Model Size",
                                "options": fw_options,
                                "confirm_on_change": True 
                            },
                            "current_value": current_fw_size, 
                            "func_tag": "Speech Recognition",
                            "driver_id": current_fw_size, 
                            "service_url": f"{app_config.network.stt_url}/models/switch",
                            "group_id": "driver.stt" 
                        })
        except Exception as e:
            logger.warning(f"Failed to fetch STT plugins: {e}")

        # 4. System Tickers
        if self.heartbeat_service:
            for ticker in self.heartbeat_service.tickers.values():
                schema = getattr(ticker, "config_schema", None)
                val = None
                if schema:
                    if hasattr(ticker, "config"):
                        val = ticker.config
                    else:
                        val = getattr(ticker, "current_value", None)
                else:
                    schema = {"type": "number", "key": f"{ticker.id}:timeout_seconds", "label": "Interval (Sec)"}
                    val = getattr(ticker, "timeout_seconds", getattr(ticker, "interval", 0))

                plugins.append({
                    "id": ticker.id, 
                    "category": "other",
                    "name": ticker.name,
                    "description": f"System Ticker: {ticker.name}",
                    "enabled": ticker.enabled,
                    "active_in_group": False, 
                    "config_schema": schema,
                    "current_value": val,
                    "func_tag": "System Automation",
                    "group_id": None 
                })

        # 5. MCP Servers
        if self.mcp_host:
            for name, client in self.mcp_host.clients.items():
                plugins.append({
                    "is_driver": False
                })

                # ⚡ Metadata Injection
                # Try to load metadata.json for schema
                mcp_dir = Path(BASE_DIR) / "mcp_servers" / name
                meta_path = mcp_dir / "metadata.json"
                if meta_path.exists():
                    try:
                        with open(meta_path, 'r', encoding='utf-8') as f:
                            meta = json.load(f)
                            # Update last added plugin
                            plugins[-1].update({
                                "name": meta.get("name", plugins[-1]["name"]),
                                "description": meta.get("description", plugins[-1]["description"]),
                                "category": meta.get("category", plugins[-1]["category"]),
                                "config_schema": meta.get("config_schema")
                            })
                    except Exception as e:
                        logger.warning(f"Failed to load metadata for MCP {name}: {e}")
        
        # Apply Overrides (Groups/Categories)
        self._apply_overrides(plugins)
        return plugins

    def _apply_overrides(self, plugins: List[Dict]):
        # Groups
        user_groups = app_config.plugin_groups.assignments
        if user_groups:
            for p in plugins:
                if p['id'] in user_groups:
                    p['group_id'] = user_groups[p['id']]
        
        # Categories
        user_cats = app_config.plugin_groups.custom_categories
        if user_cats:
            for p in plugins:
                if p['id'] in user_cats:
                    p['category'] = user_cats[p['id']]

        # Behaviors
        strict_groups = {"driver.stt", "driver.tts", "search_provider"}
        behaviors = app_config.plugin_groups.group_behaviors
        
        for p in plugins:
            gid = p.get('group_id')
            if gid:
                if gid in behaviors:
                    p['group_exclusive'] = (behaviors[gid] == 'exclusive')
                else:
                    if gid in strict_groups:
                        p['group_exclusive'] = True
                    else:
                        p['group_exclusive'] = True 

    def update_group_assignment(self, pid: str, gid: str):
        if not gid:
            if pid in app_config.plugin_groups.assignments:
                del app_config.plugin_groups.assignments[pid]
        else:
            app_config.plugin_groups.assignments[pid] = gid
        app_config.save()
        return gid

    def update_category_assignment(self, pid: str, category: str):
        valid_cats = ["skill", "stt", "tts", "system", "other"]
        if category not in valid_cats:
             raise ValueError("Invalid category")
        app_config.plugin_groups.custom_categories[pid] = category
        app_config.save()
        return category
    
    def update_group_behavior(self, gid: str, behavior: str):
        if behavior not in ["exclusive", "independent"]:
             raise ValueError("Invalid behavior")
        app_config.plugin_groups.group_behaviors[gid] = behavior
        app_config.save()
        return behavior
    
    def update_system_config(self, key: str, value: Any):
        # Special Case: Voiceprint
        if key == "voiceprint_threshold":
            try:
                val = float(value)
                app_config.audio.voiceprint_threshold = val
                app_config.save()
                return {"status": "ok", "message": f"Voiceprint threshold set to {val}"}
            except Exception as e:
                raise ValueError(f"Invalid value: {e}")

                raise ValueError(f"Invalid value: {e}")

        # General "plugin_id:field" pattern
        if ":" in key:
            target_id, field = key.split(":", 1)
            
            # 0. MCP Servers (Virtual Plugins)
            if target_id.startswith("mcp."):
                mcp_name = target_id.split(".", 1)[1]
                # Map mcp.bilibili -> mcp-bilibili (Common convention in config.json)
                module_id = f"mcp-{mcp_name}"
                
                # We need soul_client to save data
                soul_client = getattr(self.services, "soul_client", None)
                if soul_client:
                    # Load existing
                    data = soul_client.load_module_data(module_id) or {}
                    
                    # Convert types
                    try:
                        if field == "room_id": val = int(value)
                        elif field == "enabled": val = bool(value)
                        else: val = value
                    except:
                        val = value
                        
                    data[field] = val
                    soul_client.save_module_data(module_id, data)
                    logger.info(f"Updated MCP config {module_id}: {field}={val}")
                    
                    # ⚡ Hot Reload/Reconnect Logic could go here?
                    # For now just save.
                    return {"status": "ok", "config": data}
            
            # 1. System Manager
            if self.system_plugin_manager:
                plugin = self.system_plugin_manager.get_plugin(target_id)
                if plugin:
                    val = value
                    try:
                        # Attempt number conversion
                        if str(val).replace('.', '', 1).isdigit() and "." in str(val):
                             val = float(val) 
                    except:
                        pass
                        
                    plugin.update_config(field, val)
                    logger.info(f"Updated plugin {target_id} config: {field}={val}")
                    return {"status": "ok", "config": plugin.config}

            # 2. Heartbeat Tickers
            if self.heartbeat_service:
                ticker = self.heartbeat_service.get_ticker(target_id)
                if ticker:
                    try:
                        if field.endswith("seconds") or field.endswith("minutes"):
                            val = float(value)
                        else:
                            val = value
                    except:
                        val = value
                        
                    ticker.config[field] = val
                    if field == "enabled":
                        ticker.enabled = bool(val)
                    return {"status": "ok", "config": ticker.config}
        
        return {"status": "error", "message": "Plugin or Ticker not found"}

    async def toggle_plugin(self, provider_id: str):
        # STT Special Case
        if provider_id == "faster-whisper-group":
            try:
                 async with httpx.AsyncClient(timeout=5.0) as client:
                     url = f"{app_config.network.stt_url}/models/switch"
                     payload = {"model_name": "base"}
                     resp = await client.post(url, json=payload)
                     if resp.status_code == 200:
                         return {"status": "ok", "state": True, "details": resp.json()}
                     else:
                         raise RuntimeError(f"STT Server Error: {resp.text}")
            except Exception as e:
                raise RuntimeError(f"Failed to contact STT Server: {e}")

        # System Manager
        if self.system_plugin_manager:
            plugin = self.system_plugin_manager.get_plugin(provider_id)
            if plugin:
                new_state = not plugin.enabled
                success = self.system_plugin_manager.set_plugin_state(provider_id, new_state)
                if success:
                    return {"status": "ok", "state": new_state}
                else:
                    raise RuntimeError("Failed to toggle plugin state (Manager refused)")

        # Heartbeat
        if self.heartbeat_service:
             ticker = self.heartbeat_service.get_ticker(provider_id)
             if ticker:
                 if ticker.enabled:
                     ticker.stop()
                     return {"status": "ok", "state": False}
                 else:
                     ticker.start()
                     return {"status": "ok", "state": True}
        
        raise ValueError("System plugin not found")

    async def install_plugin_from_zip(self, file_obj, filename: str):
        if not filename.endswith('.zip'):
             raise ValueError("Only .zip files are supported")
        
        temp_zip_path = Path(f"temp_plugin_upload_{filename}")
        try:
            # Save
            await asyncio.to_thread(self._save_file_sync, file_obj, temp_zip_path)
            # Extract
            plugin_id = await asyncio.to_thread(self._extract_zip_sync, temp_zip_path)
            
            # Hot Reload
            if self.system_plugin_manager:
                 logger.info(f"Triggering Hot Reload for {plugin_id}")
                 success = await asyncio.to_thread(self.system_plugin_manager.reload_plugin, plugin_id)
                 if success:
                     return {"status": "success", "id": plugin_id, "message": "Installed and loaded."}
                 else:
                     return {"status": "warning", "id": plugin_id, "message": "Installed but failed to load."}
            
            return {"status": "success", "id": plugin_id, "message": "Installed. Restart backend to load."}
            
        finally:
            if temp_zip_path.exists():
                try:
                    os.remove(temp_zip_path)
                except: pass

    def _save_file_sync(self, src, dest: Path):
        with open(dest, "wb") as buffer:
            shutil.copyfileobj(src, buffer)

    def _extract_zip_sync(self, zip_path: Path) -> str:
        plugin_id = None
        with zipfile.ZipFile(zip_path, 'r') as zip_ref:
            file_list = zip_ref.namelist()
            manifest_path = next((f for f in file_list if f.endswith("manifest.yaml")), None)
            
            if not manifest_path:
                raise ValueError("No manifest.yaml found")
                
            # Determine logic for root detection (simplified from original for brevity but robust enough)
            extract_root = ""
            if '/' in manifest_path:
                 extract_root = manifest_path.rsplit('/', 1)[0]
            
            with zip_ref.open(manifest_path) as mf:
                data = yaml.safe_load(mf)
                plugin_id = data.get("id")
                if not plugin_id: raise ValueError("Missing ID in manifest")

            safe_dirname = plugin_id.split(".")[-1]
            target_dir = Path(f"plugins/system/{safe_dirname}")
            
            if target_dir.exists():
                shutil.rmtree(target_dir)
            target_dir.mkdir(parents=True, exist_ok=True)
            
            for member in zip_ref.infolist():
                if member.filename.startswith("__MACOSX"): continue
                
                # Extraction logic logic matching original
                fname = member.filename
                if extract_root and fname.startswith(extract_root + '/'):
                     fname = fname[len(extract_root)+1:]
                elif extract_root and not fname.startswith(extract_root):
                     continue # Skip files outside root?
                
                if not fname: continue
                
                target_path = target_dir / fname
                if member.is_dir():
                    target_path.mkdir(parents=True, exist_ok=True)
                else:
                    target_path.parent.mkdir(parents=True, exist_ok=True)
                    with zip_ref.open(member) as src, open(target_path, "wb") as dst:
                        shutil.copyfileobj(src, dst)
                        
        return plugin_id
