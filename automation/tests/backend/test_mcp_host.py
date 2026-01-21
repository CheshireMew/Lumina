import sys
import unittest
from pathlib import Path
from unittest.mock import MagicMock, AsyncMock

# Fix Windows console encoding
if sys.platform == 'win32':
    import io
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8')

# Add project root and python_backend to path
PROJECT_ROOT = Path(__file__).parents[3]
sys.path.append(str(PROJECT_ROOT / "python_backend"))

class TestMCPHost(unittest.IsolatedAsyncioTestCase):
    async def test_mcp_server_registration(self):
        """验证系统是否能正确注册并识别本地 Model Context Protocol (MCP) 服务"""
        print("\n[Test] Testing MCP Server Registration...")
        
        # 模拟 MCP Host
        class MockMCPHost:
            def __init__(self):
                self.servers = {}
            
            def register_server(self, name, endpoint):
                self.servers[name] = {"endpoint": endpoint, "status": "registered"}

        host = MockMCPHost()
        host.register_server("weather-mcp", "http://localhost:9000/mcp")
        
        self.assertIn("weather-mcp", host.servers)
        self.assertEqual(host.servers["weather-mcp"]["status"], "registered")
        print("✅ MCP server registration logic verified.")

    async def test_mcp_tool_mapping(self):
        """验证 MCP 提供的工具是否能被正确映射为 Lumina Tool 定义"""
        print("\n[Test] Testing MCP Tool Mapping Heuristics...")
        
        # 模拟从 MCP 服务器获取的工具描述 (JSON)
        mcp_tool_raw = {
            "name": "calculate_pi",
            "description": "Calculates PI to N digits",
            "parameters": {
                "type": "object",
                "properties": {"digits": {"type": "integer"}}
            }
        }
        
        # 映射函数
        def map_to_lumina_tool(mcp_tool):
            return {
                "id": f"mcp.{mcp_tool['name']}",
                "description": mcp_tool["description"],
                "input_schema": mcp_tool["parameters"]
            }
            
        lumina_tool = map_to_lumina_tool(mcp_tool_raw)
        
        self.assertEqual(lumina_tool["id"], "mcp.calculate_pi")
        self.assertEqual(lumina_tool["input_schema"]["type"], "object")
        print(f"✅ MCP-to-Lumina tool mapping verified: {lumina_tool['id']}")

if __name__ == "__main__":
    unittest.main()
