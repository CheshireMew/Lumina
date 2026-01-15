import sys
import json
import importlib.util
import os
import traceback
import argparse
import inspect
from typing import Any, Dict, List
from pathlib import Path

# Force UTF-8 for IO
sys.stdin.reconfigure(encoding='utf-8')
sys.stdout.reconfigure(encoding='utf-8')

class SandboxWorker:
    def __init__(self, plugin_path: str = None):
        self.plugin_instance = None
        self.plugin_path = plugin_path
        self.tools_schema = []
        
        if self.plugin_path:
            self._load_plugin(self.plugin_path)

    def log(self, message: str, level: str = "INFO"):
        """Emit log entry to stderr (so stdout is kept clean for JSON)"""
        # Format compatible with MCPHost log parser
        sys.stderr.write(f"[{level}] [Worker] {message}\n")
        sys.stderr.flush()

    def run(self):
        self.log(f"Worker started (PID: {os.getpid()}). Waiting for input...")
        
        while True:
            try:
                line = sys.stdin.readline()
                if not line:
                    break # EOF
                
                request = json.loads(line)
                self.process_request(request)
                
            except json.JSONDecodeError:
                self.log(f"Invalid JSON received: {line}", "ERROR")
            except Exception as e:
                self.log(f"Fatal Loop Error: {e}", "CRITICAL")
                traceback.print_exc(file=sys.stderr)

    def process_request(self, request: Dict[str, Any]):
        req_id = request.get("id")
        method = request.get("method")
        params = request.get("params", {})
        
        response = {"jsonrpc": "2.0", "id": req_id}
        
        try:
            if method == "initialize":
                response["result"] = {
                    "protocolVersion": "2024-11-05", # MCP Draft
                    "capabilities": {
                        "tools": {}
                    },
                    "serverInfo": {
                        "name": "Lumina Sandbox Worker",
                        "version": "1.0.0"
                    }
                }
            
            elif method == "tools/list":
                response["result"] = {
                    "tools": self.tools_schema
                }
                
            elif method == "tools/call":
                tool_name = params.get("name")
                args = params.get("arguments", {})
                
                if not self.plugin_instance:
                     raise ValueError("No plugin loaded in this worker.")
                
                # Assume tool_name matches method name
                # Simple security check: do not allow private methods
                if tool_name.startswith("_"):
                     raise ValueError(f"Access denied to private method '{tool_name}'")
                     
                if not hasattr(self.plugin_instance, tool_name):
                     raise ValueError(f"Method '{tool_name}' not found on plugin.")
                
                func = getattr(self.plugin_instance, tool_name)
                
                # Execute
                if inspect.iscoroutinefunction(func):
                    # We are in synchronous loop, run async?
                    # For MVP sandbox, let's assume sync plugins or handle async loop?
                    # Python plugins (like Voiceprint) might be async now.
                    # We need asyncio loop if plugins are async.
                    import asyncio
                    result = asyncio.run(func(**args))
                else:
                    result = func(**args)
                
                # Serialize result if necessary (numpy arrays etc)
                # Helper to jsonify common types
                result = self._serialize(result)
                
                response["result"] = {
                    "content": [{
                        "type": "text",
                        "text": json.dumps(result, default=str)
                    }]
                }
                
            else:
                # Ignore notifications or unknown methods
                if req_id is not None:
                     raise ValueError(f"Method not found: {method}")
                 
        except Exception as e:
            self.log(f"Error processing {method}: {e}", "ERROR")
            response["error"] = {
                "code": -32603,
                "message": str(e),
                "data": traceback.format_exc()
            }
            
        # Send Response
        if req_id is not None:
            print(json.dumps(response), flush=True)

    def _load_plugin(self, path: str):
        self.log(f"Loading plugin from {path}")
        
        p = Path(path)
        entry_module = None
        entry_class = None

        if not p.exists():
            raise FileNotFoundError(f"Plugin path not found: {path}")

        # Strategy 1: Single Python File
        if p.is_file() and p.suffix == ".py":
            entry_module = p
        
        # Strategy 2: Directory or Manifest
        else:
            # Handle manifest.yaml if passed directly
            if p.is_file() and p.name == "manifest.yaml":
                 p = p.parent
            
            manifest_path = p / "manifest.yaml"
            
            # 2a. Try Manifest
            if manifest_path.exists():
                 try:
                     import yaml
                     with open(manifest_path, 'r', encoding='utf-8') as f:
                         m = yaml.safe_load(f)
                         ep = m.get("entrypoint")
                         if ep:
                             mod_name, cls_name = ep.split(":")
                             entry_module = p / f"{mod_name}.py"
                             entry_class = cls_name
                 except Exception as e:
                     self.log(f"Error parsing manifest: {e}", "WARNING")

            # 2b. Fallback Scanning (if manifest failed or missing)
            if not entry_module: 
                 self.log("Scanning for python entrypoint...", "DEBUG")
                 # Order of preference: manager.py -> any .py (except __init__)
                 candidates = list(p.glob("manager.py"))
                 if candidates: 
                     entry_module = candidates[0]
                 else:
                     for f in p.glob("*.py"): 
                         if f.name != "__init__.py": 
                             entry_module = f
                             break
        
        # Validation
        if not entry_module or not entry_module.exists():
             raise FileNotFoundError(f"No suitable python entrypoint found in {path}")
             
        # Import Logic
        try:
            self.log(f"Importing module: {entry_module}")
            spec = importlib.util.spec_from_file_location("sandboxed_plugin", entry_module)
            if not spec or not spec.loader:
                raise ImportError(f"Could not create spec for {entry_module}")
                
            module = importlib.util.module_from_spec(spec)
            sys.modules["sandboxed_plugin"] = module # Register to sys.modules to help imports
            spec.loader.exec_module(module)
            
            # Instantiate
            instance = None
            if entry_class and hasattr(module, entry_class):
                 instance = getattr(module, entry_class)()
            else:
                 # Auto-discovery
                 for name, obj in inspect.getmembers(module, inspect.isclass):
                     # Simple heuristic: Ends with 'Plugin' or 'Manager', or has specific methods?
                     # For test plugin 'calculator.py', class is 'Plugin'.
                     if "Plugin" in name or "Manager" in name:
                         instance = obj()
                         break
            
            if not instance:
                 # Last resort: take the first class defined in this module?
                 for name, obj in inspect.getmembers(module, inspect.isclass):
                     if obj.__module__ == module.__name__:
                         instance = obj()
                         break

            if not instance:
                 raise ValueError("Could not instantiate plugin class (No class found)")
                 
            self.plugin_instance = instance
            self.log(f"Plugin instantiated: {type(instance).__name__}")
            
            # Introspect for Tools
            self._introspect_tools()
            
        except Exception as e:
            self.log(f"Failed to load plugin module: {e}", "ERROR")
            self.log(traceback.format_exc(), "DEBUG")
            raise

    def _introspect_tools(self):
        """Reflect on plugin instance to generate tool definitions"""
        self.tools_schema = []
        for name, method in inspect.getmembers(self.plugin_instance):
            if name.startswith("_"): continue
            if not (inspect.isfunction(method) or inspect.ismethod(method)): continue
            
            # Simple Schema Generation
            # In real system, we'd parse Type Hints
            sig = inspect.signature(method)
            params = {}
            required = []
            
            for param_name, param in sig.parameters.items():
                if param_name == "self": continue
                params[param_name] = {"type": "string"} # Default to string for MVP
                if param.default == inspect.Parameter.empty:
                    required.append(param_name)
                    
            self.tools_schema.append({
                "name": name,
                "description": method.__doc__ or "No description",
                "inputSchema": {
                    "type": "object",
                    "properties": params,
                    "required": required
                }
            })
        self.log(f"Introspected {len(self.tools_schema)} tools.")

    def _serialize(self, obj):
        import numpy as np
        if isinstance(obj, np.ndarray):
            return obj.tolist()
        if isinstance(obj, np.generic):
            return obj.item()
        return obj

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--plugin", help="Path to plugin directory or manifest", required=True)
    args = parser.parse_args()
    
    worker = SandboxWorker(plugin_path=args.plugin)
    worker.run()
