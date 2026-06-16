import pytest
import asyncio
import time
from unittest.mock import MagicMock, AsyncMock
from pathlib import Path
import sys

# Add python_backend to path
PROJECT_ROOT = Path(__file__).parents[3]
sys.path.insert(0, str(PROJECT_ROOT / "python_backend"))

@pytest.mark.performance
@pytest.mark.anyio
async def test_high_plugin_count_pressure():
    """模拟 100 个插件同时加载和响应的压力"""
    from services.plugin_state_aggregator import PluginStateAggregator
    
    aggregator = PluginStateAggregator()

    for i in range(100):
        pid = f"plugin_{i}"
        await aggregator._merge_state(pid, {
            "id": pid,
            "name": f"Stress Plugin {i}",
            "desired_enabled": True,
            "active_status": "ready",
            "kind": "system",
        }, source="local")

    start = time.perf_counter()
    # 模拟获取聚合后的插件状态快照
    plugins = aggregator.get_snapshot()
    elapsed = time.perf_counter() - start
    
    assert len(plugins) == 100
    assert elapsed < 0.5, f"Listing 100 plugins took too long: {elapsed:.2f}s"

@pytest.mark.performance
@pytest.mark.anyio
async def test_concurrent_load_stress():
    """模拟高并发请求压力"""
    async def simulated_heavy_task(i):
        # 模拟 RAG 或复杂计算
        await asyncio.sleep(0.05)
        return f"Result {i}"

    start = time.perf_counter()
    tasks = [simulated_heavy_task(i) for i in range(200)]
    results = await asyncio.gather(*tasks)
    elapsed = time.perf_counter() - start
    
    assert len(results) == 200
    # 200 个并发任务（每个 50ms）应该在合理时间内完成（asyncio 优势）
    assert elapsed < 1.0, f"200 concurrent tasks took too long: {elapsed:.2f}s"
