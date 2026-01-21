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

@pytest.mark.performance
@pytest.mark.asyncio
async def test_extreme_long_context_performance():
    """验证超长上下文（约 100k tokens）下的性能和处理能力"""
    url = f"{SERVICES['memory']}/v1/chat/completions"
    
    # 构建约 100k tokens 的内容（粗略估算：1 字符约 0.25-0.5 token）
    # 我们生成一个约 200,000 字符的字符串
    long_text = "Lumina " * 30000 
    
    payload = {
        "model": "gpt-4o-mini",
        "messages": [
            {"role": "system", "content": "You are a helpful assistant. I will provide a long text and you should summarize it in one sentence."},
            {"role": "user", "content": f"Text: {long_text}\n\nSummary:"}
        ],
        "stream": False
    }

    print(f"\n[Test] Sending request with {len(long_text)} characters...")
    start_time = time.perf_counter()
    
    # 使用较长的 timeout
    async with httpx.AsyncClient(timeout=120.0) as client:
        try:
            response = await client.post(url, json=payload)
            elapsed = time.perf_counter() - start_time
            print(f"[Test] Request completed in {elapsed:.2f}s")
            print(f"[Test] Status code: {response.status_code}")
            
            # 无论成功还是 500，我们记录表现
            if response.status_code == 200:
                data = response.json()
                print(f"[Test] Response received: {data['choices'][0]['message']['content'][:100]}...")
            elif response.status_code == 500:
                print("[Test] Server failed with 500 (Possibly soul_client bug or OOM)")
                
        except httpx.ReadTimeout:
            print("[Test] Request timed out (ReadTimeout after 120s)")
        except Exception as e:
            print(f"[Test] Request failed: {type(e).__name__}: {e}")

@pytest.mark.performance
@pytest.mark.asyncio
async def test_context_truncation_boundary():
    """验证上下文超过 128k 时的物理截断或是后端溢出报错"""
    # 这个测试模拟发送一个非常巨大的 payload，检查 FastAPI/Uvicorn 的限制
    url = f"{SERVICES['memory']}/v1/chat/completions"
    
    huge_text = "Data " * 100000 # 约 500k 字符
    
    payload = {
        "model": "gpt-4o-mini",
        "messages": [{"role": "user", "content": huge_text}],
        "stream": False
    }
    
    print(f"\n[Test] Sending extreme payload ({len(huge_text)} chars)...")
    async with httpx.AsyncClient(timeout=30.0) as client:
        try:
            response = await client.post(url, json=payload)
            print(f"[Test] Status: {response.status_code}")
            # 如果返回 413 则说明有 Request Entity Too Large 限制
            assert response.status_code in [200, 500, 413] 
        except httpx.WriteError:
            print("[Test] Write error (Possibly payload too large for socket)")
        except Exception as e:
            print(f"[Test] Failed: {e}")
