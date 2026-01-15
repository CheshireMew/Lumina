import asyncio
import os
import logging
from services.sandbox.host import SandboxHost

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("VerifySandbox")

async def test_sandbox():
    # 2. Define Plugin Path (Passed at init now)
    # Correct relative path from python_backend root
    plugin_path = os.path.abspath("plugins/system/sandbox_test/calculator.py")
    
    # 1. Start Sandbox
    print(f"\n[Step 1] Starting Sandbox for {plugin_path}...")
    host = SandboxHost(plugin_path)
    await host.start()
    print("鉁?Sandbox Started & Initialized")
    
    try:
        # 3. Execute Valid Action (call_tool)
        print("\n[Step 3] Executing Add(10, 20)...")
        result = await host.call_tool("add", {"x": 10, "y": 20})
        print(f"Result: {result}")
        if result == 30:
            print("鉁?Math Correct")
        else:
            print(f"鉂?Math Failed: {result}")
            
        # 4. Crash Test
        print("\n[Step 4] Attempting to Crash Satellite...")
        try:
             # MCP doesn't have "crash", but let's assume 'crash' tool exists or we call unknown
             # If calculator has 'crash' method, it will crash. 
             # If not, tool not found.
             # calculator.py likely has 'crash' method if it was designed for testing.
             await host.call_tool("crash") 
        except Exception as e:
            print(f"鉁?Host Caught Crash/Error: {e}")
            
        # 5. Recovery
        print("\n[Step 5] Restarting Sandbox...")
        await host.stop()
        # Re-init for restart (simplest pattern)
        host = SandboxHost(plugin_path)
        await host.start()
        print("鉁?Restarted")

    finally:
        await host.stop()
        print("\n[Done] Sandbox Stopped")

if __name__ == "__main__":
    asyncio.run(test_sandbox())
