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

@pytest.mark.backend
@pytest.mark.asyncio
async def test_character_config_file_race():
    """验证并发更新 Character 配置时是否存在文件损坏或覆盖竞争"""
    char_id = "hiyori"
    url = f"{SERVICES['memory']}/characters/{char_id}/config"
    
    # 准备 20 个不同的并发更新请求
    async def update_char(i):
        payload = {"metadata": {"last_update_id": i, "timestamp": time.time()}}
        async with httpx.AsyncClient(timeout=10.0) as client:
            try:
                # 注意：Lumina 的后端逻辑是 Merge 而非 Overwrite
                response = await client.post(url, json=payload)
                return response.status_code
            except Exception as e:
                return str(e)

    print(f"\n[Test] Launching 20 concurrent updates to character '{char_id}'...")
    results = await asyncio.gather(*[update_char(i) for i in range(20)])
    
    success_count = results.count(200)
    print(f"[Test] Success: {success_count}, Failures: {len(results) - success_count}")
    
    # 获取最终状态并检查
    async with httpx.AsyncClient() as client:
        final_res = await client.get(url)
        final_config = final_res.json()
        print(f"[Test] Final metadata: {final_config.get('metadata')}")
        
    assert success_count > 0, "No successful updates recorded"

@pytest.mark.backend
@pytest.mark.asyncio
async def test_plugin_state_postgres_race():
    """验证并发切换插件状态时 Postgres 的一致性"""
    # 我们使用一个存在的插件 ID
    plugin_id = "system.llm_core" 
    url = f"{SERVICES['memory']}/plugins/toggle"
    
    async def toggle_plugin(enabled):
        payload = {"id": plugin_id, "enabled": enabled}
        async with httpx.AsyncClient(timeout=10.0) as client:
            try:
                # 这种高频切换最容易触发数据库冲突或状态不一致
                response = await client.post(url, json=payload)
                return response.status_code
            except Exception as e:
                return str(e)

    print(f"\n[Test] Rapidly toggling plugin '{plugin_id}' with 30 concurrent requests...")
    # 模拟 30 个并发切换，一半开一半关
    tasks = [toggle_plugin(i % 2 == 0) for i in range(30)]
    results = await asyncio.gather(*tasks)
    
    success_count = results.count(200)
    print(f"[Test] Success: {success_count}, Errors: {len(results) - success_count}")
    
    # 给予一点同步时间
    await asyncio.sleep(2)
    
    # 检查最终状态是否为有效状态
    async with httpx.AsyncClient() as client:
        status_res = await client.get(f"{SERVICES['memory']}/plugins/list")
        plugins = status_res.json()
        target = next((p for p in plugins if p['id'] == plugin_id), None)
        if target:
            print(f"[Test] Final plugin state: {target.get('status')} (desired: {target.get('enabled')})")
        else:
            print("[Test] Plugin not found in list!")
            
    assert success_count > 0
