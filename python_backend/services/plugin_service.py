import logging
import httpx
import asyncio
import shutil
import zipfile
import yaml
import os
import json
from pathlib import Path
from typing import List, Dict, Any, Optional

from app_config import config as app_config
from core.manifest import PluginManifest
from core.events.bus import Event
from services.infra.service_discovery import discovery
from core.events.definitions import PluginLifecycleRequest, PluginLoadedPayload, PluginErrorPayload, PluginDisabledPayload
from core.protocol import EventType

# [Fix] CapabilityType is in schemas
from core.capabilities.schemas import CapabilityType


# [Architecture 3.0] Base Directory
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

logger = logging.getLogger("PluginService")

class PluginService:
    def __init__(self, services_container):
        self.services = services_container
        # [Architecture 5.6] Unified Registry (Plugin-Centric SSOT)
        # keys are plugin_id, values are full plugin states
        self.plugin_registry: Dict[str, Dict[str, Any]] = {}
        
        # [Architecture 5.6] Worker Node Registry (Liveness & Routing)
        # keys are worker_id
        self.worker_registry: Dict[str, Dict[str, Any]] = {}
        
        # [Architecture 31] Watchdog Tracking
        self._last_healthy_workers = set()
        
        # [Architecture 7.0] Centralized State Aggregator
        self._aggregator = None
        self._aggregator_ready = False
        
        # [Architecture 5.0] Background Tasks
        asyncio.create_task(self._watchdog_loop())
        asyncio.create_task(self._start_lifecycle_sync())
        asyncio.create_task(self._init_aggregator())

    async def _start_lifecycle_sync(self):
        """
        [Architecture 5.0] Real-time Sync.
        Listens to the distributed Lifecycle Bus for status 'Shouts'.
        Updates local registry immediately without waiting for heartbeat.
        """
        await asyncio.sleep(5) # Allow bus initialization
        try:
            from services.infra.bus_factory import get_lifecycle_bus
            bus = get_lifecycle_bus()
            
            async for event in bus.subscribe_lifecycle_shouts():
                plugins = event.get("plugins", [])
                worker_id = event.get("worker_id")
                
                # 1. Update Plugin States Individually (Deep Merge)
                for p in plugins:
                    pid = p.get("id")
                    if pid:
                        # Append worker info to plugin state if available
                        if worker_id: p["worker_id"] = worker_id
                        
                        # [Fix] Merge, don't overwrite!
                        if pid in self.plugin_registry:
                            self.plugin_registry[pid].update(p)
                        else:
                            self.plugin_registry[pid] = p

                        # [NEW] Broadcast to Frontend (Fix for Stuck Transitioning State)
                        # We need to compute the "frontend status" (enabled/disabled) based on the new state
                        desired = p.get("enabled", False) 
                        active_status = p.get("active_status", "unknown")
                        
                        # Logic from list_all_plugins to map raw state to UI status
                        computed_status = "disabled"
                        if active_status == "ready" or active_status == "idle":
                             computed_status = "enabled"
                        elif active_status == "stopped":
                             computed_status = "disabled"
                        elif active_status == "error":
                             computed_status = "error"
                        else: 
                             computed_status = active_status # e.g. transitioning, provisioning
                        
                        # Emit Event
                        if self.services.event_bus:
                            # Use fire_and_forget to avoid blocking the sync loop
                            asyncio.create_task(self.services.event_bus.emit(EventType.PLUGIN_STATUS, {
                                "plugin_id": pid,
                                "status": computed_status,
                                "active_status": active_status,
                                "active": desired
                            }))
                        
                        # [Aggregator] Feed worker reports into aggregator
                        if self._aggregator:
                            asyncio.create_task(self._aggregator._merge_state(pid, p, source="worker"))
                
                # 2. Update Worker Node Info (Liveness)
                if worker_id and worker_id != "unknown":
                    host = event.get("host", "127.0.0.1")
                    port = event.get("port")
                    capabilities = event.get("capabilities", [])
                    
                    self.worker_registry[worker_id] = {
                        "host": host,
                        "port": port,
                        "capabilities": capabilities,
                        "last_seen": asyncio.get_event_loop().time()
                    }
                    
                    if port:
                        discovery.register(worker_id, host, port, capabilities=capabilities)
                    
                    # Update watchdog tracker
                    self._last_healthy_workers.add(worker_id)
        except Exception as e:
            logger.error(f"Lifecycle sync error: {e}")
            await asyncio.sleep(10)
            asyncio.create_task(self._start_lifecycle_sync())

    async def _watchdog_loop(self):
        """Active monitoring of worker health"""
        # Delay start to allow initial registration
        await asyncio.sleep(20)
        
        while True:
            try:
                from services.infra.bus_factory import get_lifecycle_bus
                bus = get_lifecycle_bus()
                
                active_records = await bus.get_active_workers(timeout_seconds=15)
                current_active = {r.get("worker_id") for r in active_records if r.get("worker_id")}
                
                # Only track workers we've seen before or core ones
                # For now, we detect transition from Alive -> Dead
                dead = self._last_healthy_workers - current_active
                for wid in dead:
                    logger.warning(f"🚨 [Watchdog] Worker '{wid}' has gone OFFLINE!")
                    # Emit event via Bus
                    if self.services.event_bus:
                        await self.services.event_bus.emit("system.worker.offline", {"worker_id": wid})
                
                # Update tracker with currently alive ones
                self._last_healthy_workers = current_active
                
                # [Monitoring] Periodic stats logging (every 5 cycles = ~50s)
                if not hasattr(self, '_stats_counter'):
                    self._stats_counter = 0
                self._stats_counter += 1
                
                if self._stats_counter % 5 == 0:
                    self._log_memory_stats()
                
                await asyncio.sleep(10)
            except Exception as e:
                logger.error(f"Watchdog error: {e}")
                await asyncio.sleep(20)

    def _log_memory_stats(self):
        """Log memory usage statistics for monitoring."""
        import sys
        
        plugin_count = len(self.plugin_registry)
        worker_count = len(self.worker_registry)
        
        # Estimate memory size (rough)
        plugin_size = sys.getsizeof(self.plugin_registry)
        worker_size = sys.getsizeof(self.worker_registry)
        
        logger.info(
            f"📊 PluginService Memory: "
            f"plugins={plugin_count} (~{plugin_size}B), "
            f"workers={worker_count} (~{worker_size}B)"
        )
        
        # Also log EventBus stats if available
        if self.services.event_bus and hasattr(self.services.event_bus, 'log_stats'):
            self.services.event_bus.log_stats()
        
        # Warn if registries are growing too large
        if plugin_count > 100:
            logger.warning(f"⚠️ Plugin registry has {plugin_count} entries (high)")
        if worker_count > 20:
            logger.warning(f"⚠️ Worker registry has {worker_count} entries (high)")

    async def _init_aggregator(self):
        """Initialize the centralized state aggregator"""
        await asyncio.sleep(3)  # Wait for event bus to be ready
        try:
            from services.plugin_state_aggregator import init_plugin_state_aggregator
            
            if self.services.event_bus:
                self._aggregator = await init_plugin_state_aggregator(self.services.event_bus)
                
                # Set user overrides from config
                self._aggregator.set_overrides(
                    groups=app_config.plugin_groups.assignments,
                    categories=app_config.plugin_groups.custom_categories,
                    behaviors=app_config.plugin_groups.group_behaviors
                )
                
                # Seed initial state from system plugin manager
                await self._seed_aggregator_from_local()
                
                self._aggregator_ready = True
                logger.info("✅ PluginStateAggregator ready")
        except Exception as e:
            logger.error(f"Failed to initialize aggregator: {e}")
    
    async def _seed_aggregator_from_local(self):
        """Populate aggregator with initial plugin states from all sources"""
        if not self._aggregator:
            return
        
        # 1. Local system plugins
        if self.system_plugin_manager:
            local_plugins = self.system_plugin_manager.list_plugins()
            for p in local_plugins:
                p["runtime_target"] = "main"
                p["worker_id"] = "main"
                await self._aggregator._merge_state(p["id"], p, source="local")
        
        # 2. Heartbeat tickers
        if self.heartbeat_service:
            for ticker in self.heartbeat_service.tickers.values():
                ticker_state = {
                    "id": ticker.id,
                    "name": ticker.name,
                    "category": "other",
                    "description": f"System Ticker: {ticker.name}",
                    "desired_enabled": ticker.enabled,
                    "active_status": "ready" if ticker.enabled else "stopped",
                    "group_policy": "independent",
                    "capabilities": ["heartbeat.ticker"],
                    "runtime_target": "main",
                    "worker_id": "main"
                }
                await self._aggregator._merge_state(ticker.id, ticker_state, source="ticker")
        
        # 3. MCP servers
        if self.mcp_host:
            for name, client in self.mcp_host.clients.items():
                pid = f"mcp.{name}"
                mcp_state = {
                    "id": pid,
                    "name": name,
                    "category": "tool",
                    "description": f"MCP Module: {name}",
                    "desired_enabled": True,
                    "active_status": "ready",
                    "group_policy": "independent",
                    "capabilities": ["mcp.tool"],
                    "runtime_target": "main",
                    "worker_id": "main"
                }
                await self._aggregator._merge_state(pid, mcp_state, source="mcp")

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

    async def register_capabilities(self, worker_id: str, capabilities: List[Dict], host: str = "127.0.0.1", port: int = 8000):
        """
        [Architecture 6.0] Schema-Enforced Registration.
        Workers push their active plugins/drivers here via heartbeats.
        """
        REQUIRED_FIELDS = ['id', 'name', 'category', 'runtime_target']
        
        valid_count = 0
        for p in capabilities:
            pid = p.get("id")
            if not pid: continue
            
            # 1. Schema Validation
            missing = [f for f in REQUIRED_FIELDS if f not in p]
            if missing:
                logger.warning(f"⚠️ [Registry] Plugin {pid} from {worker_id} rejected: Missing {missing}")
                continue
            
            # 2. Ingestion
            p["worker_id"] = worker_id
            p.setdefault("enabled", True)
            p.setdefault("active", True)
            
            # [Fix] Deep Merge for Registry Ingestion
            if pid in self.plugin_registry:
                self.plugin_registry[pid].update(p)
            else:
                self.plugin_registry[pid] = p
            
            valid_count += 1
                
        # [Architecture 6.0 - Scheme C]
        # Main Process NO LONGER updates remote worker state in DB.
        # Workers (Mesh Nodes) are responsible for their own liveness via WorkerStatusReporter.
        
        # We only use this payload for Service Discovery (IP/Port) below.
        pass

        try:
            # Capabilities summary for discovery (list of capability strings)
            caps_summary = []
            for p in self.plugin_registry.values():
                if p.get("worker_id") == worker_id:
                    caps_summary.extend(p.get("capabilities", []))
            
            discovery.register(
                worker_id=worker_id,
                host=host,
                port=port,
                capabilities=list(set(caps_summary))
            )
        except Exception as e:
            logger.warning(f"Discovery Registration Failed for {worker_id}: {e}")

        logger.debug(f"[Registry] Worker '{worker_id}' registered {valid_count} capabilities.")
        return True

    async def list_all_plugins(self) -> List[Dict[str, Any]]:
        """
        [Architecture 7.0] Plugin State Query
        Uses centralized aggregator when available, falls back to legacy merge.
        """
        # Fast path: Use aggregator if ready
        if self._aggregator_ready and self._aggregator:
            plugins = self._aggregator.get_snapshot()
            # Enrich remote drivers with service URLs
            for p in plugins:
                target = p.get('runtime_target', 'main')
                if target in ['stt_server', 'tts_server']:
                    p['is_driver'] = True
                    fallback_port = app_config.network.stt_port if target == 'stt_server' else app_config.network.tts_port
                    p['service_url'] = discovery.get_url(target, fallback_port=fallback_port)
            return plugins
        
        # Legacy fallback: Manual aggregation
        logger.debug("[list_all_plugins] Aggregator not ready, using legacy merge")
        plugin_map = {}

        # 1. System Plugin Manager (Local SSOT)
        if self.system_plugin_manager:
            try:
                # spm.list_plugins() already provides live state for local plugins
                for p in self.system_plugin_manager.list_plugins():
                    plugin_map[p['id']] = p
            except Exception as e:
                logger.error(f"Failed to fetch system plugins: {e}")

        # 2. Worker Registry (Distributed SSOT)
        # Ensure registry is fresh (filter dead workers)
        try:
            from services.infra.bus_factory import get_lifecycle_bus
            dist_bus = get_lifecycle_bus()
            active_records = await dist_bus.get_active_workers(timeout_seconds=15)
            active_worker_ids = {r.get("worker_id") for r in active_records if r.get("worker_id")}
            
            # Identify plugins associated with dead workers
            plugins_to_prune = []
            for pid, p in self.plugin_registry.items():
                wid = p.get("worker_id")
                if wid and wid != "main" and wid not in active_worker_ids:
                    plugins_to_prune.append(pid)
            
            for pid in plugins_to_prune:
                logger.info(f"👻 Pruning plugin from dead worker: {pid}")
                self.plugin_registry.pop(pid, None)
                
            # Sync internal worker registry
            self.worker_registry = {wid: info for wid, info in self.worker_registry.items() if wid in active_worker_ids}
            self._last_healthy_workers = active_worker_ids
        except Exception as e:
            logger.warning(f"Liveness check failed: {e}")
            from services.error_monitor import track_error
            track_error(e, context={"component": "PluginService", "operation": "liveness_check"})

        # Overlay registry (Worker reports take precedence)
        for pid, rp in self.plugin_registry.items():
            if pid in plugin_map:
                plugin_map[pid].update(rp)
            else:
                plugin_map[pid] = rp

        # 3. System Tickers (Live State)
        if self.heartbeat_service:
            for ticker in self.heartbeat_service.tickers.values():
                plugin_map[ticker.id] = {
                    "id": ticker.id, 
                    "name": ticker.name,
                    "category": "other",
                    "description": f"System Ticker: {ticker.name}",
                    "enabled": ticker.enabled,
                    "active": ticker.enabled,
                    "group_policy": "independent",
                    "capabilities": ["heartbeat.ticker"],
                    "runtime_target": "main"
                }

        # 4. MCP Servers (Live State)
        if self.mcp_host:
            for name, client in self.mcp_host.clients.items():
                pid = f"mcp.{name}"
                plugin_map[pid] = {
                    "id": pid,
                    "name": name,
                    "category": "tool",
                    "description": f"MCP Module: {name}",
                    "desired_enabled": True,  # Canonical
                    "active_status": "ready",  # Canonical
                    "enabled": True,  # UI Compat
                    "active": True,
                    "group_policy": "independent",
                    "capabilities": ["mcp.tool"],
                    "runtime_target": "main"
                }
                # Enrich with Schema if found
                mcp_dir = Path(app_config.base_dir) / "mcp_servers" / name
                meta_path = mcp_dir / "metadata.json"
                if meta_path.exists():
                     try:
                         import json
                         with open(meta_path, 'r', encoding='utf-8') as f:
                             meta = json.load(f)
                             plugin_map[pid].update({
                                 "description": meta.get("description", plugin_map[pid]["description"]),
                                 "category": meta.get("category", plugin_map[pid]["category"]),
                                 "config_schema": meta.get("config_schema")
                             })
                     except Exception as e:
                         logger.warning(f"Failed to load metadata for MCP {name}: {e}")
        
        plugins = list(plugin_map.values())
        
        # Apply Overrides (Groups/Categories)
        self._apply_overrides(plugins)
        
        # [Architecture 5.0] Post-Processing for Unified Schema
        for p in plugins:
            # 1. Capabilities Inference
            if not p.get('capabilities'):
                gid = p.get('group_id', '')
                cat = p.get('category', '')
                if gid == 'stt' or cat == 'stt': p['capabilities'] = ["stt.provider"]
                elif gid == 'tts' or cat == 'tts': p['capabilities'] = ["tts.provider"]
                elif gid == 'search_provider' or cat == 'search': p['capabilities'] = ["search.provider"]
                else: p['capabilities'] = p.get('capabilities', [])

            # 2. Map Legacy group_exclusive to group_policy if policy missing
            if 'group_exclusive' in p and 'group_policy' not in p:
                p['group_policy'] = "exclusive" if p['group_exclusive'] else "independent"
                
            # [Architecture 6.0] State Synthesis (Controller Logic)
            desired = p.get("desired_enabled")
            # Fallback for migration or locally managed plugins
            if desired is None: desired = p.get("enabled", False)
            
            actual = p.get("active_status", "unknown")
            
            # Compute Status
            computed = "unknown"
            if desired:
                if actual in ["ready", "idle"]: computed = "running"
                elif actual in ["loading", "transitioning"]: computed = "provisioning"
                elif actual == "error": computed = "error"
                else: computed = "stuck" # desired=True, actual=stopped/unknown
            else:
                if actual == "ready": computed = "stopping" # desired=False, actual=ready
                else: computed = "stopped"
            
            p["computed_status"] = computed
            p["enabled"] = desired # UI Compatibility
            
            # 3. Ensure sensible defaults
            p.setdefault('group_policy', "independent")
            p.setdefault('active', p.get('enabled', False))
            p.setdefault('active_in_group', p.get('active', False) if p.get('group_policy') == "exclusive" else False)

            # [Fix] Enrich Remote Drivers for Frontend Toggle Logic
            target = p.get('runtime_target', 'main')
            if target in ['stt_server', 'tts_server']:
                p['is_driver'] = True
                # Resolve Service URL
                fallback_port = app_config.network.stt_port if target == 'stt_server' else app_config.network.tts_port
                # discovery is already imported
                p['service_url'] = discovery.get_url(target, fallback_port=fallback_port)

        return plugins

    def _apply_overrides(self, plugins: List[Dict]):
        # Groups
        user_groups = app_config.plugin_groups.assignments
        if user_groups:
            for p in plugins:
                if 'id' not in p: continue
                if p['id'] in user_groups:
                    p['group_id'] = user_groups[p['id']]
        
        # Categories
        user_cats = app_config.plugin_groups.custom_categories
        if user_cats:
            for p in plugins:
                if p['id'] in user_cats:
                    p['category'] = user_cats[p['id']]

        # Behaviors
        strict_groups = {"stt", "tts", "search_provider"}
        behaviors = app_config.plugin_groups.group_behaviors
        
        for p in plugins:
            gid = p.get('group_id')
            if gid:
                if gid in behaviors:
                    p['group_policy'] = behaviors[gid] # "exclusive" or "independent"
                else:
                    if gid in strict_groups:
                         p['group_policy'] = "exclusive"
                    else:
                         p.setdefault('group_policy', "independent")
            else:
                 p.setdefault('group_policy', "independent")
                    
            # [Scheme C Cleanup] Hardcoded Overrides Removed
            # Logic for determining 'active_in_group' is now decentralized.
            # STT/TTS Servers report this via their Status Reporter.
            # PluginService trusts the registry.
            
            # Legacy logic removed to prevent "Split Brain" overriding valid worker reports.
            pass
            
            # [Fix] Fallback for system plugins moved to drivers (like Voiceprint)
            # If a system plugin is acting as a driver but has no group_id, 
            # we check if it matches the current stt/tts provider anyway.
            # if not gid and p.get('category') == 'driver':
            #    if stt_provider and stt_provider in pid_clean: p['active_in_group'] = True
            #    if tts_provider and tts_provider in pid_clean: p['active_in_group'] = True

    def update_group_assignment(self, pid: str, gid: str):
        if not gid:
            if pid in app_config.plugin_groups.assignments:
                del app_config.plugin_groups.assignments[pid]
        else:
            app_config.plugin_groups.assignments[pid] = gid
        app_config.save()
        return gid

    def update_category_assignment(self, pid: str, category: str):
        # [Architecture 6.0] Strict Type Check
        from core.interfaces.capability import CapabilityType
        
        # Legacy mappings for shorthand => Full Enum
        legacy_map = {
            "skill": CapabilityType.TOOL_EXECUTION.value,
            "stt": CapabilityType.STT_PROVIDER.value,
            "tts": CapabilityType.TTS_PROVIDER.value,
            "system": CapabilityType.EXTENSION.value,
            "other": "other"
        }
        
        normalized = legacy_map.get(category, category)
        
        # Validation: Must be in Enum or explicit 'other' whitelist
        valid_values = [m.value for m in CapabilityType] + ["other"]
        
        if normalized not in valid_values:
             # Try fallback to partial match if needed, or fail strict
             raise ValueError(f"Invalid category: {category}. Valid: {valid_values}")

        app_config.plugin_groups.custom_categories[pid] = normalized
        app_config.save()
        return normalized
    
    def update_group_behavior(self, gid: str, behavior: str):
        if behavior not in ["exclusive", "independent"]:
             raise ValueError("Invalid behavior")
        app_config.plugin_groups.group_behaviors[gid] = behavior
        app_config.save()
        return behavior
    
    async def update_config(self, plugin_id: str, key: str, value: Any):
        """
        [Architecture 5.3] Contract-Aware Config Handler.
        Distinguishes between Persistent (Saved) and Transient (Runtime) keys.
        """
        # 1. Resolve Target & Intent
        all_plugins = await self.list_all_plugins()
        target_info = next((p for p in all_plugins if p['id'] == plugin_id), None)
        if not target_info:
             raise ValueError(f"Plugin {plugin_id} not found")
        
        target = target_info.get('runtime_target', 'main')
        caps = target_info.get('capabilities', [])
        
        # [Safety] Persistent vs Transient Audit
        is_transient = key.startswith("_") or key in ["session_id", "trace_id"]
        
        logger.info(f"⚙️ [Unified Config] {plugin_id} ({target}) -> {key}={value} {'(Transient)' if is_transient else '(Persistent)'}")

        # 2. Persistence (Main Process Authority)
        if not is_transient:
            app_config.plugins.settings.setdefault(plugin_id, {})[key] = value
            app_config.save()

        # 3. Route by Target
        # A. Remote Worker
        if target != 'main':
             # [Architecture 5.2] Dynamic Discovery
             fallback_port = app_config.network.stt_port if target == 'stt_server' else app_config.network.tts_port
             base_url = discovery.get_url(target, fallback_port=fallback_port)
             url = f"{base_url}/plugins/config"
             
             # [Optimization] Use shared HTTP client pool
             from services.http_client import get_http_client
             try:
                 client = await get_http_client()
                 res = await client.post(url, json={"id": plugin_id, "key": key, "value": value}, timeout=5.0)
                 return res.json()
             except Exception as e:
                 logger.error(f"Failed to forward config to {url}: {e}")
                 raise RuntimeError(f"Remote config update failed: {e}")

        # B. MCP Virtual Plugins
        if plugin_id.startswith("mcp."):
            mcp_name = plugin_id.split(".", 1)[1]
            module_id = f"mcp-{mcp_name}"
            soul_client = getattr(self.services, "soul_client", None)
            if soul_client:
                data = soul_client.load_module_data(module_id) or {}
                data[key] = value
                soul_client.save_module_data(module_id, data)
                return {"status": "ok", "config": data}

        # C. System Plugins
        plugin = self.system_plugin_manager.get_plugin(plugin_id)
        if plugin:
            plugin.update_config(key, value)
            return {"status": "ok", "config": getattr(plugin, 'config', {})}

        # D. Heartbeat Tickers
        if self.heartbeat_service:
            ticker = self.heartbeat_service.get_ticker(plugin_id)
            if ticker:
                ticker.config[key] = value
                if key == "enabled": ticker.enabled = bool(value)
                return {"status": "ok", "config": ticker.config}
        
        return {"status": "error", "message": "Configuration target not supported"}

    async def ensure_worker_running(self, worker_id: str) -> bool:
        """
        [Architecture 4.0] On-Demand Orchestrator Trigger.
        Ensures the specified worker process is running.
        """
        # Get ProcessManager from container (Might be None if not initialized)
        pm = getattr(self.services, "get_process_manager", lambda: None)()
        if not pm:
            logger.warning("ProcessManager not available. Cannot spawn worker.")
            return False

        if pm.is_running(worker_id):
            return True

        # Map worker_id to script args
        # backend_launcher.py expects: python backend_launcher.py [stt|tts]
        script_args = {
            "stt_server": ["stt"],
            "tts_server": ["tts"]
        }
        
        args = script_args.get(worker_id)
        if not args:
            logger.error(f"Unknown worker ID: {worker_id}")
            return False

        logger.info(f"🚀 [Orchestrator] Spawning {worker_id} on demand...")
        success = pm.start_worker(worker_id, "backend_launcher.py", args)
        if success:
            # Short wait for startup? Or we let the registry handle it?
            # Architecture 3.0 handles the discovery asynchronously.
            # But the caller might expect immediate results.
            # We just return True that "We started it".
            return True
        return False

    async def toggle_plugin(self, provider_id: str, target_state: bool = None):
        """
        [Architecture 5.0] Unified Dispatcher.
        Routes toggle requests to the appropriate runtime (Local, Remote, Search).
        """
        # 0. Handle Legacy Toggle (No intent)
        if target_state is None:
             current_plugins = await self.list_all_plugins()
             p = next((x for x in current_plugins if x['id'] == provider_id), None)
             target_state = not (p.get('enabled', False) or p.get('active', False)) if p else True

        # 1. Resolve Metadata (Live SSOT)
        all_plugins = await self.list_all_plugins()
        target_info = next((p for p in all_plugins if p['id'] == provider_id), None)
        if not target_info:
            raise ValueError(f"Plugin {provider_id} not found")

        gid = target_info.get('group_id')
        policy = target_info.get('group_policy', 'independent')
        caps = target_info.get('capabilities', [])
        target = target_info.get('runtime_target', 'main')

        logger.info(f"🔌 [Unified Toggle] {provider_id} -> {target_state} (Group: {gid}, Policy: {policy}, Target: {target})")

        # 2. Handle Mutual Exclusion (Backend Driven)
        if target_state is True and policy == "exclusive" and gid:
            for p in all_plugins:
                if p['group_id'] == gid and p['id'] != provider_id and (p.get('enabled') or p.get('active')):
                    logger.info(f"🔄 [Auto-Exclusion] Deactivating {p['id']} in group {gid}")
                    if p.get('runtime_target') == 'main':
                        # System plugins handle themselves
                        self.system_plugin_manager.disable_plugin(p['id'])
                    # For search/remote, it's implicitly handled by switching the provider/context below

        # [Architecture Refinement] Hybrid Fast Path
        # If target IS local ('main'), we execute immediately for UI responsiveness ("Desktop Pet Mode")
        # Then we sync to DB for persistence ("Home AI OS Mode")
        
        # 1. Fast Path Execution
        fast_path_success = False
        if target == 'main':
            logger.info(f"🚀 [Hybrid Fast Path] Executing local toggle for {provider_id} -> {target_state}")
            try:
                if target_state:
                    if "search.provider" in caps or gid == "search_provider":
                         app_config.search.provider = provider_id
                         app_config.save()
                    fast_path_success = self.system_plugin_manager.enable_plugin(provider_id)
                else:
                    if "search.provider" in caps or gid == "search_provider":
                        if app_config.search.provider == provider_id:
                            app_config.search.provider = "none"
                            app_config.save()
                    fast_path_success = self.system_plugin_manager.disable_plugin(provider_id)
            except Exception as e:
                logger.error(f"❌ Fast Path Execution Failed: {e}")
                # Fallback to slow path? Or fail?
                # If local execution fails, writing to DB won't help much for immediate use.
                return {"status": "error", "message": f"Local execution failed: {e}", "state": not target_state}
        
        # 2. Persistence & D-Bus Notification (Eventual Consistency)
        # We ALWAYS do this to keep the 'Home AI OS' dream alive (Remote nodes/UI need to know).
        try:
            from services.infra.bus_factory import get_lifecycle_bus
            bus_ssot = get_lifecycle_bus()
            
            # If Fast Path succeeded, we report "ready/stopped" immediately instead of "transitioning"
            # This prevents the UI from showing a spinner if we are already done.
            new_status = "ready" if (target_state and fast_path_success) else \
                         "stopped" if (not target_state and fast_path_success) else \
                         "transitioning"
                         
            await bus_ssot.publish_state(provider_id, {
                "desired_enabled": target_state, 
                "active_status": new_status,
                "runtime_target": target, # [Fix] Critical for Worker Filtering
                # "active": target_state  <-- REMOVED: Workers perform the action, we just signal Intent.
                # "enabled": target_state <-- REMOVED: 'enabled' is now effective state reported by Worker.
            })
        except Exception as e:
            logger.warning(f"Failed to update SSOT in DB (Non-Critical for Local): {e}")

        # [Frontend Sync] Real-time Push
        # Notify Gateway -> Frontend immediately
        if self.services.event_bus:
            # Map Internal Status to Frontend Expectation (enabled/disabled)
            # Frontend: PluginStoreModal.tsx expects 'status' to be 'enabled' or 'disabled' to clear transit state
            event_status = "enabled" if new_status == "ready" else "disabled" if new_status == "stopped" else new_status
            
            payload = {
                "plugin_id": provider_id,
                "status": event_status, # [Fix] Compatibility with PluginStoreModal
                "desired_enabled": target_state,
                "active_status": new_status,
                "active": target_state
            }
            # Use 'fire_and_forget' or just emit? emit is async usually.
            await self.services.event_bus.emit(EventType.PLUGIN_STATUS, payload)


        # 3. Hybrid Return Strategy
        if target == 'main':
             # Return immediately, don't wait for reconciliation loop
             return {"status": "ok", "state": target_state}
             
        # --- End Hybrid Fast Path ---

        # 4. Slow Path (Remote / Search / Legacy)
        # If we didn't execute locally (e.g. Remote Worker), we fall back to the Wait-Loop
        
        # Phase B: Execution (Remote)
        # B. Remote Driver (STT/TTS Worker)
        if target != 'main':
             # [Architecture 6.1] Pure Mesh Control (Scheme C)
             # The Intent was already written to the Bus (Phase A/2).
             # We rely on Worker's PluginStateSync to pick it up and report back.
             pass

        # Phase C: Reconciliation Loop (Wait for Actual State)
        logger.info(f"⏳ [Reconciliation] Waiting for remote {provider_id} to report state {target_state}...")
        for _ in range(10):
            await asyncio.sleep(0.5)
            current_state = self.plugin_registry.get(provider_id, {})
            # [Fix] Use canonical fields for state comparison
            actual_desired = current_state.get("desired_enabled")
            actual_status = current_state.get("active_status", "unknown")
            
            if target_state:  # Enabling
                if actual_desired is True and actual_status in ["ready", "idle"]:
                    logger.info(f"✅ [Reconciliation] State confirmed for {provider_id}")
                    return {"status": "ok", "state": target_state}
            else:  # Disabling
                if actual_desired is False or actual_status == "stopped":
                    logger.info(f"✅ [Reconciliation] State confirmed for {provider_id}")
                    return {"status": "ok", "state": target_state}
        
        return {"status": "pending", "state": target_state, "message": "Toggle requested but remote state report is lagging."}

    async def install_plugin_from_zip(self, file_obj, filename: str):
        if not filename.endswith('.zip'):
             raise ValueError("Only .zip files are supported")
        
        temp_zip_path = Path(f"temp_plugin_upload_{filename}")
        install_id = f"install_{int(asyncio.get_event_loop().time())}"
        
        async def emit_progress(current: int, total: int, message: str):
            """Emit progress event to frontend via EventBus"""
            if self.services.event_bus:
                await self.services.event_bus.emit("plugin.install.progress", {
                    "install_id": install_id,
                    "filename": filename,
                    "current": current,
                    "total": total,
                    "percent": int((current / total) * 100) if total > 0 else 0,
                    "message": message
                })
        
        def sync_progress_callback(current, total, message):
            """Sync wrapper for async emit (runs in thread)"""
            # Store progress for later async emission
            sync_progress_callback.last_progress = (current, total, message)
        sync_progress_callback.last_progress = None
        
        try:
            # Phase 1: Save file
            await emit_progress(0, 100, "Saving uploaded file...")
            await asyncio.to_thread(self._save_file_sync, file_obj, temp_zip_path)
            await emit_progress(5, 100, "File saved, extracting...")
            
            # Phase 2: Extract with progress
            plugin_id = await asyncio.to_thread(
                self._extract_zip_sync, 
                temp_zip_path, 
                sync_progress_callback
            )
            
            # Emit final extraction progress
            if sync_progress_callback.last_progress:
                c, t, m = sync_progress_callback.last_progress
                await emit_progress(c, t, m)
            
            # Phase 3: Hot Reload
            await emit_progress(95, 100, "Loading plugin...")
            if self.system_plugin_manager:
                 logger.info(f"Triggering Hot Reload for {plugin_id}")
                 success = await asyncio.to_thread(self.system_plugin_manager.reload_plugin, plugin_id)
                 await emit_progress(100, 100, "Complete")
                 if success:
                     return {"status": "success", "id": plugin_id, "message": "Installed and loaded.", "install_id": install_id}
                 else:
                     return {"status": "warning", "id": plugin_id, "message": "Installed but failed to load.", "install_id": install_id}
            
            await emit_progress(100, 100, "Complete")
            return {"status": "success", "id": plugin_id, "message": "Installed. Restart backend to load.", "install_id": install_id}
            
        except Exception as e:
            await emit_progress(0, 100, f"Error: {str(e)}")
            raise
        finally:
            if temp_zip_path.exists():
                try:
                    os.remove(temp_zip_path)
                except Exception:
                    pass

    def _save_file_sync(self, src, dest: Path):
        with open(dest, "wb") as buffer:
            shutil.copyfileobj(src, buffer)

    def _extract_zip_sync(self, zip_path: Path, progress_callback=None) -> str:
        """
        Extract plugin zip with progress reporting.
        
        Args:
            zip_path: Path to zip file
            progress_callback: Optional callback(current, total, message)
        """
        plugin_id = None
        with zipfile.ZipFile(zip_path, 'r') as zip_ref:
            file_list = zip_ref.namelist()
            manifest_path = next((f for f in file_list if f.endswith("manifest.yaml")), None)
            
            if not manifest_path:
                raise ValueError("No manifest.yaml found")
            
            # Report: Parsing manifest
            if progress_callback:
                progress_callback(0, 100, "Parsing manifest...")
                
            extract_root = ""
            if '/' in manifest_path:
                 extract_root = manifest_path.rsplit('/', 1)[0]
            
            with zip_ref.open(manifest_path) as mf:
                data = yaml.safe_load(mf)
                try:
                    manifest = PluginManifest(**data)
                    plugin_id = manifest.id
                except Exception as e:
                    raise ValueError(f"Invalid Manifest: {e}")

            safe_dirname = plugin_id.replace(".", "_")
            # [Security] Resolve absolute path for boundary check
            target_dir = Path(f"plugins/system/{safe_dirname}").resolve()
            
            if target_dir.exists():
                if progress_callback:
                    progress_callback(5, 100, "Removing old version...")
                shutil.rmtree(target_dir)
            target_dir.mkdir(parents=True, exist_ok=True)
            
            # Count extractable files for progress
            extractable = [m for m in zip_ref.infolist() 
                          if not m.filename.startswith("__MACOSX")]
            total_files = len(extractable)
            extracted = 0
            
            for member in extractable:
                fname = member.filename
                if extract_root and fname.startswith(extract_root + '/'):
                     fname = fname[len(extract_root)+1:]
                elif extract_root and not fname.startswith(extract_root):
                     continue
                
                if not fname: continue
                
                # [Security Fix] Zip Slip Prevention
                target_path = (target_dir / fname).resolve()
                
                # Robust Containment Check
                try:
                    if os.path.commonpath([target_dir, target_path]) != str(target_dir):
                        logger.warning(f"🚨 [Security] Blocked Zip Path Traversal attempt: {member.filename}")
                        continue
                except ValueError:
                    # Can happen on Windows if paths are on different drives
                    continue

                if member.is_dir():
                    target_path.mkdir(parents=True, exist_ok=True)
                else:
                    target_path.parent.mkdir(parents=True, exist_ok=True)
                    with zip_ref.open(member) as src, open(target_path, "wb") as dst:
                        shutil.copyfileobj(src, dst)
                
                extracted += 1
                if progress_callback and total_files > 0:
                    # Progress: 10-95% for extraction
                    pct = 10 + int((extracted / total_files) * 85)
                    progress_callback(pct, 100, f"Extracting {fname[:30]}...")
                        
        if progress_callback:
            progress_callback(100, 100, "Complete")
        return plugin_id

    async def get_all_ui_slots(self) -> List[Dict[str, Any]]:
        """
        Aggregate UI components from all plugin sources.
        """
        slots = []
        
        # 1. System Plugins (Local Stubs & Active)
        if self.system_plugin_manager:
            try:
                slots.extend(self.system_plugin_manager.get_active_ui_slots())
            except Exception as e:
                logger.error(f"Failed to get system plugin slots: {e}")

        # 2. Remote Registry (Distributed Workers)
        for pid, state in self.plugin_registry.items():
            worker_slots = state.get("ui_slots")
            if worker_slots:
                for s in worker_slots:
                    s["_source"] = state.get("worker_id", "remote")
                    slots.append(s)
        
        # 3. MCP Servers 
        if self.mcp_host:
            for name, client in self.mcp_host.clients.items():
                mcp_dir = Path(BASE_DIR) / "mcp_servers" / name
                meta_path = mcp_dir / "metadata.json"
                if meta_path.exists():
                     try:
                         with open(meta_path, 'r', encoding='utf-8') as f:
                             meta = json.load(f)
                             mcp_slots = meta.get("ui_slots", [])
                             if mcp_slots:
                                 for s in mcp_slots:
                                     s["plugin_id"] = f"mcp.{name}" # logical ID
                                     s["_source"] = "mcp"
                                 slots.extend(mcp_slots)
                     except Exception as e:
                         pass

        return slots

    async def _broadcast_lifecycle_event(self, plugin_id: str, event_type: str):
        """
        [Scheme D] The 'Shoute' Sender.
        Broadcasts Lifecycle events to all known worker ports via HTTP.
        This ensures external processes (STT/TTS) stay in sync with the Main Process.
        """
        logger.info(f"📢 Broadcasting Lifecycle Event: {plugin_id} -> {event_type}")
        
        # Define Targets
        # Alternatively, iterate self.registry or config.network
        stt_port = app_config.network.stt_port
        tts_port = app_config.network.tts_port
        
        targets = [
            f"http://127.0.0.1:{stt_port}/system/lifecycle",
            f"http://127.0.0.1:{tts_port}/system/lifecycle"
        ]
        
        payload = {
            "type": event_type, # 'enabled' | 'disabled'
            "plugin_id": plugin_id,
            "timestamp": asyncio.get_event_loop().time()
        }
        
        # [Optimization] Use shared HTTP client pool
        from services.http_client import get_http_client
        try:
            client = await get_http_client()
            for url in targets:
                try:
                    # Fire and Forget (mostly)
                    await client.post(url, json=payload, timeout=1.0)
                except httpx.ConnectError:
                    pass # Worker might be offline, which is fine
                except Exception as e:
                    logger.warning(f"Broadcast to {url} failed: {e}")
        except Exception as e:
            logger.warning(f"HTTP client error: {e}")
