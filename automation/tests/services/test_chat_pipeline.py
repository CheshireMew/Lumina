import sys
import unittest
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock

PROJECT_ROOT = Path(__file__).parents[3]
sys.path.append(str(PROJECT_ROOT / "python_backend"))
sys.path.append(str(PROJECT_ROOT))

from services.chat.pipeline import ChatPipeline, ContextBuilderStep, PipelineContext, PipelineStep
from services.companion.context import CompanionContext
from services.companion.context_pack import CompanionContextPack


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


def context_pack(**kwargs) -> CompanionContextPack:
    return CompanionContextPack(
        identity=kwargs.get("identity") or companion_context(),
        user_message=kwargs.get("user_message", "Hello"),
        recent_session_history=kwargs.get("recent_session_history", []),
        relevant_memories=kwargs.get("relevant_memories", ""),
        stable_profile_facts=kwargs.get("stable_profile_facts", ""),
        current_soul_state=kwargs.get("current_soul_state", {}),
        runtime_capabilities=kwargs.get("runtime_capabilities", {}),
        current_time=kwargs.get("current_time", ""),
        system_prompt=kwargs.get("system_prompt", "System prompt"),
    )


class MockPipelineStep(PipelineStep):
    def __init__(self, should_fail=False):
        self.should_fail = should_fail
        self.executed = False

    async def execute(self, ctx: PipelineContext):
        self.executed = True
        if self.should_fail:
            raise ValueError("Mock step failure")


class TestChatPipeline(unittest.IsolatedAsyncioTestCase):
    def setUp(self):
        from services.container import ServiceContainer
        from services.container import services
        from services.container.provider_registry import ProviderRegistry
        from services.container.service_definitions import LuminaContainer

        ServiceContainer._instance = None
        services._container = LuminaContainer()
        services._providers = ProviderRegistry()
        self.container = services

    async def test_pipeline_context_creation(self):
        pack = context_pack(identity=companion_context(user_id="u1", character_id="hiyori"))
        ctx = PipelineContext(
            context_pack=pack,
            companion_context=pack.identity,
            enable_tools=False,
            model_override=None,
            temperature=0.7,
            stream=True,
        )

        self.assertEqual(ctx.companion_context.user_id, "u1")
        self.assertEqual(ctx.companion_context.character_id, "hiyori")
        self.assertFalse(ctx.enable_tools)
        self.assertEqual(ctx.temperature, 0.7)
        self.assertEqual(ctx.context_pack.user_message, "Hello")

    async def test_context_builder_uses_context_pack_as_single_source(self):
        pack = context_pack(
            recent_session_history=[
                {"role": "user", "content": "Earlier"},
                {"role": "assistant", "content": "Reply"},
            ],
            relevant_memories="User likes quiet mornings.",
            current_soul_state={"active_character_id": "hiyori"},
            current_time="2026-06-18T00:00:00+00:00",
        )
        ctx = PipelineContext(
            context_pack=pack,
            companion_context=pack.identity,
            enable_tools=False,
            model_override=None,
            temperature=0.7,
            stream=True,
        )

        await ContextBuilderStep(self.container).execute(ctx)

        self.assertEqual(ctx.final_messages[0]["role"], "system")
        self.assertIn("System prompt", ctx.final_messages[0]["content"])
        self.assertIn("Relevant Memories", ctx.final_messages[0]["content"])
        self.assertEqual(ctx.final_messages[-1], {"role": "user", "content": "Hello"})
        self.assertEqual(ctx.final_messages[1]["content"], "Earlier")

    async def test_context_builder_filters_system_history(self):
        pack = context_pack(
            recent_session_history=[
                {"role": "system", "content": "old system"},
                {"role": "user", "content": "keep"},
            ],
        )
        ctx = PipelineContext(
            context_pack=pack,
            companion_context=pack.identity,
            enable_tools=False,
            model_override=None,
            temperature=0.7,
            stream=True,
        )

        await ContextBuilderStep(self.container).execute(ctx)

        system_messages = [m for m in ctx.final_messages if m["role"] == "system"]
        self.assertEqual(len(system_messages), 1)
        self.assertNotIn("old system", system_messages[0]["content"])

    async def test_pipeline_step_failure_propagation(self):
        pack = context_pack()
        ctx = PipelineContext(
            context_pack=pack,
            companion_context=pack.identity,
            enable_tools=False,
            model_override=None,
            temperature=0.7,
            stream=True,
        )
        step1 = MockPipelineStep()
        step2 = MockPipelineStep(should_fail=True)
        step3 = MockPipelineStep()

        with self.assertRaises(ValueError):
            for step in [step1, step2, step3]:
                await step.execute(ctx)

        self.assertTrue(step1.executed)
        self.assertTrue(step2.executed)
        self.assertFalse(step3.executed)

    async def test_pipeline_run_requires_context_pack(self):
        pipeline = ChatPipeline(self.container)

        with self.assertRaisesRegex(ValueError, "requires context_pack"):
            async for _ in pipeline.run(
                companion_context=companion_context(),
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
    runner.run(suite)
