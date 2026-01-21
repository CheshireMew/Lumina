import pytest
import httpx
import asyncio
import random
import time

SERVICES = {
    "memory": "http://127.0.0.1:8010",
}

@pytest.mark.backend
@pytest.mark.asyncio
async def test_distributed_sync_churn():
    """
    模拟多节点/多插件环境下高频状态变动 (Churn Test)。
    验证 PluginService 在高负载下是否能保持最终一致性，且不会出现死锁或堆栈溢出。
    """
    plugin_ids = ["system.llm_core", "system.stt_manager", "system.tts_manager"]
    
    async def simulate_worker_shout(worker_id):
        """模拟一个 Worker 节点向主节点报告状态"""
        url = f"{SERVICES['memory']}/plugins/registry"
        for _ in range(20): # 每个节点报告 20 次
            target_plugin = random.choice(plugin_ids)
            payload = {
                "worker_id": worker_id,
                "plugins": [{
                    "id": target_plugin,
                    "active_status": random.choice(["ready", "busy", "idle"]),
                    "last_updated": time.time()
                }]
            }
            async with httpx.AsyncClient() as client:
                try:
                    await client.post(url, json=payload)
                except Exception:
                    pass
            await asyncio.sleep(0.05) # 高频

    print(f"\n[Test] Launching 5 'pseudo-workers' with high-frequency state updates...")
    workers = [simulate_worker_shout(f"worker_{i}") for i in range(5)]
    await asyncio.gather(*workers)
    
    print("[Test] Churn phase complete. Checking final consistency...")
    
    # 验证主 Registry 是否还能正常列出插件且不报错
    async with httpx.AsyncClient() as client:
        response = await client.get(f"{SERVICES['memory']}/plugins/list")
        assert response.status_code == 200
        data = response.json()
        print(f"[Test] Registry size: {len(data)}")
        
        # 验证每个插件至少有一个状态记录
        for pid in plugin_ids:
            found = any(p['id'] == pid for p in data)
            assert found, f"Plugin {pid} lost during churn!"
            
    print("[Test] Distributed sync consistency verified.")

@pytest.mark.backend
@pytest.mark.asyncio
async def test_rapid_toggle_consistency():
    """高频开关同一个插件，验证 desired_enabled 最终状态是否与最后一次请求一致"""
    plugin_id = "system.llm_core"
    url = f"{SERVICES['memory']}/plugins/toggle"
    
    # 最后一次状态应该是 True
    sequence = [True, False, True, False, True]
    
    print(f"\n[Test] Rapidly toggling '{plugin_id}' in sequence: {sequence}...")
    
    async with httpx.AsyncClient(timeout=10.0) as client:
        for state in sequence:
            await client.post(url, json={"id": plugin_id, "enabled": state})
            
        await asyncio.sleep(2) # 等待同步
    
        response = await client.get(f"{SERVICES['memory']}/plugins/list")
        data = response.json()
        target = next((p for p in data if p['id'] == plugin_id), None)
    
        assert target is not None
        print(f"[Test] Final desired state: {target.get('enabled')}")
        assert target.get('enabled') is True, f"Consistency lost! Expected True, got {target.get('enabled')}"
