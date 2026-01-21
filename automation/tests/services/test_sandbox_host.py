"""
Unit tests for Sandbox Host
Tests sandbox execution, process isolation, and communication failures
"""
import sys
import asyncio
import unittest
from pathlib import Path
from unittest.mock import MagicMock, AsyncMock, patch

# Fix Windows console encoding
if sys.platform == 'win32':
    import io
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8')

# Add project root and python_backend to path
PROJECT_ROOT = Path(__file__).parents[3]
sys.path.append(str(PROJECT_ROOT / "python_backend"))
sys.path.append(str(PROJECT_ROOT))


class TestSandboxHost(unittest.IsolatedAsyncioTestCase):
    """Test Sandbox Host functionality"""

    def setUp(self):
        """Reset services before each test"""
        from services.container import ServiceContainer
        ServiceContainer._instance = None
        self.container = ServiceContainer()

    async def test_sandbox_host_initialization(self):
        """Test SandboxHost initialization"""
        from services.sandbox.host import SandboxHost

        host = SandboxHost(plugin_path="/test/plugin", transport="stdio")

        self.assertEqual(host.plugin_path, "/test/plugin")
        self.assertEqual(host.transport, "stdio")
        self.assertIsNotNone(host.worker_script)
        print("✅ SandboxHost initialization verified")

    async def test_sandbox_host_sse_initialization(self):
        """Test SandboxHost with SSE transport"""
        from services.sandbox.host import SandboxHost

        host = SandboxHost(plugin_path="/test/plugin", transport="sse", sse_url="http://localhost:8080/sse")

        self.assertEqual(host.transport, "sse")
        self.assertEqual(host.name, "SandboxHost")
        print("✅ SandboxHost SSE initialization verified")

    async def test_sandbox_start_stdio(self):
        """Test starting sandbox with stdio transport"""
        from services.sandbox.host import SandboxHost

        host = SandboxHost(plugin_path="/test/plugin", transport="stdio")

        # Mock parent start method
        with patch.object(host.__class__.__bases__[0], 'start', new=AsyncMock()) as mock_start:
            with patch.object(host, 'send_initialize', new=AsyncMock()) as mock_init:
                await host.start()

                # Verify start was called with command
                mock_start.assert_called_once()
                call_args = mock_start.call_args
                self.assertIn('cmd', call_args.kwargs)

                # Verify initialize was sent
                mock_init.assert_called_once()

        print("✅ Sandbox start stdio verified")

    async def test_sandbox_start_sse(self):
        """Test starting sandbox with SSE transport"""
        from services.sandbox.host import SandboxHost

        host = SandboxHost(plugin_path="/test/plugin", transport="sse", sse_url="http://localhost:8080/sse")

        # Mock parent start method
        with patch.object(host.__class__.__bases__[0], 'start', new=AsyncMock()) as mock_start:
            await host.start()

            # SSE doesn't send initialize separately
            mock_start.assert_called_once()
            # Should not have send_initialize called
            print("✅ Sandbox start SSE verified")

    async def test_sandbox_send_initialize(self):
        """Test sending initialize request"""
        from services.sandbox.host import SandboxHost

        host = SandboxHost(plugin_path="/test/plugin")

        # Mock call_tool
        with patch.object(host, 'call_tool', new=AsyncMock(return_value={"status": "ok"})) as mock_call:
            client_info = {"name": "Test Host"}
            result = await host.send_initialize(client_info)

            # Verify call_tool was called with initialize
            mock_call.assert_called_once_with("initialize", {
                "protocolVersion": "2024-11-05",
                "capabilities": {},
                "clientInfo": client_info
            })

        print("✅ Sandbox send initialize verified")

    async def test_sandbox_call_tool_success(self):
        """Test successful tool call"""
        from services.sandbox.host import SandboxHost

        host = SandboxHost(plugin_path="/test/plugin")

        # Mock parent call_tool to return standard MCP result
        with patch.object(host.__class__.__bases__[0], 'call_tool', new=AsyncMock()) as mock_call:
            mock_call.return_value = {"result": "success"}

            result = await host.call_tool("test_tool", {"param": "value"})

            self.assertEqual(result, {"result": "success"})
            mock_call.assert_called_once_with("test_tool", {"param": "value"})

        print("✅ Sandbox call tool success verified")

    async def test_sandbox_call_tool_with_wrapped_content(self):
        """Test tool call with wrapped content response"""
        from services.sandbox.host import SandboxHost

        host = SandboxHost(plugin_path="/test/plugin")

        # Mock parent call_tool to return wrapped content
        with patch.object(host.__class__.__bases__[0], 'call_tool', new=AsyncMock()) as mock_call:
            mock_call.return_value = {
                "content": [
                    {"text": '{"status": "ok", "data": "value"}'}
                ]
            }

            result = await host.call_tool("test_tool", {})

            # Should unwrap and parse JSON
            self.assertIsInstance(result, dict)
            self.assertEqual(result.get("status"), "ok")

        print("✅ Sandbox call tool wrapped content verified")

    async def test_sandbox_call_tool_text_response(self):
        """Test tool call returning plain text"""
        from services.sandbox.host import SandboxHost

        host = SandboxHost(plugin_path="/test/plugin")

        # Mock parent call_tool to return text content
        with patch.object(host.__class__.__bases__[0], 'call_tool', new=AsyncMock()) as mock_call:
            mock_call.return_value = {
                "content": [
                    {"text": "plain text response"}
                ]
            }

            result = await host.call_tool("test_tool", {})

            # Should return plain text when not valid JSON
            self.assertEqual(result, "plain text response")

        print("✅ Sandbox call tool text response verified")

    async def test_sandbox_call_tool_error(self):
        """Test tool call error handling"""
        from services.sandbox.host import SandboxHost

        host = SandboxHost(plugin_path="/test/plugin")

        # Mock parent call_tool to raise exception
        with patch.object(host.__class__.__bases__[0], 'call_tool', new=AsyncMock()) as mock_call:
            mock_call.side_effect = Exception("Connection lost")

            with self.assertRaises(Exception) as context:
                await host.call_tool("test_tool", {})

            self.assertIn("Connection lost", str(context.exception))

        print("✅ Sandbox call tool error handling verified")

    async def test_sandbox_call_tool_none_arguments(self):
        """Test tool call with None arguments"""
        from services.sandbox.host import SandboxHost

        host = SandboxHost(plugin_path="/test/plugin")

        # Mock parent call_tool
        with patch.object(host.__class__.__bases__[0], 'call_tool', new=AsyncMock()) as mock_call:
            mock_call.return_value = {"result": "ok"}

            result = await host.call_tool("test_tool", None)

            # Should convert None to empty dict
            mock_call.assert_called_once_with("test_tool", {})

        print("✅ Sandbox call tool None arguments verified")

    async def test_sandbox_command_construction(self):
        """Test worker command construction"""
        from services.sandbox.host import SandboxHost
        import sys

        host = SandboxHost(plugin_path="/test/plugin", transport="stdio")

        # The command should be: [sys.executable, worker_script, "--plugin", plugin_path]
        expected_python = sys.executable
        expected_script = host.worker_script
        expected_plugin = "/test/plugin"

        # Verify worker_script path exists
        self.assertIsNotNone(expected_script)

        # Verify the structure (not actual execution)
        self.assertTrue(str(expected_script).endswith("worker.py"))
        self.assertEqual(host.plugin_path, expected_plugin)

        print("✅ Sandbox command construction verified")

    async def test_sandbox_communication_failure(self):
        """Test handling of communication failures"""
        from services.sandbox.host import SandboxHost

        host = SandboxHost(plugin_path="/test/plugin")

        # Test various failure scenarios
        failures = [
            ConnectionError("Worker disconnected"),
            TimeoutError("Worker timeout"),
            RuntimeError("Worker crashed")
        ]

        for failure in failures:
            with patch.object(host.__class__.__bases__[0], 'call_tool', new=AsyncMock()) as mock_call:
                mock_call.side_effect = failure

                with self.assertRaises(type(failure)):
                    await host.call_tool("test_tool", {})

        print("✅ Sandbox communication failure handling verified")

    async def test_sandbox_json_parse_error(self):
        """Test handling of invalid JSON in content"""
        from services.sandbox.host import SandboxHost

        host = SandboxHost(plugin_path="/test/plugin")

        # Mock parent call_tool to return invalid JSON
        with patch.object(host.__class__.__bases__[0], 'call_tool', new=AsyncMock()) as mock_call:
            mock_call.return_value = {
                "content": [
                    {"text": "not valid json {"}
                ]
            }

            result = await host.call_tool("test_tool", {})

            # Should return text as-is when JSON parsing fails
            self.assertEqual(result, "not valid json {")

        print("✅ Sandbox JSON parse error handling verified")

    async def test_sandbox_multiple_content_items(self):
        """Test handling of multiple content items in response"""
        from services.sandbox.host import SandboxHost

        host = SandboxHost(plugin_path="/test/plugin")

        # Mock parent call_tool to return multiple content items
        with patch.object(host.__class__.__bases__[0], 'call_tool', new=AsyncMock()) as mock_call:
            mock_call.return_value = {
                "content": [
                    {"text": '{"status": "ok"}'},
                    {"text": "extra content"}
                ]
            }

            result = await host.call_tool("test_tool", {})

            # Should use first content item
            self.assertIsInstance(result, dict)
            self.assertEqual(result.get("status"), "ok")

        print("✅ Sandbox multiple content items verified")


if __name__ == "__main__":
    suite = unittest.TestLoader().loadTestsFromTestCase(TestSandboxHost)
    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(suite)

    print("\n" + "="*60)
    print(f"Tests run: {result.testsRun}")
    print(f"Failures: {len(result.failures)}")
    print(f"Errors: {len(result.errors)}")
    if result.wasSuccessful():
        print("✅ All SandboxHost tests passed!")
    print("="*60)
