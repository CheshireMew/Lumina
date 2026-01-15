
import asyncio
import asyncio
import sys
import os
import logging

# Add path to sys to import services
sys.path.append(os.path.join(os.getcwd(), "python_backend"))

from services.mcp.client import MCPClient

async def test_mcp_client():
    """
    Test generic MCP Client against the Sandbox Worker (since it's a valid MCP-Lite Server)
    """
    print("\n[TEST] 1. Initializing MCP Client...")
    
    # Use worker.py as a generic MCP server for testing
    worker_script = os.path.join("python_backend", "services", "sandbox", "worker.py")
    plugin_path = os.path.join("python_backend", "plugins", "system", "sandbox_test", "calculator.py")
    
    cmd = [sys.executable, worker_script, "--plugin", plugin_path]
    
    client = MCPClient(name="TestClient")
    
    print("[TEST] 2. Starting Process...")
    await client.start(cmd=cmd, cwd=os.getcwd())
    
    print("[TEST] 3. Sending Handshake...")
    resp = await client.send_initialize()
    print(f"[TEST] Handshake Result: {resp}")
    
    assert resp.get("capabilities"), "Handshake returned empty capabilities"
    

    print("[TEST] 4. Stopping Client...")
    await client.stop()
    print("[TEST] ✅ Unified MCP Client Test Passed")

if __name__ == "__main__":
    logging.basicConfig(level=logging.DEBUG, stream=sys.stdout) # Enable Debug Logs
    if sys.platform == "win32":
        asyncio.set_event_loop_policy(asyncio.WindowsProactorEventLoopPolicy())
    asyncio.run(test_mcp_client())
