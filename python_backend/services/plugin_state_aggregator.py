"""
Plugin State Aggregator Service
Event-driven centralized plugin state management.

Replaces the scattered state merging logic in PluginService.list_all_plugins()
with a unified cache that updates via events.
"""

import asyncio
import logging
import time
from typing import Dict, List, Optional, Any
from dataclasses import dataclass, field

from core.runtime import MAIN_RUNTIME_TARGET, normalize_runtime_target

logger = logging.getLogger("PluginStateAggregator")


@dataclass
class PluginStateEntry:
    """Cached plugin state with metadata"""
    id: str
    data: Dict[str, Any] = field(default_factory=dict)
    last_updated: float = 0.0
    source: str = "unknown"  # local, worker, mcp, ticker


class PluginStateAggregator:
    """
    Event-driven Plugin State Aggregator.
    
    Responsibilities:
    - Subscribe to state change events from all sources
    - Maintain unified in-memory cache
    - Provide O(1) state queries
    - Centralize status computation logic
    
    Event Sources:
    - plugin.state.local: SystemPluginManager updates
    - plugin.state.worker: Remote worker heartbeats
    - plugin.state.mcp: MCP server registration
    - plugin.state.ticker: Heartbeat ticker updates
    - worker.offline: Worker disconnect events
    """
    
    # Status computation constants
    OFFLINE_TIMEOUT_SECONDS = 30
    
    def __init__(self, bus=None):
        self._cache: Dict[str, PluginStateEntry] = {}
        self._lock = asyncio.Lock()
        self._bus = bus
        self._initialized = False
        self._overrides = {}
        
    async def initialize(self, bus=None):
        """Initialize aggregator and subscribe to events"""
        if self._initialized:
            return
            
        if bus:
            self._bus = bus
            
        if not self._bus:
            logger.warning("No EventBus provided, aggregator will run in passive mode")
            return
        
        # Subscribe to all state sources
        self._bus.subscribe("plugin.state.local", self._on_local_update)
        self._bus.subscribe("plugin.state.worker", self._on_worker_update)
        self._bus.subscribe("plugin.state.mcp", self._on_mcp_update)
        self._bus.subscribe("plugin.state.ticker", self._on_ticker_update)
        self._bus.subscribe("worker.offline", self._on_worker_offline)
        self._bus.subscribe("system.worker.offline", self._on_worker_offline)
        
        self._initialized = True
        logger.info("✅ PluginStateAggregator initialized")
    
    def set_overrides(self, groups: Dict, categories: Dict, behaviors: Dict):
        """Set user configuration overrides"""
        self._overrides = {
            "groups": groups or {},
            "categories": categories or {},
            "behaviors": behaviors or {}
        }

    @staticmethod
    def _normalize_incoming_state(state: dict[str, Any], source: str) -> dict[str, Any]:
        normalized = dict(state)

        if source == "worker":
            active_status = normalized.get("active_status") or normalized.get("status")
            if active_status is not None:
                normalized["active_status"] = active_status

            if normalized.get("active") is None:
                if normalized.get("active_in_group") is not None:
                    normalized["active"] = bool(normalized.get("active_in_group"))
                elif active_status is not None:
                    normalized["active"] = active_status in {"ready", "idle", "running"}

        return normalized
    
    # --- Event Handlers ---
    
    async def _on_local_update(self, event):
        """Handle local plugin state changes"""
        data = event.data
        if isinstance(data, dict):
            plugin_id = data.get("id") or data.get("plugin_id")
            if plugin_id:
                await self._merge_state(plugin_id, data, source="local")
    
    async def _on_worker_update(self, event):
        """Handle remote worker plugin reports"""
        data = event.data
        if isinstance(data, dict):
            plugins = data.get("plugins", [])
            if not plugins and "id" in data:
                # Single plugin update
                plugins = [data]
            
            for plugin in plugins:
                plugin_id = plugin.get("id") or plugin.get("plugin_id")
                if plugin_id:
                    await self._merge_state(plugin_id, plugin, source="worker")
    
    async def _on_mcp_update(self, event):
        """Handle MCP server registration"""
        data = event.data
        if isinstance(data, dict):
            plugin_id = data.get("id")
            if plugin_id:
                await self._merge_state(plugin_id, data, source="mcp")
    
    async def _on_ticker_update(self, event):
        """Handle heartbeat ticker updates"""
        data = event.data
        if isinstance(data, dict):
            plugin_id = data.get("id")
            if plugin_id:
                await self._merge_state(plugin_id, data, source="ticker")
    
    async def _on_worker_offline(self, event):
        """Mark all plugins from offline worker as offline"""
        data = event.data
        worker_id = data.get("worker_id") if isinstance(data, dict) else None
        if not worker_id:
            return
            
        async with self._lock:
            for pid, entry in self._cache.items():
                if entry.data.get("worker_id") == worker_id:
                    entry.data["active_status"] = "offline"
                    entry.data["computed_status"] = "offline"
                    entry.last_updated = time.time()
                    logger.info(f"👻 Marked {pid} as offline (worker {worker_id} disconnected)")
    
    # --- State Management ---
    
    async def _merge_state(self, plugin_id: str, new_state: dict, source: str):
        """
        Intelligently merge new state into cache.
        
        Priority Rules:
        - active_status: worker report wins over local snapshots
        - desired_enabled: config intent is the single writable source
        - metadata: merge, don't guess
        """
        async with self._lock:
            normalized_state = self._normalize_incoming_state(new_state, source)
            existing = self._cache.get(plugin_id)
            
            if existing:
                merged = existing.data.copy()
            else:
                merged = {}
            
            for key, value in normalized_state.items():
                if value is not None:
                    if key == "active_status" and source != "worker" and merged.get("_status_source") == "worker":
                        continue
                    merged[key] = value
            
            if "active_status" in normalized_state:
                merged["_status_source"] = source
            merged["last_updated"] = time.time()

            self._apply_overrides_to_plugin(plugin_id, merged)
            merged["computed_status"] = self._compute_status(merged)
            merged.setdefault("id", plugin_id)
            desired_enabled = merged.get("desired_enabled")
            if desired_enabled is None:
                desired_enabled = merged.get("enabled")
            merged["enabled"] = bool(desired_enabled) if desired_enabled is not None else bool(merged.get("active"))
            if merged.get("active") is None:
                merged["active"] = merged.get("active_status") in {"ready", "idle", "running"}
            if merged.get("active_in_group") is None:
                merged["active_in_group"] = bool(merged.get("active"))
            merged.setdefault("group_policy", "independent")
            merged["runtime_target"] = normalize_runtime_target(merged.get("runtime_target", MAIN_RUNTIME_TARGET))
            merged.setdefault("capabilities", [])
            
            # Update cache entry
            self._cache[plugin_id] = PluginStateEntry(
                id=plugin_id,
                data=merged,
                last_updated=time.time(),
                source=source
            )
    
    def _apply_overrides_to_plugin(self, plugin_id: str, state: dict):
        """Apply user configuration overrides to a plugin state"""
        # Group assignment
        if plugin_id in self._overrides.get("groups", {}):
            state["group_id"] = self._overrides["groups"][plugin_id]
        
        # Category assignment
        if plugin_id in self._overrides.get("categories", {}):
            state["category"] = self._overrides["categories"][plugin_id]
        
        # Group behavior (exclusive/independent)
        gid = state.get("group_id")
        if gid and gid in self._overrides.get("behaviors", {}):
            state["group_policy"] = self._overrides["behaviors"][gid]
        
    def _compute_status(self, state: dict) -> str:
        """
        Unified status computation logic.
        
        Combines desired_enabled (intent) and active_status (reality)
        into a user-friendly computed_status.
        """
        # Get intent
        desired = state.get("desired_enabled")
        if desired is None:
            desired = state.get("enabled", False)
        
        # Get reality
        actual = state.get("active_status", "unknown")
        
        # Check staleness
        last_update = state.get("last_updated", 0)
        age = 0
        if last_update:
            # Handle both float (timestamp) and string (ISO format) 
            if isinstance(last_update, (int, float)):
                age = time.time() - last_update
            elif isinstance(last_update, str):
                try:
                    from datetime import datetime
                    dt = datetime.fromisoformat(last_update.replace('Z', '+00:00'))
                    age = time.time() - dt.timestamp()
                except (ValueError, AttributeError):
                    age = 0
        
        # Compute
        if desired:
            if actual in ["ready", "idle", "running", "healthy"]:
                return "running"
            elif actual in ["loading", "transitioning", "starting"]:
                return "provisioning"
            elif actual == "error":
                return "error"
            elif actual == "offline":
                return "offline"
            elif age > self.OFFLINE_TIMEOUT_SECONDS:
                return "offline"
            else:
                return "stuck"
        else:
            if actual == "ready":
                return "stopping"
            elif actual == "offline":
                return "offline"
            else:
                return "stopped"
    
    # --- Queries ---
    
    def get_snapshot(self) -> List[Dict[str, Any]]:
        """
        Get current state snapshot of all plugins.
        O(n) but no async calls or merging needed.
        """
        result = []
        for entry in self._cache.values():
            plugin_data = entry.data.copy()
            plugin_data["_cache_age"] = time.time() - entry.last_updated
            result.append(plugin_data)
        return result
    
    def get_plugin(self, plugin_id: str) -> Optional[Dict[str, Any]]:
        """Get state for a specific plugin"""
        entry = self._cache.get(plugin_id)
        if entry:
            return entry.data.copy()
        return None
    
    def get_plugins_by_source(self, source: str) -> List[Dict[str, Any]]:
        """Get all plugins from a specific source (local, worker, mcp, ticker)"""
        return [
            entry.data.copy()
            for entry in self._cache.values()
            if entry.source == source
        ]
    
    def get_plugins_by_worker(self, worker_id: str) -> List[Dict[str, Any]]:
        """Get all plugins belonging to a specific worker"""
        return [
            entry.data.copy()
            for entry in self._cache.values()
            if entry.data.get("worker_id") == worker_id
        ]
    
    # --- Bulk Operations ---
    
    async def bulk_update(self, plugins: List[Dict], source: str = "bulk"):
        """Bulk update multiple plugins at once"""
        for plugin in plugins:
            plugin_id = plugin.get("id")
            if plugin_id:
                await self._merge_state(plugin_id, plugin, source=source)
    
    async def remove_plugin(self, plugin_id: str):
        """Remove a plugin from cache"""
        async with self._lock:
            if plugin_id in self._cache:
                del self._cache[plugin_id]
                logger.info(f"🗑️ Removed {plugin_id} from aggregator cache")
    
    async def prune_stale(self, max_age_seconds: float = 300):
        """Remove plugins that haven't been updated recently"""
        now = time.time()
        async with self._lock:
            stale = [
                pid for pid, entry in self._cache.items()
                if now - entry.last_updated > max_age_seconds
            ]
            for pid in stale:
                del self._cache[pid]
            if stale:
                logger.info(f"🧹 Pruned {len(stale)} stale plugins from cache")
    
    # --- Debug ---
    
    def debug_dump(self) -> Dict:
        """Get debug info about cache state"""
        return {
            "total_plugins": len(self._cache),
            "by_source": {
                "local": len(self.get_plugins_by_source("local")),
                "worker": len(self.get_plugins_by_source("worker")),
                "mcp": len(self.get_plugins_by_source("mcp")),
                "ticker": len(self.get_plugins_by_source("ticker")),
            },
            "overrides": self._overrides,
            "initialized": self._initialized
        }


# Singleton instance
_aggregator_instance: Optional[PluginStateAggregator] = None


def get_plugin_state_aggregator() -> PluginStateAggregator:
    """Get or create the global aggregator instance"""
    global _aggregator_instance
    if _aggregator_instance is None:
        _aggregator_instance = PluginStateAggregator()
    return _aggregator_instance


async def init_plugin_state_aggregator(bus) -> PluginStateAggregator:
    """Initialize the global aggregator with an event bus"""
    aggregator = get_plugin_state_aggregator()
    await aggregator.initialize(bus)
    return aggregator
