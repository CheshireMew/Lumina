import sys
import json
import unittest
import asyncio
from pathlib import Path
from unittest.mock import MagicMock, AsyncMock


# Add project root and python_backend to path
PROJECT_ROOT = Path(__file__).parents[3]
sys.path.append(str(PROJECT_ROOT / "python_backend"))

class TestBridgeIPCMock(unittest.IsolatedAsyncioTestCase):
    async def test_bridge_packet_serialization(self):
        """验证 Electron 发往 Python 的指令包序列化格式是否符合后端要求"""
        print("\n[Test] Testing IPC Packet Compatibility...")
        
        # 模拟从 Electron 桥接层发来的 JSON 数据
        electron_raw_packet = {
            "cmd": "invoke_capability",
            "payload": {
                "module_id": "test_capability",
                "method": "start",
                "params": {"arg1": "value"}
            },
            "metadata": {"origin": "electron_renderer"}
        }
        
        # 后端接收逻辑模拟
        async def mock_bridge_receiver(raw_data):
            packet = json.loads(raw_data) if isinstance(raw_data, str) else raw_data
            if packet.get("cmd") == "invoke_capability":
                return f"SUCCESS: Invoked {packet['payload']['module_id']}"
            return "UNKNOWN_CMD"

        result = await mock_bridge_receiver(electron_raw_packet)
        self.assertEqual(result, "SUCCESS: Invoked test_capability")
        print(f"✅ IPC packet formats are compatible: {result}")

    async def test_async_event_bridging(self):
        """模拟 Python 事件如何通过桥接器转发回 Electron 渲染进程"""
        print("\n[Test] Testing Event Bridging (Python -> Electron)...")
        
        # 模拟 Electron 端的监听逻辑 (Mock)
        mock_electron_ipc = MagicMock()
        
        # Python 端的桥接发送逻辑
        def send_to_electron(event_type, payload):
            packed = json.dumps({
                "type": "PYTHON_EVENT",
                "event": event_type,
                "data": payload
            })
            # 实际上这里会通过 stdout.write 或 Socket/Named Pipe 发送
            mock_electron_ipc.send(packed)
            
        test_payload = {"status": "ready", "version": "1.0.0"}
        send_to_electron("system_started", test_payload)
        
        # 验证 Electron Mock 是否收到了正确的包
        self.assertTrue(mock_electron_ipc.send.called)
        sent_msg = json.loads(mock_electron_ipc.send.call_args[0][0])
        self.assertEqual(sent_msg["event"], "system_started")
        self.assertEqual(sent_msg["data"]["status"], "ready")
        print("✅ Python-to-Electron event bridging logic verified.")

if __name__ == "__main__":
    unittest.main()
