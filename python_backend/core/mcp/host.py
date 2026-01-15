import logging
import asyncio
from typing import Dict, Any, List, Optional
from contextlib import AsyncExitStack

logger = logging.getLogger("MCPManager")

try:
    from mcp import ClientSession, StdioServerParameters
    from mcp.client.stdio import stdio_client
    from mcp.client.sse import sse_client
    MCP_AVAILABLE = True
except ImportError:
    MCP_AVAILABLE = False
    logger.warning("mcp library not installed. MCP features will be disabled.")

class MCPManager:
    """
    璐熻矗绠$悊鎵€鏈夌殑 MCP 杩炴帴 (Clients)銆?
    """
    def __init__(self):
        self.sessions: Dict[str, ClientSession] = {}
        self.exit_stack = AsyncExitStack()
        self.tools_cache: Dict[str, List[Dict]] = {}

    async def connect_stdio(self, name: str, command: str, args: List[str] = [], env: Optional[Dict] = None):
        """
        杩炴帴鍒颁竴涓湰鍦?stdio MCP 鏈嶅姟鍣ㄣ€?
        """
        if not MCP_AVAILABLE:
            return
            
        logger.info(f"Connecting to MCP (stdio): {name} -> {command} {args}")
        try:
            server_params = StdioServerParameters(command=command, args=args, env=env)
            read, write = await self.exit_stack.enter_async_context(stdio_client(server_params))
            session = await self.exit_stack.enter_async_context(ClientSession(read, write))
            await session.initialize()
            
            self.sessions[name] = session
            await self._refresh_tools(name)
            logger.info(f"Connected to MCP: {name}")
            return True
        except Exception as e:
            logger.error(f"Failed to connect to MCP {name}: {e}")
            return False

    async def connect_sse(self, name: str, url: str):
        """
        杩炴帴鍒颁竴涓繙绋?SSE MCP 鏈嶅姟鍣ㄣ€?
        """
        if not MCP_AVAILABLE:
            return

        logger.info(f"Connecting to MCP (SSE): {name} -> {url}")
        try:
            import httpx
            # TODO: Implement full SSE transport logic similar to example reference
            # For simplicity, we assume robust implementation later.
            # Here we use the basic sse_client context manager provided by mcp
            transport = await self.exit_stack.enter_async_context(sse_client(url))
            read, write = transport
            session = await self.exit_stack.enter_async_context(ClientSession(read, write))
            await session.initialize()
            
            self.sessions[name] = session
            await self._refresh_tools(name)
            logger.info(f"Connected to MCP: {name}")
            return True
        except Exception as e:
            logger.error(f"Failed to connect to MCP {name}: {e}")
            return False

    async def _refresh_tools(self, name: str):
        session = self.sessions.get(name)
        if not session:
            return
        
        try:
            result = await session.list_tools()
            tools = result.tools
            # Convert to OpenAI function format
            formatted_tools = []
            for t in tools:
                formatted_tools.append({
                    "type": "function",
                    "function": {
                        "name": t.name,
                        "description": t.description,
                        "parameters": t.inputSchema
                    }
                })
            self.tools_cache[name] = formatted_tools
            logger.info(f"Discovered {len(formatted_tools)} tools for {name}")
        except Exception as e:
            logger.error(f"Failed to list tools for {name}: {e}")

    def get_all_tools(self) -> List[Dict]:
        """
        鑾峰彇鎵€鏈夎繛鎺ョ殑 MCP 宸ュ叿锛屽悎骞朵负涓€涓垪琛ㄨ繑鍥炵粰 LLM銆?
        """
        all_tools = []
        for tools in self.tools_cache.values():
            all_tools.extend(tools)
        return all_tools

    async def call_tool(self, tool_name: str, arguments: Dict[str, Any]) -> Any:
        """
        璋冪敤宸ュ叿銆傞渶瑕侀亶鍘嗘墍鏈?session 鎵惧埌鎷ユ湁璇ュ伐鍏风殑 session銆?
        """
        # 绠€鍗曟煡鎵剧瓥鐣?
        for name, session in self.sessions.items():
            # Check if tool is in this session's cache
            # (Optimization: Build a reverse map tool_name -> session_name)
            cached = self.tools_cache.get(name, [])
            if any(t['function']['name'] == tool_name for t in cached):
                logger.info(f"Calling tool {tool_name} on session {name}")
                return await session.call_tool(tool_name, arguments)
        
        raise ValueError(f"Tool not found: {tool_name}")

    async def cleanup(self):
        await self.exit_stack.aclose()
