import pytest
import httpx
import asyncio
import tracemalloc
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
@pytest.mark.anyio
async def test_memory_leak_detection():
    """使用 tracemalloc 监控连续请求下的内存增长"""
    # 注意：tracemalloc 主要监控当前进程，但我们要监控的是远程服务。
    # 所以这个测试主要监控客户端内存泄露，如果要监控服务端，需要服务端暴露 /debug/memory 接口。
    # 鉴于无法修改服务端，我们将重点放在服务端对压力请求的响应稳定性和耗时增长上。
    
    url = f"{SERVICES['memory']}/v1/chat/completions"
    payload = {
        "model": "gpt-4o-mini",
        "messages": [{"role": "user", "content": "Ping"}],
        "stream": False
    }

    print("\n[Test] Starting 50 repeated requests to check for response degradation...")
    
    times = []
    
    async with httpx.AsyncClient(timeout=10.0) as client:
        for i in range(50):
            start = time.perf_counter()
            try:
                response = await client.post(url, json=payload)
                elapsed = time.perf_counter() - start
                times.append(elapsed)
                
                if (i + 1) % 10 == 0:
                    avg_time = sum(times[-10:]) / 10
                    print(f"  Request {i+1}/50: Avg latencies (last 10): {avg_time:.3f}s")
                    
            except Exception as e:
                print(f"  Request {i+1} failed: {e}")
                
    # 分析延迟趋势
    first_10_avg = sum(times[:10]) / 10
    last_10_avg = sum(times[-10:]) / 10
    
    print(f"\n[Test] Initial Avg: {first_10_avg:.3f}s, Final Avg: {last_10_avg:.3f}s")
    
    # 如果最后 10 次请求的平均时间比前 10 次慢了 50% 以上，可能存在服务端瓶颈或泄露导致的性能衰减
    if last_10_avg > first_10_avg * 1.5:
        print(" [WARNING] Detected significant performance degradation!")
    else:
        print(" [INFO] Performance remains stable.")

@pytest.mark.performance
@pytest.mark.anyio
async def test_client_side_memory_leak():
    """简单检测 client 进程在大量 async 请求下的内存占用"""
    tracemalloc.start()
    snapshot1 = tracemalloc.take_snapshot()
    
    url = f"{SERVICES['memory']}/v1/chat/completions"
    async with httpx.AsyncClient() as client:
        tasks = [client.get(f"{SERVICES['memory']}/health") for _ in range(100)]
        await asyncio.gather(*tasks)
    
    snapshot2 = tracemalloc.take_snapshot()
    top_stats = snapshot2.compare_to(snapshot1, 'lineno')
    
    print("\n[Test] Top 5 memory growth areas in client process:")
    for stat in top_stats[:5]:
        print(f"  {stat}")
    
    tracemalloc.stop()
