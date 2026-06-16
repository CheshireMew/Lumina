import pytest
import httpx
import asyncio
import time
from pathlib import Path
import sys

# Add python_backend to path
PROJECT_ROOT = Path(__file__).parents[3]
sys.path.insert(0, str(PROJECT_ROOT / "python_backend"))

SERVICES = {
    "memory": "http://127.0.0.1:8010",
}

@pytest.mark.e2e
@pytest.mark.anyio
async def test_streaming_client_disconnect():
    """验证客户端在流式响应中途断开连接后，后端是否能正确处理"""
    url = f"{SERVICES['memory']}/v1/chat/completions"
    payload = {
        "model": "gpt-4o-mini",
        "messages": [{"role": "user", "content": "Write a short sentence."}],
        "stream": True
    }

    print(f"\n[Test] Connecting to {url}...")
    
    try:
        async with httpx.AsyncClient(timeout=15.0) as client:
            async with client.stream("POST", url, json=payload) as response:
                print(f"[Test] Response status: {response.status_code}")
                # Note: Even if it's 500, we want to see if the stream starts
                if response.status_code != 200:
                    print(f"[Test] Warning: Status is {response.status_code}")
                
                count = 0
                async for chunk in response.aiter_lines():
                    count += 1
                    print(f"Received line {count}: {chunk[:50]}...")
                    if count >= 2:
                        print("[Test] Disconnecting abruptly now!")
                        break 
    except httpx.ConnectError:
        print("[Test] ConnectError occurred. Trying with 'localhost' instead of '127.0.0.1'...")
        url = url.replace("127.0.0.1", "localhost")
        # Retry logic or just fail with more info
        raise
    except Exception as e:
        print(f"[Test] Stream info/interruption: {type(e).__name__}: {e}")

    # 等待一会，然后检查服务是否仍然存活
    await asyncio.sleep(1)
    
    print("[Test] Verifying service health...")
    async with httpx.AsyncClient() as client:
        try:
            health = await client.get(f"{SERVICES['memory']}/health")
            print(f"[Test] Health check status: {health.status_code}")
            assert health.status_code == 200
        except Exception as e:
            print(f"[Test] Health check failed: {e}")
            raise

@pytest.mark.e2e
@pytest.mark.anyio
async def test_streaming_timeout_recovery():
    """验证流式响应超时后的恢复能力"""
    url = f"{SERVICES['memory']}/v1/chat/completions"
    
    print(f"\n[Test] Triggering timeout on {url}...")
    async with httpx.AsyncClient(timeout=0.001) as client:
        try:
            await client.post(url, json={
                "model": "gpt-4o-mini",
                "messages": [{"role": "user", "content": "Hello"}],
                "stream": True
            })
        except (httpx.TimeoutException, httpx.ConnectError) as e:
            print(f"[Test] Expected interruption: {type(e).__name__}")
            
    # 立即尝试第二次正常请求
    await asyncio.sleep(1)
    print("[Test] Attempting recovery request...")
    async with httpx.AsyncClient(timeout=10.0) as client:
        try:
            response = await client.get(f"{SERVICES['memory']}/health")
            print(f"[Test] Recovery health check: {response.status_code}")
            assert response.status_code == 200
        except Exception as e:
            print(f"[Test] Recovery failed: {e}")
            raise
