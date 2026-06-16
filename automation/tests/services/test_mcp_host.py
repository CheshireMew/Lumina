import sys
import types
from pathlib import Path

import pytest

PROJECT_ROOT = Path(__file__).parents[3]
sys.path.insert(0, str(PROJECT_ROOT / "python_backend"))

aiohttp_stub = types.ModuleType("aiohttp")
aiohttp_stub.ClientSession = object
sys.modules.setdefault("aiohttp", aiohttp_stub)

from services.mcp_host import MCPHost


class FakeSoulService:
    def __init__(self):
        self.modules = {"module.alpha": {"token": "secret"}}

    def load_module_data(self, module_id: str):
        return self.modules.get(module_id, {})


@pytest.mark.anyio
async def test_mcp_host_requires_soul_service():
    with pytest.raises(ValueError, match="SoulService is required"):
        MCPHost(None)


@pytest.mark.anyio
async def test_mcp_host_resolves_auto_connect_args_from_soul_module_data():
    host = MCPHost(FakeSoulService())
    calls = []

    async def capture_call(tool_name, arguments=None):
        calls.append((tool_name, arguments))

    host.call_tool = capture_call

    await host._delayed_connect(
        "server",
        {
            "delay": 0,
            "tool": "login",
            "args": {},
            "args_from_module_data": {
                "module_id": "module.alpha",
                "keys": {"api_token": "token"},
            },
        },
    )

    assert calls == [("server.login", {"api_token": "secret"})]
