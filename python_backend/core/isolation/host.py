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

# Force UTF-8 for Isolated Process (Windows default is GBK)
if sys.platform == "win32":
    sys.stdout.reconfigure(encoding='utf-8')
    sys.stderr.reconfigure(encoding='utf-8')

# Setup logging for child process
logging.basicConfig(
    level=logging.INFO, 
    format='%(asctime)s [%(levelname)s] [PluginHost-%(process)d] %(message)s',
    handlers=[
        logging.StreamHandler(sys.stdout),
        logging.FileHandler("child_process.log", mode='w', encoding='utf-8')
    ]
)
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
            try:
                with open(f"host_debug_{self.manifest.get('id', 'unknown')}.txt", "w") as f:
                    f.write(f"Manifest Keys: {list(self.manifest.keys())}\n")
                    f.write(f"Path: {self.manifest.get('path')}\n")
                    f.write(f"Entrypoint: {self.manifest.get('entrypoint')}\n")
                
                self._load_plugin()
            except Exception as e:
                with open(f"host_crash_{self.manifest.get('id', 'unknown')}.txt", "w") as f:
                    import traceback
                    f.write(traceback.format_exc())
                raise e # Re-raise to trigger main exception handler logging
            
            # 2. Command Loop
            logger.info("Host: Entering Command Loop. Waiting for ipc_queue.get()...")
            while True:
                # Blocking Get
                msg = self.ipc_queue.get()
                logger.info(f"Host: Received message: {msg.get('cmd') if msg else 'None'}")
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
                elif cmd == "event":
                    # [Phase 1] Handle forwarded events from main process
                    self.loop.run_until_complete(self._handle_forwarded_event(msg))
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
        initial_data = msg.get("initial_data", {})  # [Phase 2] Pre-loaded data
        
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
        
        context = RemoteContextStub(self.event_queue, self.manifest['id'])
        context.config = ConfigStub(config_snapshot)
        context._data_dir = data_dir
        context._data_cache = initial_data  # [Phase 2] Set pre-loaded data cache
        
        # [PR-3] Bridge Logging
        # We attach a custom handler to the root logger that forwards to context
        class IPCLogHandler(logging.Handler):
            def emit(self, record):
                try:
                    # Avoid infinite recursion if logging fails in queue put
                    log_entry = {
                        "levelno": record.levelno,
                        "msg": self.format(record),
                        "name": record.name
                    }
                    context.emit_log(log_entry)
                except Exception:
                    pass
        
        # Add handler to root logger
        ipc_handler = IPCLogHandler()
        ipc_handler.setFormatter(logging.Formatter('%(message)s'))
        logging.getLogger().addHandler(ipc_handler)
        logger.info("📡 Logging Bridge Established. Forwarding to Main Process.")
        
        if hasattr(self.plugin_instance, 'initialize'):
             if asyncio.iscoroutinefunction(self.plugin_instance.initialize):
                 await self.plugin_instance.initialize(context)
             else:
                 self.plugin_instance.initialize(context)
                 
        self.event_queue.put({"type": "result", "id": msg["id"], "status": "ok"})

    async def _handle_call(self, msg):
        import types
        import inspect
        
        req_id = msg.get("id")
        method_name = msg.get("method")
        args = msg.get("args", [])
        kwargs = msg.get("kwargs", {})
        
        try:
            method = getattr(self.plugin_instance, method_name)
            
            # Execute
            # Note: iscoroutinefunction returns FALSE for async generators (async def ... yield)
            if asyncio.iscoroutinefunction(method):
                res = await method(*args, **kwargs)
            else:
                # Sync OR Async Generator execution returns the generator object immediately
                res = method(*args, **kwargs)
                
            # [PR-4] Streaming Support
            # Check for Async Generator OR Async Iterator
            is_async_gen = isinstance(res, types.AsyncGeneratorType) or inspect.isasyncgen(res)
            
            if is_async_gen:
                # It's an Async Generator!
                self.event_queue.put({"type": "stream_start", "id": req_id})
                
                async for chunk in res:
                    self.event_queue.put({
                        "type": "stream_chunk", 
                        "id": req_id, 
                        "chunk": chunk
                    })
                    
                self.event_queue.put({"type": "stream_end", "id": req_id})
            
            else:
                # Standard Result
                self.event_queue.put({"type": "result", "id": req_id, "status": "ok", "result": res})
                
        except Exception as e:
            logger.error(f"RPC Call '{method_name}' failed: {e}", exc_info=True)
            self.event_queue.put({"type": "result", "id": req_id, "status": "error", "error": str(e)})

    async def _handle_forwarded_event(self, msg):
        """[Phase 1] Handle events forwarded from main process to child"""
        topic = msg.get("topic")
        event_data = msg.get("event", {})
        
        # Get context from plugin instance
        context = getattr(self.plugin_instance, 'context', None)
        if not context:
            logger.warning(f"No context available to dispatch event '{topic}'")
            return
            
        # Get local handlers registered via context.subscribe()
        handlers = getattr(context, '_local_handlers', {})
        handler = handlers.get(topic)
        
        if handler:
            try:
                if asyncio.iscoroutinefunction(handler):
                    await handler(event_data)
                else:
                    handler(event_data)
                logger.debug(f"📨 Dispatched event '{topic}' to local handler")
            except Exception as e:
                logger.error(f"Error handling forwarded event '{topic}': {e}", exc_info=True)
        else:
            logger.debug(f"No handler registered for event '{topic}'")

    def _handle_teardown(self):
        if hasattr(self.plugin_instance, 'terminate'):
            self.plugin_instance.terminate()

def host_entrypoint(manifest, ipc, events):
    """Entrypoint for multiprocessing"""
    host = PluginHost(manifest, ipc, events)
    host.run()
