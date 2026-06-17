import pytest
import httpx
import asyncio
import json
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
async def test_multi_turn_tool_loop_failure():
    """
    验证系统是否存在‘单轮工具限制’。
    如果 LLM 第一轮调用了工具，在获取结果后需要再次调用工具才能完成任务，
    当前的架构（pipeline.py）会强制进入 Final Pass 并禁用工具，导致多轮逻辑中断。
    """
    url = f"{SERVICES['memory']}/companion/message"
    
    # 构造一个需要两步搜索的任务：
    # 1. 搜索 A 的最新成员 (假设是个虚构或实时变化的)
    # 2. 搜索该成员的出生地
    prompt = "First, use web_search to find the current CEO of a fictional company 'Z-Alpha' (just assume it returns 'John Doe'). Then, use web_search again to find where 'John Doe' was born."
    
    payload = {"model": "gpt-4o-mini", "text": prompt}

    print(f"\n[Test] Sending multi-turn tool request to {url}...")
    
    async with httpx.AsyncClient(timeout=30.0) as client:
        try:
            response = await client.post(url, json=payload)
            print(f"[Test] Status: {response.status_code}")
            
            if response.status_code == 200:
                data = response.json()
                content = data["content"]
                print(f"[Test] Response: {content}")
                
                # 如果系统只能做一轮工具调用，它可能会在找不到 CEO 出生地的情况下胡编乱造，
                # 或者直接说由于某种原因无法继续。
                # 关键在于观察它是否真的尝试了第二次调用（可以通过后端日志查看，或者在这里观察回答的逻辑连贯性）
            
            elif response.status_code == 500:
                print("[Test] Server returned 500 (Expected if soul_client bug hits)")
                
        except Exception as e:
            print(f"[Test] Failed: {e}")

@pytest.mark.e2e
@pytest.mark.anyio
async def test_tool_output_injection_consistency():
    """验证工具返回的结果是否被正确注入到上下文中"""
    url = f"{SERVICES['memory']}/companion/message"
    
    # 强制让 LLM 调用工具并验证它是否看到了结果
    prompt = "Use web_search to find the 'Secret Code of Lumina 2026'. (It's just for testing, tell me whatever you find)"
    
    payload = {"model": "gpt-4o-mini", "text": prompt}
    
    async with httpx.AsyncClient(timeout=30.0) as client:
        response = await client.post(url, json=payload)
        if response.status_code == 200:
            print(f"[Test] Tool usage response: {response.json()['content'][:200]}")
        else:
            print(f"[Test] Status {response.status_code}")
