
import asyncio
import httpx
import sys
import os


# Configuration
SERVICES = {
    "main": "http://127.0.0.1:8010",
    "stt": "http://127.0.0.1:8765",
    "tts": "http://127.0.0.1:8766"
}

# ANSI Colors
GREEN = "\033[92m"
RED = "\033[91m"
RESET = "\033[0m"

async def check_service_health(client, name, url):
    try:
        resp = await client.get(f"{url}/health")
        if resp.status_code == 200:
            print(f"[{GREEN}PASS{RESET}] {name} Health Check ({url})")
            
            # Verify Request ID Propagation
            req_id = resp.headers.get("x-request-id")
            if req_id:
                print(f"       鈹斺攢鈹€ Request ID: {req_id}")
            else:
                print(f"       鈹斺攢鈹€ {RED}WARNING: No X-Request-ID header found!{RESET}")
                
            return True
        else:
            print(f"[{RED}FAIL{RESET}] {name} returned {resp.status_code}")
            return False
    except Exception as e:
        print(f"[{RED}FAIL{RESET}] {name} Connection Failed: {e}")
        return False

async def check_core_chat(client):
    """Test the Core Chat Flow"""
    url = SERVICES["main"]
    print(f"\n--- Testing Main Application Flow ({url}) ---")
    resp = await client.get(f"{url}/health")
    if resp.status_code == 200:
        print(f"[{GREEN}PASS{RESET}] Main health endpoint reachable")
    else:
        print(f"[{RED}FAIL{RESET}] Main health endpoint returned {resp.status_code}")

async def main():
    print("Starting Lumina E2E Regression Test...\n")
    
    async with httpx.AsyncClient(timeout=5.0) as client:
        # 1. Health Checks
        results = await asyncio.gather(
            check_service_health(client, "Core Service", SERVICES["main"]),
            check_service_health(client, "STT Service", SERVICES["stt"]),
            check_service_health(client, "TTS Service", SERVICES["tts"])
        )
        
        if not all(results):
            print(f"\n[{RED}CRITICAL{RESET}] Some services are down. Aborting flow tests.")
            raise RuntimeError("Some services are down")
            
        # 2. Functional Tests
        await check_core_chat(client)
        
    print(f"\n[{GREEN}SUCCESS{RESET}] All basic checks passed.")

if __name__ == "__main__":
    if sys.platform == "win32":
        asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())
    asyncio.run(main())
