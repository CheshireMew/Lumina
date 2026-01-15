import sys
import time
import queue
import logging
import traceback
import importlib.util
from typing import Dict, Any
from multiprocessing import Queue

# Adjust path to find core modules if running as script
import os
sys.path.append(os.getcwd())

from core.isolation.protocol import PluginCommand, PluginEvent, CommandType, EventType
from core.isolation.remote_context import RemoteContext

# Setup basic logging for worker
logging.basicConfig(level=logging.INFO, format='[Worker] %(message)s')
logger = logging.getLogger("PluginWorker")

class PluginWorker:
    def __init__(self, cmd_queue: Queue, event_queue: Queue):
        self.cmd_queue = cmd_queue
        self.event_queue = event_queue
        self.running = True
        self.plugins: Dict[str, Any] = {} # id -> plugin_instance
        self.contexts: Dict[str, RemoteContext] = {} # id -> context

    def run(self):
        logger.info("Worker Process Started")
        self._emit_sys_event(EventType.READY, {}, "worker")
        
        while self.running:
            try:
                # Blokcing get with timeout to allow graceful shutdown check
                cmd_data = self.cmd_queue.get(timeout=1.0)
                if cmd_data:
                    self._process_command(cmd_data)
            except queue.Empty:
                continue
            except Exception as e:
                logger.error(f"Worker Loop Error: {e}")
                self._emit_error("system", str(e), traceback.format_exc())

    def _process_command(self, cmd_data: Dict[str, Any]):
        try:
            # Validate command structure
            cmd = PluginCommand(**cmd_data)
            logger.info(f"Received Command: {cmd.type} for {cmd.id}")

            if cmd.type == CommandType.LOAD:
                self._handle_load(cmd.id, cmd.payload)
            elif cmd.type == CommandType.START:
                self._handle_start(cmd.id)
            elif cmd.type == CommandType.STOP:
                self._handle_stop(cmd.id)
            elif cmd.type == CommandType.TERMINATE:
                self.running = False
            elif cmd.type == CommandType.EVENT_EMIT:
                self._handle_event_dispatch(cmd.payload)
            else:
                logger.warning(f"Unknown command type: {cmd.type}")

        except Exception as e:
            logger.error(f"Command Processing Error: {e}")
            self._emit_error("system", f"Command Failed: {e}", traceback.format_exc())

    def _handle_load(self, plugin_id: str, payload: Dict[str, Any]):
        try:
            manifest_path = payload.get("manifest_path")
            if not manifest_path:
                raise ValueError("Missing manifest_path")

            # Dynamic Import
            # 1. Resolve 'plugin.py' relative to manifest (assuming standard layout)
            plugin_dir = os.path.dirname(manifest_path)
            entry_py = os.path.join(plugin_dir, "plugin.py")
            
            if not os.path.exists(entry_py):
                 # Try finding via manifest 'entry' field? For now assume standard plugin.py
                 raise FileNotFoundError(f"Entry file not found: {entry_py}")

            spec = importlib.util.spec_from_file_location(f"plugin_{plugin_id}", entry_py)
            if not spec or not spec.loader:
                raise ImportError(f"Could not load spec for {entry_py}")
                
            module = importlib.util.module_from_spec(spec)
            sys.modules[spec.name] = module # Should we isolate strict? Yes, it's a separate process.
            spec.loader.exec_module(module)
            
            # Find Plugin Class
            plugin_class = None
            for attr_name in dir(module):
                attr = getattr(module, attr_name)
                # Heuristic: Inherits from BaseSystemPlugin (duck type check by name to avoid import dependency issues?)
                # Ideally we import BaseSystemPlugin here too.
                # Let's assume the plugin exports a class ending in 'Plugin'
                if isinstance(attr, type) and attr.__name__.endswith("Plugin") and attr.__name__ != "BaseSystemPlugin":
                    plugin_class = attr
                    break
            
            if not plugin_class:
                raise ValueError("No Plugin class found in module")

            # Instantiate
            plugin_instance = plugin_class()
            
            # Create RemoteContext
            ctx = RemoteContext(plugin_id, self.event_queue)
            
            # Initialize
            if hasattr(plugin_instance, "initialize"):
                plugin_instance.initialize(ctx)
            
            self.plugins[plugin_id] = plugin_instance
            self.contexts[plugin_id] = ctx
            
            self._emit_sys_event(EventType.LOG, {"level": "info", "message": f"Plugin {plugin_id} loaded in worker"}, plugin_id)

        except Exception as e:
            self._emit_error(plugin_id, f"Load Failed: {e}", traceback.format_exc())

    def _handle_start(self, plugin_id: str):
        # Optional: Call start() if plugin has it? 
        # BaseSystemPlugin doesn't have explicit start(), but maybe we add it.
        # For now, initialize is effectively load+start.
        pass

    def _handle_stop(self, plugin_id: str):
        if plugin_id in self.plugins:
            # Cleanup
            del self.plugins[plugin_id]
            del self.contexts[plugin_id]
            # Force GC?
            import gc
            gc.collect()

    def _handle_event_dispatch(self, payload: Dict[str, Any]):
        # Received Event from Host -> dispatch to local listeners
        # For V1, we haven't implemented local listeners registry in RemoteContext yet.
        pass

    def _emit_sys_event(self, type: EventType, payload: Dict[str, Any], plugin_id: str):
        evt = PluginEvent(type=type, plugin_id=plugin_id, payload=payload)
        self.event_queue.put(evt.dict()) # Pydantic v1 usually wants .dict() or model_dump()

    def _emit_error(self, plugin_id: str, message: str, tb: str):
        self._emit_sys_event(EventType.ERROR, {"message": message, "traceback": tb}, plugin_id)

def run_worker(cmd_q, event_q):
    """Entry point for multiprocessing"""
    worker = PluginWorker(cmd_q, event_q)
    worker.run()
