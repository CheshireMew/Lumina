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
@pytest.mark.asyncio
async def test_high_plugin_count_pressure():
    """模拟 100 个插件同时加载和响应的压力"""
    from services.plugin_service import PluginService
    
    # Mock container and system_plugin_manager
    mock_container = MagicMock()
    service = PluginService(mock_container)
    mock_spm = MagicMock()
    mock_container.system_plugin_manager = mock_spm
    
    # 模拟 100 个插件的状态
    stress_plugins = []
    for i in range(100):
        pid = f"plugin_{i}"
        stress_plugins.append({
            "id": pid,
            "name": f"Stress Plugin {i}",
            "enabled": True,
            "category": "system"
        })
    
    mock_spm.list_plugins.return_value = stress_plugins

    start = time.perf_counter()
    # 模拟获取所有插件列表
    plugins = await service.list_all_plugins()
    elapsed = time.perf_counter() - start
    
    assert len(plugins) == 100
    assert elapsed < 0.5, f"Listing 100 plugins took too long: {elapsed:.2f}s"

@pytest.mark.performance
@pytest.mark.asyncio
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
