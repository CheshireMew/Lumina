"""
PluginHost: Running inside the Child Process.
Responsible for:
1. Receiving IPC commands.
2. Loading the actual Plugin class.
3. Invoking methods.
4. Sending results back.
"""
import sys
import multiprocessing
import importlib.util
import asyncio
import logging
from pathlib import Path

# Setup logging for child process
logging.basicConfig(level=logging.INFO, format='%(asctime)s [%(levelname)s] [PluginHost-%(process)d] %(message)s')
logger = logging.getLogger("PluginHost")

class PluginHost:
    def __init__(self, manifest_data: dict, ipc_queue: multiprocessing.Queue, event_queue: multiprocessing.Queue):
        self.manifest = manifest_data
        self.ipc_queue = ipc_queue
        self.event_queue = event_queue
        self.plugin_instance = None
        self.loop = asyncio.new_event_loop()

    def run(self):
        """Main Loop"""
        asyncio.set_event_loop(self.loop)
        logger.info(f"Starting PluginHost for {self.manifest['id']}")
        
        try:
            # 1. Load Plugin
            self._load_plugin()
            
            # 2. Command Loop
            while True:
                # Blocking Get
                msg = self.ipc_queue.get()
                if msg is None: # Sentinel
                    break
                
                cmd = msg.get("cmd")
                req_id = msg.get("id")
                
                if cmd == "initialize":
                    self.loop.run_until_complete(self._handle_initialize(msg))
                elif cmd == "teardown":
                    self._handle_teardown()
                    break
                elif cmd == "call":
                    self.loop.run_until_complete(self._handle_call(msg))
                else:
                    logger.warning(f"Unknown command: {cmd}")
                    
        except KeyboardInterrupt:
            logger.info("PluginHost received Stop Signal (KeyboardInterrupt).")
        except Exception as e:
            logger.critical(f"PluginHost Crash: {e}", exc_info=True)
        finally:
            logger.info("PluginHost Exiting.")

    def _load_plugin(self):
        # Similar logic to PluginLoader but simplified since we are isolated
        # We need to reconstruct the path
        # Note: sys.path manipulation might be needed if plugin relies on relative imports
        path = Path(self.manifest['path'])
        
        # entrypoint: "module:Class"
        mod_name, cls_name = self.manifest['entrypoint'].split(":")
        
        # We assume standard structure
        sys.path.insert(0, str(path.parent)) # Enable finding siblings? No, isolation.
        
        # Determine file
        entry_file = path / f"{mod_name}.py"
        if not entry_file.exists():
             entry_file = path / mod_name / "__init__.py"
             
        spec = importlib.util.spec_from_file_location(f"plugins.isolated.{self.manifest['id']}", entry_file)
        module = importlib.util.module_from_spec(spec)
        sys.modules[spec.name] = module
        spec.loader.exec_module(module)
        
        plugin_cls = getattr(module, cls_name)
        self.plugin_instance = plugin_cls()
        self.plugin_instance.manifest = self.manifest # Dict format, not Pydantic
        logger.info(f"Loaded Plugin Class: {cls_name}")

    async def _handle_initialize(self, msg):
        # Unwrap data
        config_snapshot = msg.get("config", {})
        data_dir = msg.get("data_dir", "")
        
        # Minimal Context for Isolated Plugin
        from core.isolation.proxy import RemoteContextStub
        # We define a ConfigStub class dynamically or import it
        class ConfigStub:
             def __init__(self, data):
                 self._data = data
             def __getattr__(self, name):
                 # Recursive return for config.audio.threshold
                 val = self._data.get(name)
                 if isinstance(val, dict): return ConfigStub(val)
                 return val
        
        context = RemoteContextStub(self.event_queue)
        context.config = ConfigStub(config_snapshot)
        context._data_dir = data_dir 
        
        if hasattr(self.plugin_instance, 'initialize'):
             if asyncio.iscoroutinefunction(self.plugin_instance.initialize):
                 await self.plugin_instance.initialize(context)
             else:
                 self.plugin_instance.initialize(context)
                 
        self.event_queue.put({"type": "result", "id": msg["id"], "status": "ok"})

    async def _handle_call(self, msg):
        method_name = msg["method"]
        args = msg.get("args", [])
        kwargs = msg.get("kwargs", {})
        
        try:
            method = getattr(self.plugin_instance, method_name)
            if asyncio.iscoroutinefunction(method):
                res = await method(*args, **kwargs)
            else:
                res = method(*args, **kwargs)
            
            self.event_queue.put({"type": "result", "id": msg["id"], "result": res, "status": "ok"})
        except Exception as e:
            self.event_queue.put({"type": "result", "id": msg["id"], "error": str(e), "status": "error"})

    def _handle_teardown(self):
        if hasattr(self.plugin_instance, 'terminate'):
            self.plugin_instance.terminate()

def host_entrypoint(manifest, ipc, events):
    """Entrypoint for multiprocessing"""
    host = PluginHost(manifest, ipc, events)
    host.run()
