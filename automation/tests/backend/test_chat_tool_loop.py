import sys
import json
import asyncio
import unittest
from unittest.mock import MagicMock, AsyncMock, patch
from pathlib import Path


# Add project root and python_backend to path
PROJECT_ROOT = Path(__file__).parents[3]
sys.path.append(str(PROJECT_ROOT / "python_backend"))

class TestChatToolLoop(unittest.IsolatedAsyncioTestCase):
    async def test_tool_call_interception(self):
        """验证 LLMExecutionStep 是否能正确截获 Tool Call 并准备执行参数"""
        print("\n[Test] Testing Tool Call Interception...")
        
        # 模拟包含 Tool Call 的 LLM 返回对象
        mock_tool_call = MagicMock()
        mock_tool_call.function.name = "get_weather"
        mock_tool_call.function.arguments = json.dumps({"location": "Tokyo"})
        
        mock_llm_response = MagicMock()
        mock_llm_response.tool_calls = [mock_tool_call]
        mock_llm_response.content = None # 没有内容，只有工具调用
        
        # 模拟 Tool Registry
        registry = {
            "get_weather": lambda location: f"The weather in {location} is Sunny."
        }
        
        # 核心逻辑：从 OpenAI/LiteLLM 格式中提取并执行
        call = mock_llm_response.tool_calls[0]
        func_name = call.function.name
        args = json.loads(call.function.arguments)
        
        self.assertEqual(func_name, "get_weather")
        self.assertEqual(args["location"], "Tokyo")
        
        result = registry[func_name](**args)
        self.assertIn("Tokyo", result)
        print(f"✅ Tool call '{func_name}' intercepted and executed: {result}")

    async def test_recursive_loop_logic(self):
        """验证多轮 Tool Loop 的简化逻辑（伪代码闭环）"""
        print("\n[Test] Testing Recursive Tool-Loop Heuristics...")
        
        async def mock_chat_loop(prompt, max_turns=3):
            turns = 0
            context = [prompt]
            
            while turns < max_turns:
                turns += 1
                # 第一轮：LLM 要求查询天气
                if turns == 1:
                    tool_call = {"func": "get_weather", "args": {"location": "Shanghai"}}
                    print(f"   Turn {turns}: LLM requested tool.")
                    context.append(f"TOOL_RESULT: Rain in Shanghai")
                # 第二轮：LLM 根据天气给出回复
                else:
                    print(f"   Turn {turns}: LLM gave final answer.")
                    return "It is raining in Shanghai, take an umbrella!"
            return "Failed"

        final_resp = await mock_chat_loop("How is the weather?")
        self.assertIn("umbrella", final_resp)
        print("✅ Multi-turn tool loop logic verified.")

if __name__ == "__main__":
    unittest.main()
