import asyncio
import json
import logging
import os
import sys
from typing import Optional, Dict, Any
from app_config import config as app_settings, BASE_DIR
from services.mcp.client import MCPClient

logger = logging.getLogger("MCPHost")

class MCPHost:
    """
    Orchestrator for multiple MCP Satellite Services.
    Uses MCPClient for protocol handling.
    """
    def __init__(self, soul_client):
        self.soul_client = soul_client
        self.clients: Dict[str, MCPClient] = {} 
        self.running = False
        self.servers_dir = os.path.join(BASE_DIR, "mcp_servers")
        self._lock = asyncio.Lock()

    async def start(self):
        """Start all MCP Services in mcp_servers directory"""
        async with self._lock:
            if self.running: return
            self.running = True
            
            logger.info(f"Scanning for MCP servers in: {self.servers_dir}")
            
            if not os.path.exists(self.servers_dir):
                logger.warning(f"MCP servers directory not found: {self.servers_dir}")
                return

            # Scan subdirectories
            for item in os.listdir(self.servers_dir):
                item_path = os.path.join(self.servers_dir, item)
                if os.path.isdir(item_path):
                    server_script = os.path.join(item_path, "server.py")
                    if os.path.exists(server_script):
                        await self._start_server(item, server_script)

    async def _start_server(self, name: str, script_path: str):
        """Launch a single MCP server process using MCPClient"""
        
        # Load Config if exists
        config_path = os.path.join(os.path.dirname(script_path), "config.json")
        server_config = {}
        if os.path.exists(config_path):
            try:
                with open(config_path, 'r', encoding='utf-8') as f:
                    server_config = json.load(f)
            except Exception as e:
                logger.error(f"Failed to load config for {name}: {e}")

        # Check Enabled status
        if server_config.get("enabled", True) is False:
             logger.info(f"MCP Service [{name}] is disabled by config.")
             return
             
        # Create & Start Client
        try:
            # Custom Stderr Handler to forward Bilibili Events
            async def stderr_handler(line: str):
                if line.startswith("EVENT:"):
                    try:
                        data = json.loads(line[6:])
                        await self._handle_event(name, data)
                    except:
                        pass # Ignore malformed events
            
            client = MCPClient(name=name, stderr_handler=stderr_handler)
            
            cmd = [sys.executable, script_path]
            await client.start(cmd=cmd)
            
            self.clients[name] = client
            
            # Auto-Connect Hooks (Generic)
            auto_connect = server_config.get("auto_connect")
            if auto_connect:
                asyncio.create_task(self._delayed_connect(name, auto_connect))
                
        except Exception as e:
            logger.error(f"Failed to spawn MCP process [{name}]: {e}")

    async def _delayed_connect(self, name, rule):
        delay = rule.get("delay", 2)
        await asyncio.sleep(delay)
        
        tool = rule.get("tool")
        args = rule.get("args", {})
        
        # Resolve dynamic args from Plugin Data
        if "args_from_module_data" in rule:
             module_id = rule["args_from_module_data"].get("module_id")
             key_map = rule["args_from_module_data"].get("keys", {})
             
             if module_id and self.soul_client:
                 data = self.soul_client.load_module_data(module_id)
                 for arg_name, data_key in key_map.items():
                     if data_key in data:
                         args[arg_name] = data[data_key]
                     else:
                         logger.warning(f"[{name}] Key {data_key} not found in module {module_id}")

        # Resolve dynamic args from app_settings (Legacy/Global)
        if "args_from_config" in rule:
            for arg_name, config_path in rule["args_from_config"].items():
                parts = config_path.split(".")
                val = app_settings
                try:
                    for p in parts:
                        val = getattr(val, p)
                    args[arg_name] = val
                except Exception as e:
                    pass
        
        if tool:
            await self.call_tool(f"{name}.{tool}", args)

    async def stop(self):
        async with self._lock:
            self.running = False
            logger.info("Stopping all MCP Servers...")
            
            for name, client in self.clients.items():
                try:
                    await client.stop()
                    logger.info(f"Stopped MCP Server: {name}")
                except Exception as e:
                    logger.error(f"Error stopping {name}: {e}")
            
            self.clients.clear()

    async def call_tool(self, tool_name: str, arguments: Dict[str, Any] = {}) -> Any:
        """
        Call a tool.
        Format: "server_name.tool_name"
        """
        if "." not in tool_name:
            logger.warning(f"Invalid tool format '{tool_name}'. Expected 'server.tool'.")
            return None
            
        server_name, tool_method = tool_name.split(".", 1)
        
        client = self.clients.get(server_name)
        if not client:
            logger.warning(f"MCP Server '{server_name}' not running or found.")
            return None
        
        try:
            logger.info(f"Sent Tool Call to [{server_name}]: {tool_method}")
            # This now properly awaits the Future from MCPClient!
            result = await client.call_tool(tool_method, arguments)
            return result
        except Exception as e:
            logger.error(f"Failed to send tool call to [{server_name}]: {e}")
            return None

    async def _handle_event(self, server_name: str, event: Dict):
        """Forward Events to SoulManager (Legacy Event Bus)"""
        user = event.get("user")
        content = event.get("content")
        
        full_msg = f"[{server_name.capitalize()}] {user}: {content}"
        logger.info(f"Forwarding interaction: {full_msg}")
        
        self.soul_client.set_pending_interaction(full_msg, server_name)
