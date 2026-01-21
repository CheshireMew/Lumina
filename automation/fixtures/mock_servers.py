"""
Mock server fixtures for testing

These provide lightweight HTTP servers for integration testing
without requiring the full application stack.
"""
import asyncio
import json
from typing import AsyncGenerator, Dict, Any
from aiohttp import web
import pytest


class MockHTTPServer:
    """A mock HTTP server for testing"""

    def __init__(self, port: int = 9999):
        self.port = port
        self.app = web.Application()
        self.runner = None
        self.site = None
        self._setup_routes()

    def _setup_routes(self):
        """Setup default routes"""
        self.app.router.add_get("/health", self._health_handler)
        self.app.router.add_post("/api/chat", self._chat_handler)
        self.app.router.add_get("/api/memory", self._memory_handler)

    async def _health_handler(self, request):
        """Health check endpoint"""
        return web.json_response({"status": "healthy", "service": "mock"})

    async def _chat_handler(self, request):
        """Chat completion endpoint"""
        data = await request.json()
        return web.json_response({
            "content": f"Mock response to: {data.get('content', '')}",
            "finish_reason": "stop"
        })

    async def _memory_handler(self, request):
        """Memory retrieval endpoint"""
        return web.json_response({
            "memories": [
                {"id": "1", "content": "Mock memory 1"},
                {"id": "2", "content": "Mock memory 2"}
            ]
        })

    def add_route(self, method: str, path: str, handler):
        """Add a custom route"""
        self.app.router.add_route(method, path, handler)

    async def start(self):
        """Start the server"""
        self.runner = web.AppRunner(self.app)
        await self.runner.setup()
        self.site = web.TCPSite(self.runner, '127.0.0.1', self.port)
        await self.site.start()

    async def stop(self):
        """Stop the server"""
        if self.site:
            await self.site.stop()
        if self.runner:
            await self.runner.cleanup()

    @property
    def base_url(self) -> str:
        """Get the base URL for the server"""
        return f"http://127.0.0.1:{self.port}"


class MockLLMServer(MockHTTPServer):
    """Mock LLM server for testing chat"""

    def __init__(self, port: int = 9998):
        super().__init__(port)
        self.responses = []  # Store request/response pairs

    def _setup_routes(self):
        """Setup LLM-specific routes"""
        super()._setup_routes()
        self.app.router.add_post("/v1/chat/completions", self._completion_handler)
        self.app.router.add_post("/v1/completions", self._completion_handler)

    async def _completion_handler(self, request):
        """OpenAI-compatible completion endpoint"""
        data = await request.json()
        messages = data.get("messages", [])

        # Store request
        self.responses.append({
            "request": data,
            "response": None
        })

        # Generate mock response
        response = {
            "id": f"chatcmpl-{asyncio.get_event_loop().time()}",
            "object": "chat.completion",
            "created": int(asyncio.get_event_loop().time()),
            "model": data.get("model", "mock-model"),
            "choices": [{
                "index": 0,
                "message": {
                    "role": "assistant",
                    "content": f"Mock response for: {messages[-1].get('content', '') if messages else ''}"
                },
                "finish_reason": "stop"
            }],
            "usage": {
                "prompt_tokens": sum(len(m.get('content', '')) for m in messages),
                "completion_tokens": 10,
                "total_tokens": sum(len(m.get('content', '')) for m in messages) + 10
            }
        }

        # Store response
        self.responses[-1]["response"] = response

        return web.json_response(response)

    def get_last_request(self) -> Dict:
        """Get the last request received"""
        if self.responses:
            return self.responses[-1]["request"]
        return {}

    def clear_history(self):
        """Clear request/response history"""
        self.responses = []


class MockMemoryServer(MockHTTPServer):
    """Mock memory/database server for testing"""

    def __init__(self, port: int = 9997):
        super().__init__(port)
        self.memories = {}
        self._counter = 0

    def _setup_routes(self):
        """Setup memory-specific routes"""
        super()._setup_routes()
        self.app.router.add_post("/api/memory/store", self._store_handler)
        self.app.router.add_get("/api/memory/search", self._search_handler)
        self.app.router.add_get("/api/memory/{id}", self._get_handler)
        self.app.router.add_delete("/api/memory/{id}", self._delete_handler)

    async def _store_handler(self, request):
        """Store a memory"""
        data = await request.json()
        self._counter += 1
        memory_id = str(self._counter)
        memory = {
            "id": memory_id,
            **data
        }
        self.memories[memory_id] = memory
        return web.json_response({"id": memory_id, "status": "stored"})

    async def _search_handler(self, request):
        """Search memories"""
        query = request.query.get("q", "")
        results = [
            m for m in self.memories.values()
            if query.lower() in m.get("content", "").lower()
        ]
        return web.json_response({"memories": results, "count": len(results)})

    async def _get_handler(self, request):
        """Get a specific memory"""
        memory_id = request.match_info["id"]
        memory = self.memories.get(memory_id)
        if memory:
            return web.json_response(memory)
        return web.json_response({"error": "Not found"}, status=404)

    async def _delete_handler(self, request):
        """Delete a memory"""
        memory_id = request.match_info["id"]
        if memory_id in self.memories:
            del self.memories[memory_id]
            return web.json_response({"status": "deleted"})
        return web.json_response({"error": "Not found"}, status=404)


# ============================================================================
# Pytest Server Fixtures
# ============================================================================

@pytest.fixture
async def mock_http_server():
    """Provide a running mock HTTP server"""
    server = MockHTTPServer()
    await server.start()
    yield server
    await server.stop()


@pytest.fixture
async def mock_llm_server():
    """Provide a running mock LLM server"""
    server = MockLLMServer()
    await server.start()
    yield server
    await server.stop()


@pytest.fixture
async def mock_memory_server():
    """Provide a running mock memory server"""
    server = MockMemoryServer()
    await server.start()
    yield server
    await server.stop()


@pytest.fixture
async def all_mock_servers(mock_llm_server, mock_memory_server):
    """Provide all mock servers at once"""
    return {
        "llm": mock_llm_server,
        "memory": mock_memory_server,
        "llm_url": mock_llm_server.base_url,
        "memory_url": mock_memory_server.base_url,
    }
