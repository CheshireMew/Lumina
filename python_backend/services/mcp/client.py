import asyncio
import json
import logging
import os
import sys
import uuid
import aiohttp
from typing import Optional, Dict, Any, Callable, Awaitable

logger = logging.getLogger("MCPClient")

class MCPClient:
    """
    Generic MCP-Lite Client.
    Supports JSON-RPC over Stdio or SSE.
    """
    def __init__(self, name: str, transport: str = "stdio", sse_url: str = None, stderr_handler: Callable[[str], Awaitable[None]] = None):
        self.name = name
        self.transport = transport
        self.sse_url = sse_url
        self.stderr_handler = stderr_handler
        
        self.process: Optional[asyncio.subprocess.Process] = None
        self.session: Optional[aiohttp.ClientSession] = None
        self._msg_id = 0
        self._pending_requests: Dict[int, asyncio.Future] = {}
        
        self.running = False
        self._reader_task = None
        self._stderr_task = None

    async def start(self, cmd: list = None):
        """Start the client connection/process"""
        if self.running: return
        self.running = True
        
        if self.transport == "stdio":
            if not cmd:
                raise ValueError("Command required for stdio transport")
            
            logger.info(f"[{self.name}] Starting process: {cmd}")
            self.process = await asyncio.create_subprocess_exec(
                *cmd,
                stdin=asyncio.subprocess.PIPE,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )
            
            self._reader_task = asyncio.create_task(self._read_stdout())
            self._stderr_task = asyncio.create_task(self._read_stderr())
            
        elif self.transport == "sse":
            if not self.sse_url:
                raise ValueError("SSE URL required for sse transport")
            self.session = aiohttp.ClientSession()
            raise NotImplementedError("SSE transport not yet fully implemented")

    async def stop(self):
        """Stop the client"""
        self.running = False
        
        if self.process:
            try:
                self.process.terminate()
                await self.process.wait()
            except Exception as e:
                logger.error(f"[{self.name}] Error stopping process: {e}")
        
        if self.session:
            await self.session.close()

    async def _read_stdout(self):
        """Read JSON-RPC messages from stdout"""
        if not self.process: return
        
        try:
            while self.running:
                line = await self.process.stdout.readline()
                if not line: break
                
                line_str = line.decode('utf-8').strip()
                if not line_str: continue
                
                try:
                    data = json.loads(line_str)
                    await self._handle_message(data)
                except json.JSONDecodeError:
                    logger.warning(f"[{self.name}] Non-JSON Output: {line_str}")
                except Exception as e:
                    logger.error(f"[{self.name}] Message Error: {e}")
                    
        except Exception as e:
            logger.error(f"[{self.name}] Reader Error: {e}")

    async def _read_stderr(self):
        """Read logging/debug from stderr"""
        if not self.process: return
        
        try:
            while self.running:
                line = await self.process.stderr.readline()
                if not line: break
                
                line_str = line.decode('utf-8').strip()
                if not line_str: continue
                
                if self.stderr_handler:
                    try:
                        await self.stderr_handler(line_str)
                    except Exception as e:
                        logger.error(f"[{self.name}] Stderr handler error: {e}")
                
                logger.debug(f"[{self.name}] STDERR: {line_str}")
        except Exception as e:
            pass 

    async def _handle_message(self, data: Dict):
        """Handle incoming JSON-RPC"""
        if "id" in data and "result" in data:
            req_id = data["id"]
            if req_id in self._pending_requests:
                self._pending_requests[req_id].set_result(data["result"])
                del self._pending_requests[req_id]
        
        elif "id" in data and "error" in data:
            req_id = data["id"]
            if req_id in self._pending_requests:
                self._pending_requests[req_id].set_exception(Exception(data["error"]))
                del self._pending_requests[req_id]

    async def call_tool(self, method: str, params: Dict = {}) -> Any:
        """Send JSON-RPC Request"""
        if not self.running:
            raise RuntimeError("Client not running")

        self._msg_id += 1
        req_id = self._msg_id
        
        request = {
            "jsonrpc": "2.0",
            "method": method,
            "params": params,
            "id": req_id
        }
        
        if self.transport == "stdio" and self.process:
            content = json.dumps(request) + "\n"
            self.process.stdin.write(content.encode('utf-8'))
            await self.process.stdin.drain()
            
            loop = asyncio.get_running_loop()
            future = loop.create_future()
            self._pending_requests[req_id] = future
            
            try:
                return await asyncio.wait_for(future, timeout=30.0)
            except asyncio.TimeoutError:
                if req_id in self._pending_requests:
                    del self._pending_requests[req_id]
                raise TimeoutError(f"Tool call {method} timed out")
        else:
            raise RuntimeError("Transport not available")
