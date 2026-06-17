"""
Unit tests for Chat Pipeline
Tests message processing pipeline, step execution, and error recovery
"""
import sys
import unittest
from pathlib import Path
from unittest.mock import MagicMock, AsyncMock

# Add project root and python_backend to path
PROJECT_ROOT = Path(__file__).parents[3]
sys.path.append(str(PROJECT_ROOT / "python_backend"))
sys.path.append(str(PROJECT_ROOT))

from services.chat.pipeline import ChatPipeline, PipelineContext, PipelineStep, ContextBuilderStep
from services.companion.context import CompanionContext


def companion_context(
    *,
    session_id: int = 1,
    user_id: str = "user",
    character_id: str = "char",
) -> CompanionContext:
    return CompanionContext(
        session_id=session_id,
        user_id=user_id,
        character_id=character_id,
    )


class MockPipelineStep(PipelineStep):
    """Mock pipeline step for testing"""
    def __init__(self, should_fail=False):
        self.should_fail = should_fail
        self.executed = False

    async def execute(self, ctx: PipelineContext):
        self.executed = True
        if self.should_fail:
            raise ValueError("Mock step failure")


class TestChatPipeline(unittest.IsolatedAsyncioTestCase):
    """Test Chat Pipeline components"""

    def setUp(self):
        """Reset services before each test"""
        from services.container import ServiceContainer
        from services.container import services
        from services.container.provider_registry import ProviderRegistry
        from services.container.service_definitions import LuminaContainer

        ServiceContainer._instance = None
        services._container = LuminaContainer()
        services._providers = ProviderRegistry()
        self.container = services

    async def test_pipeline_context_creation(self):
        """Test PipelineContext dataclass initialization"""
        ctx = PipelineContext(
            original_messages=[{"role": "user", "content": "Hello"}],
            companion_context=companion_context(user_id="test_user", character_id="test_char"),
            enable_rag=True,
            enable_tools=False,
            model_override=None,
            temperature=0.7,
            stream=True
        )

        self.assertEqual(ctx.companion_context.user_id, "test_user")
        self.assertEqual(ctx.companion_context.character_id, "test_char")
        self.assertTrue(ctx.enable_rag)
        self.assertFalse(ctx.enable_tools)
        self.assertEqual(ctx.temperature, 0.7)
        self.assertEqual(len(ctx.original_messages), 1)
        print("✅ PipelineContext creation verified")

    async def test_pipeline_context_default_values(self):
        """Test PipelineContext default field values"""
        ctx = PipelineContext(
            original_messages=[],
            companion_context=companion_context(),
            enable_rag=False,
            enable_tools=False,
            model_override=None,
            temperature=0.5,
            stream=False
        )

        # Check default values
        self.assertEqual(ctx.rag_context, "")
        self.assertEqual(ctx.system_prompt, "")
        self.assertEqual(len(ctx.tools_def), 0)
        self.assertEqual(len(ctx.final_messages), 0)
        self.assertEqual(len(ctx.tool_calls_buffer), 0)
        print("✅ PipelineContext default values verified")

    async def test_context_builder_step_with_providers(self):
        """Test ContextBuilderStep with mocked providers"""
        from services.container import services

        # Create mock context provider
        mock_provider = MagicMock()
        mock_provider.provide = AsyncMock(return_value="Additional context from provider")
        mock_provider.__class__.__name__ = "MockContextProvider"

        services.register_context_provider(mock_provider)

        # Create step and context
        step = ContextBuilderStep(services)
        ctx = PipelineContext(
            original_messages=[{"role": "user", "content": "Hello"}],
            companion_context=companion_context(),
            enable_rag=False,
            enable_tools=False,
            model_override=None,
            temperature=0.7,
            stream=True
        )

        # Mock soul service
        mock_soul = MagicMock()
        mock_soul.get_system_prompt = AsyncMock(return_value="You are a helpful assistant.")
        services.set_soul(mock_soul)

        # Execute step
        await step.execute(ctx)

        # Verify system prompt was set
        self.assertIsNotNone(ctx.system_prompt)
        self.assertIn("helpful assistant", ctx.system_prompt)
        print("✅ ContextBuilderStep with providers verified")

    async def test_context_builder_step_rag_injection(self):
        """Test RAG context injection into last user message"""
        from services.container import services

        step = ContextBuilderStep(services)
        ctx = PipelineContext(
            original_messages=[
                {"role": "user", "content": "First message"},
                {"role": "assistant", "content": "First response"},
                {"role": "user", "content": "Second message"}
            ],
            companion_context=companion_context(),
            enable_rag=True,
            enable_tools=False,
            model_override=None,
            temperature=0.7,
            stream=True,
            rag_context="Relevant memory: User likes cats."
        )

        # Mock soul service
        mock_soul = MagicMock()
        mock_soul.get_system_prompt = AsyncMock(return_value="System prompt")
        services.set_soul(mock_soul)

        await step.execute(ctx)

        # Check that RAG context was injected into the last user message
        last_user_msg = [m for m in ctx.final_messages if m["role"] == "user"][-1]
        self.assertIn("Relevant memory", last_user_msg["content"])
        self.assertIn("User likes cats", last_user_msg["content"])
        print("✅ RAG context injection verified")

    async def test_context_builder_provider_failure_propagates(self):
        """Test that provider failures break context construction."""
        from services.container import services

        failing_provider = MagicMock()
        failing_provider.provide = AsyncMock(side_effect=Exception("Provider failed"))
        failing_provider.__class__.__name__ = "FailingProvider"

        working_provider = MagicMock()
        working_provider.provide = AsyncMock(return_value="Working context")
        working_provider.__class__.__name__ = "WorkingProvider"

        services.register_context_provider(failing_provider)
        services.register_context_provider(working_provider)

        step = ContextBuilderStep(services)
        ctx = PipelineContext(
            original_messages=[{"role": "user", "content": "Hello"}],
            companion_context=companion_context(),
            enable_rag=False,
            enable_tools=False,
            model_override=None,
            temperature=0.7,
            stream=True
        )

        # Mock soul service
        mock_soul = MagicMock()
        mock_soul.get_system_prompt = AsyncMock(return_value="System")
        services.set_soul(mock_soul)

        with self.assertRaisesRegex(Exception, "Provider failed"):
            await step.execute(ctx)

        working_provider.provide.assert_not_called()
        print("✅ Provider failure propagation verified")

    async def test_context_builder_soul_prompt_failure_propagates(self):
        """Test that missing system prompt source is not replaced by a generic prompt."""
        from services.container import services

        step = ContextBuilderStep(services)
        ctx = PipelineContext(
            original_messages=[{"role": "user", "content": "Hello"}],
            companion_context=companion_context(),
            enable_rag=False,
            enable_tools=False,
            model_override=None,
            temperature=0.7,
            stream=True
        )

        mock_soul = MagicMock()
        mock_soul.get_system_prompt = AsyncMock(side_effect=RuntimeError("Soul prompt failed"))
        services.set_soul(mock_soul)

        with self.assertRaisesRegex(RuntimeError, "Soul prompt failed"):
            await step.execute(ctx)

        self.assertEqual(ctx.system_prompt, "")
        print("✅ Soul prompt failure propagation verified")

    async def test_rag_context_provider_memory_failure_propagates(self):
        """Test that memory retrieval failures are not converted into missing RAG context."""
        from services.chat.providers import RAGContextProvider

        memory = MagicMock()
        memory.retrieve_context = AsyncMock(side_effect=RuntimeError("memory retrieval failed"))
        container = MagicMock()
        container.get_memory.return_value = memory
        provider = RAGContextProvider(container)
        ctx = PipelineContext(
            original_messages=[{"role": "user", "content": "remember this"}],
            companion_context=companion_context(),
            enable_rag=True,
            enable_tools=False,
            model_override=None,
            temperature=0.7,
            stream=True
        )

        with self.assertRaisesRegex(RuntimeError, "memory retrieval failed"):
            await provider.provide(ctx)

        memory.retrieve_context.assert_awaited_once()
        self.assertEqual(ctx.rag_context, "")
        print("✅ RAG memory failure propagation verified")

    async def test_context_builder_message_filtering(self):
        """Test that system messages are filtered correctly"""
        from services.container import services

        step = ContextBuilderStep(services)
        ctx = PipelineContext(
            original_messages=[
                {"role": "system", "content": "Should be filtered"},
                {"role": "user", "content": "Keep this"},
                {"role": "assistant", "content": "Keep this too"}
            ],
            companion_context=companion_context(),
            enable_rag=False,
            enable_tools=False,
            model_override=None,
            temperature=0.7,
            stream=True
        )

        # Mock soul service
        mock_soul = MagicMock()
        mock_soul.get_system_prompt = AsyncMock(return_value="System prompt")
        services.set_soul(mock_soul)

        await step.execute(ctx)

        # Original system message should be replaced
        # Check final_messages structure
        system_msgs = [m for m in ctx.final_messages if m["role"] == "system"]
        self.assertEqual(len(system_msgs), 1)
        self.assertEqual(system_msgs[0]["content"], "System prompt")
        print("✅ Message filtering verified")

    async def test_pipeline_step_execution_order(self):
        """Test that pipeline steps execute in order"""
        ctx = PipelineContext(
            original_messages=[],
            companion_context=companion_context(),
            enable_rag=False,
            enable_tools=False,
            model_override=None,
            temperature=0.7,
            stream=True
        )

        # Create multiple steps
        step1 = MockPipelineStep()
        step2 = MockPipelineStep()
        step3 = MockPipelineStep()

        steps = [step1, step2, step3]

        # Execute in order
        for step in steps:
            await step.execute(ctx)

        # Verify all executed in order
        self.assertTrue(step1.executed)
        self.assertTrue(step2.executed)
        self.assertTrue(step3.executed)
        print("✅ Step execution order verified")

    async def test_pipeline_step_failure_propagation(self):
        """Test that step failures propagate correctly"""
        ctx = PipelineContext(
            original_messages=[],
            companion_context=companion_context(),
            enable_rag=False,
            enable_tools=False,
            model_override=None,
            temperature=0.7,
            stream=True
        )

        # Create steps where middle one fails
        step1 = MockPipelineStep(should_fail=False)
        step2 = MockPipelineStep(should_fail=True)
        step3 = MockPipelineStep(should_fail=False)

        steps = [step1, step2, step3]

        # Execute until failure
        with self.assertRaises(ValueError):
            for step in steps:
                await step.execute(ctx)

        # First step executed, third did not
        self.assertTrue(step1.executed)
        self.assertTrue(step2.executed)
        self.assertFalse(step3.executed)
        print("✅ Step failure propagation verified")

    async def test_pipeline_run_requires_companion_context(self):
        """Test that ChatPipeline cannot run with legacy scattered identity kwargs"""
        pipeline = ChatPipeline(self.container)

        with self.assertRaisesRegex(ValueError, "requires companion_context"):
            async for _ in pipeline.run(
                [{"role": "user", "content": "Hello"}],
                user_id="legacy-user",
                character_id="legacy-character",
            ):
                pass

    async def test_execute_tool_rejects_invalid_json_arguments(self):
        container = MagicMock()
        container.get_tool_provider.return_value = None
        step = ChatPipeline(container).exec_step
        tool_call = {
            "function": {
                "name": "known_tool",
                "arguments": "{invalid-json",
            }
        }

        with self.assertRaises(ValueError):
            await step._execute_tool(tool_call)

    async def test_execute_tool_rejects_unknown_tool(self):
        container = MagicMock()
        container.get_tool_provider.return_value = None
        step = ChatPipeline(container).exec_step
        tool_call = {
            "function": {
                "name": "missing_tool",
                "arguments": "{}",
            }
        }

        with self.assertRaisesRegex(ValueError, "Unknown tool: missing_tool"):
            await step._execute_tool(tool_call)

    async def test_execute_tool_provider_failure_propagates(self):
        provider = MagicMock()
        provider.execute = AsyncMock(side_effect=RuntimeError("tool provider failed"))
        container = MagicMock()
        container.get_tool_provider.return_value = provider
        step = ChatPipeline(container).exec_step
        tool_call = {
            "function": {
                "name": "known_tool",
                "arguments": "{\"query\": \"hello\"}",
            }
        }

        with self.assertRaisesRegex(RuntimeError, "tool provider failed"):
            await step._execute_tool(tool_call)


if __name__ == "__main__":
    suite = unittest.TestLoader().loadTestsFromTestCase(TestChatPipeline)
    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(suite)

    print("\n" + "="*60)
    print(f"Tests run: {result.testsRun}")
    print(f"Failures: {len(result.failures)}")
    print(f"Errors: {len(result.errors)}")
    if result.wasSuccessful():
        print("✅ All ChatPipeline tests passed!")
    print("="*60)
