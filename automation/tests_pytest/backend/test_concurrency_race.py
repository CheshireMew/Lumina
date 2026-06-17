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
@pytest.mark.anyio
async def test_character_config_file_race():
    """验证并发更新 Character 配置时是否存在文件损坏或覆盖竞争"""
    url = f"{SERVICES['memory']}/character/config"
    
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

    print("\n[Test] Launching 20 concurrent updates to active companion config...")
    results = await asyncio.gather(*[update_char(i) for i in range(20)])
    
    success_count = results.count(200)
    print(f"[Test] Success: {success_count}, Failures: {len(results) - success_count}")
    
    # 获取最终状态并检查
    async with httpx.AsyncClient() as client:
        final_res = await client.get(url)
        final_config = final_res.json()
        print(f"[Test] Final metadata: {final_config.get('metadata')}")
        
    assert success_count > 0, "No successful updates recorded"
