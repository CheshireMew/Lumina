import logging
import os
import sys
from typing import Dict, Any
import json
from services.mcp.client import MCPClient

logger = logging.getLogger("SandboxHost")

class SandboxHost(MCPClient):
    """
    Manages a single SandboxWorker process (Satellite).
    Inherits Generic JSON-RPC logic from MCPClient.
    """
    def __init__(self, plugin_path: str = None, transport: str = "stdio", sse_url: str = None):
        super().__init__(name="SandboxHost", transport=transport, sse_url=sse_url)
        self.worker_script = os.path.join(os.path.dirname(__file__), "worker.py")
        self.plugin_path = plugin_path

    async def start(self):
        """Spawns the worker or connects via SSE."""
        if self.transport == "sse":
            await super().start()
            # [FIX] send_initialize removed (handled by client handshake or non-existent)
            # await self.send_initialize({"name": "Lumina Sandbox Host"})
            return
            
        logger.info(f"Starting Sandbox Worker via Stdio for: {self.plugin_path}")
        
        # Build Command for Worker
        cmd = [
            sys.executable, 
            self.worker_script,
            "--plugin", self.plugin_path
        ]
        
        await super().start(cmd=cmd)
        await self.send_initialize({"name": "Lumina Sandbox Host"})
        logger.info("✅ Sandbox Worker Ready")

    async def send_initialize(self, client_info: Dict[str, Any]):
        """
        Sends JSON-RPC initialize request.
        """
        params = {
            "protocolVersion": "2024-11-05",
            "capabilities": {},
            "clientInfo": client_info
        }
        # Use generic call_tool logic which wraps in json-rpc request
        # 'initialize' is just a method in MCP
        return await self.call_tool("initialize", params)

    async def call_tool(self, tool_name: str, arguments: Dict[str, Any] = None) -> Any:
        if arguments is None:
            arguments = {}
        try:
            # Delegate to generic client
            result = await super().call_tool(tool_name, arguments)
            
            # Legacy Sandbox Worker returns {content: [{text: JSON}]} for some reason?
            # Or standard MCP result? Let's normalize here if needed.
            # If standard MCP, result is list of contents.
            
            # Check if result is wrapped in MCP content list
            if isinstance(result, dict) and "content" in result:
                contents = result["content"]
                if isinstance(contents, list) and len(contents) > 0:
                    text_val = contents[0].get("text", "")
                    # Try parsing as JSON if it looks like it?
                    try:
                        return json.loads(text_val)
                    except Exception:
                        return text_val
            
            return result
        except Exception as e:
            logger.error(f"Sandbox Call Error: {e}")
            raise

# Singleton instance placeholder
sandbox = SandboxHost("path/to/plugin")
