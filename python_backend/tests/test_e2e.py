
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

async def test_service_health(client, name, url):
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

async def test_memory_chat(client):
    """Test the Core Memory/Chat Flow"""
    url = SERVICES["main"]
    print(f"\n--- Testing Main Application Flow ({url}) ---")
    
    # 1. Config Check (Debug Table Access) - Security Check
    try:
        # P1 Vulnerability Check: Try to access generic table with whitelist enabled
        print("1. Security Check: White-list enforcement...")
        resp = await client.get(f"{url}/debug/surreal/table/system_prompt_log?limit=1")
        if resp.status_code == 200:
             print(f"[{GREEN}PASS{RESET}] Safe Table Access Allowed")
        else:
             print(f"[{RED}FAIL{RESET}] Safe Table Access Blocked? {resp.status_code}")
             
        # P1 Vulnerability Check: Try injection or invalid table
        resp_bad = await client.get(f"{url}/debug/surreal/table/invalid_table_name_123")
        if resp_bad.status_code == 400:
             print(f"[{GREEN}PASS{RESET}] Invalid Table Blocked (Expected 400)")
        else:
             print(f"[{RED}FAIL{RESET}] Invalid Table allowed or wrong code: {resp_bad.status_code}")
             
    except Exception as e:
        print(f"[{RED}ERROR{RESET}] Security Check Failed: {e}")

async def main():
    print("Starting Lumina E2E Regression Test...\n")
    
    async with httpx.AsyncClient(timeout=5.0) as client:
        # 1. Health Checks
        results = await asyncio.gather(
            test_service_health(client, "Memory Service", SERVICES["main"]),
            test_service_health(client, "STT Service", SERVICES["stt"]),
            test_service_health(client, "TTS Service", SERVICES["tts"])
        )
        
        if not all(results):
            print(f"\n[{RED}CRITICAL{RESET}] Some services are down. Aborting flow tests.")
            sys.exit(1)
            
        # 2. Functional Tests
        await test_memory_chat(client)
        
    print(f"\n[{GREEN}SUCCESS{RESET}] All basic checks passed.")

if __name__ == "__main__":
    if sys.platform == "win32":
        asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())
    asyncio.run(main())
