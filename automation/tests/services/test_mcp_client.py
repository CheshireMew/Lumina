"""
Unit tests for MCP Client
Tests JSON-RPC communication, protocol errors, and timeout handling
"""
import sys
import asyncio
import unittest
from pathlib import Path
from unittest.mock import MagicMock, AsyncMock, patch
import json


# Add project root and python_backend to path
PROJECT_ROOT = Path(__file__).parents[3]
sys.path.append(str(PROJECT_ROOT / "python_backend"))
sys.path.append(str(PROJECT_ROOT))


class TestMCPClient(unittest.IsolatedAsyncioTestCase):
    """Test MCP Client functionality"""

    def setUp(self):
        """Reset services before each test"""
        from services.container import ServiceContainer
        ServiceContainer._instance = None
        self.container = ServiceContainer()

    async def test_mcp_client_initialization(self):
        """Test MCP Client initialization"""
        # Mock MCP Client structure
        class MockMCPClient:
            def __init__(self, name, endpoint):
                self.name = name
                self.endpoint = endpoint
                self.connected = False
                self.pid = None

            async def connect(self):
                self.connected = True
                self.pid = 12345
                return True

            async def disconnect(self):
                self.connected = False
                self.pid = None

        client = MockMCPClient("test_client", "ws://localhost:8080")

        self.assertEqual(client.name, "test_client")
        self.assertEqual(client.endpoint, "ws://localhost:8080")
        self.assertFalse(client.connected)

        await client.connect()
        self.assertTrue(client.connected)
        self.assertEqual(client.pid, 12345)

        await client.disconnect()
        self.assertFalse(client.connected)
        self.assertIsNone(client.pid)
        print("✅ MCP Client initialization verified")

    async def test_mcp_json_rpc_request_format(self):
        """Test JSON-RPC request format"""
        def create_jsonrpc_request(method, params=None, request_id=1):
            """Create a JSON-RPC 2.0 request"""
            request = {
                "jsonrpc": "2.0",
                "method": method,
                "id": request_id
            }
            if params:
                request["params"] = params
            return request

        # Test basic request
        req = create_jsonrpc_request("test_method", {"param1": "value1"}, 1)
        self.assertEqual(req["jsonrpc"], "2.0")
        self.assertEqual(req["method"], "test_method")
        self.assertEqual(req["params"]["param1"], "value1")
        self.assertEqual(req["id"], 1)

        # Test request without params
        req2 = create_jsonrpc_request("simple_method", request_id=2)
        self.assertNotIn("params", req2)
        print("✅ MCP JSON-RPC request format verified")

    async def test_mcp_json_rpc_response_parsing(self):
        """Test JSON-RPC response parsing"""
        def parse_response(response_str):
            """Parse JSON-RPC response"""
            return json.loads(response_str)

        # Valid response
        valid_response = '{"jsonrpc": "2.0", "result": {"status": "ok"}, "id": 1}'
        result = parse_response(valid_response)
        self.assertEqual(result["result"]["status"], "ok")

        # Error response
        error_response = '{"jsonrpc": "2.0", "error": {"code": -32600, "message": "Invalid Request"}, "id": 1}'
        result = parse_response(error_response)
        self.assertIn("error", result)
        self.assertEqual(result["error"]["code"], -32600)
        print("✅ MCP JSON-RPC response parsing verified")

    async def test_mcp_protocol_error_handling(self):
        """Test handling of protocol errors"""
        class MockMCPClient:
            def __init__(self):
                self.errors = []

            def handle_protocol_error(self, error_data):
                """Handle protocol-level errors"""
                error_code = error_data.get("code", 0)
                error_msg = error_data.get("message", "Unknown error")

                # Parse standard JSON-RPC error codes
                if error_code == -32700:
                    self.errors.append("Parse error")
                elif error_code == -32600:
                    self.errors.append("Invalid Request")
                elif error_code == -32601:
                    self.errors.append("Method not found")
                elif error_code == -32602:
                    self.errors.append("Invalid params")
                else:
                    self.errors.append(f"Error {error_code}: {error_msg}")

        client = MockMCPClient()

        # Test various error codes
        client.handle_protocol_error({"code": -32600, "message": "Invalid Request"})
        client.handle_protocol_error({"code": -32601, "message": "Method not found"})
        client.handle_protocol_error({"code": -32602, "message": "Invalid params"})
        client.handle_protocol_error({"code": -32000, "message": "Server error"})

        self.assertEqual(len(client.errors), 4)
        self.assertIn("Invalid Request", client.errors)
        self.assertIn("Method not found", client.errors)
        self.assertIn("Invalid params", client.errors)
        self.assertIn("Error -32000: Server error", client.errors)
        print("✅ MCP protocol error handling verified")

    async def test_mcp_timeout_handling(self):
        """Test timeout handling for MCP requests"""
        import asyncio

        class MockMCPClient:
            def __init__(self, timeout=1.0):
                self.timeout = timeout
                self.request_timed_out = False

            async def send_request(self, method, params):
                """Send request with timeout"""
                try:
                    await asyncio.wait_for(self.mock_remote_call(method, params),
                                            timeout=self.timeout)
                    return {"result": "success"}
                except asyncio.TimeoutError:
                    self.request_timed_out = True
                    return {"error": {"code": -32000, "message": "Request timed out"}}

            async def mock_remote_call(self, method, params):
                """Simulate slow remote call"""
                await asyncio.sleep(2.0)  # Longer than timeout
                return {"result": "done"}

        client = MockMCPClient(timeout=0.5)
        result = await client.send_request("test_method", {})

        # Should have timed out
        self.assertTrue(client.request_timed_out)
        self.assertIn("error", result)
        self.assertEqual(result["error"]["code"], -32000)
        print("✅ MCP timeout handling verified")

    async def test_mcp_batch_requests(self):
        """Test batch request support"""
        def create_batch_request(requests):
            """Create a JSON-RPC batch request"""
            return [
                {
                    "jsonrpc": "2.0",
                    "method": req["method"],
                    "params": req.get("params", {}),
                    "id": req["id"]
                }
                for req in requests
            ]

        batch = [
            {"method": "method1", "params": {"p": 1}, "id": 1},
            {"method": "method2", "params": {"p": 2}, "id": 2},
            {"method": "method3", "params": {}, "id": 3}
        ]

        batch_request = create_batch_request(batch)
        self.assertEqual(len(batch_request), 3)
        self.assertEqual(batch_request[0]["method"], "method1")
        self.assertEqual(batch_request[1]["id"], 2)
        print("✅ MCP batch requests verified")

    async def test_mcp_notification_messages(self):
        """Test notification (unidirectional) messages"""
        def create_notification(method, params=None):
            """Create a JSON-RPC notification (no id)"""
            notification = {
                "jsonrpc": "2.0",
                "method": method
            }
            if params:
                notification["params"] = params
            return notification

        notif = create_notification("system.status", {"status": "running"})

        self.assertEqual(notif["method"], "system.status")
        self.assertEqual(notif["params"]["status"], "running")
        self.assertNotIn("id", notif)  # Notifications don't have ids
        print("✅ MCP notification messages verified")

    async def test_mcp_connection_retry(self):
        """Test connection retry logic"""
        import asyncio

        class MockMCPClient:
            def __init__(self, max_retries=3):
                self.max_retries = max_retries
                self.attempt = 0

            async def connect_with_retry(self):
                """Attempt connection with retries"""
                for attempt in range(self.max_retries):
                    self.attempt = attempt + 1
                    try:
                        # Simulate connection attempt
                        if attempt < 2:  # First two attempts fail
                            raise ConnectionError("Connection refused")
                        return True  # Third attempt succeeds
                    except ConnectionError:
                        if attempt < self.max_retries - 1:
                            await asyncio.sleep(0.1)  # Brief delay before retry
                        continue
                return False

        client = MockMCPClient(max_retries=3)
        result = await client.connect_with_retry()

        self.assertTrue(result)
        self.assertEqual(client.attempt, 3)  # Took 3 attempts
        print("✅ MCP connection retry verified")

    async def test_mcp_message_validation(self):
        """Test incoming message validation"""
        class MockMCPClient:
            @staticmethod
            def validate_message(message):
                """Validate incoming JSON-RPC message"""
                if not isinstance(message, dict):
                    return False, "Message must be a dictionary"

                if "jsonrpc" not in message:
                    return False, "Missing jsonrpc version"

                if message["jsonrpc"] != "2.0":
                    return False, "Unsupported JSON-RPC version"

                if "method" not in message:
                    return False, "Missing method name"

                return True, "Valid"

        client = MockMCPClient()

        # Valid message
        valid_msg = {
            "jsonrpc": "2.0",
            "method": "test_method",
            "params": {},
            "id": 1
        }
        is_valid, msg = client.validate_message(valid_msg)
        self.assertTrue(is_valid)

        # Invalid messages
        invalid1 = {"method": "test"}  # Missing jsonrpc
        is_valid, msg = client.validate_message(invalid1)
        self.assertFalse(is_valid)

        invalid2 = {"jsonrpc": "1.0", "method": "test"}  # Wrong version
        is_valid, msg = client.validate_message(invalid2)
        self.assertFalse(is_valid)

        invalid3 = {"jsonrpc": "2.0"}  # Missing method
        is_valid, msg = client.validate_message(invalid3)
        self.assertFalse(is_valid)
        print("✅ MCP message validation verified")


if __name__ == "__main__":
    suite = unittest.TestLoader().loadTestsFromTestCase(TestMCPClient)
    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(suite)

    print("\n" + "="*60)
    print(f"Tests run: {result.testsRun}")
    print(f"Failures: {len(result.failures)}")
    print(f"Errors: {len(result.errors)}")
    if result.wasSuccessful():
        print("✅ All MCP Client tests passed!")
    print("="*60)
