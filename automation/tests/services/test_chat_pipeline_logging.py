import logging

import pytest

from services.chat.pipeline import LLMExecutionStep, PipelineContext


class StreamingDriverStub:
    async def chat_completion(self, *_args, **_kwargs):
        async def chunks():
            yield {"reasoning": "private reasoning", "content": "private response"}

        return chunks()


@pytest.mark.anyio
async def test_normal_chat_logs_only_metadata(monkeypatch, caplog):
    monkeypatch.delenv("LUMINA_DIAGNOSTIC_MODEL_CONTENT", raising=False)
    context = PipelineContext(
        context_pack=None,
        companion_context=None,
        enable_tools=False,
        model_override=None,
        parameter_overrides={"temperature": 0.7},
        stream=True,
        llm_driver=StreamingDriverStub(),
        target_model="test-model",
        final_messages=[{"role": "user", "content": "private prompt"}],
    )

    caplog.set_level(logging.INFO, logger="ChatPipeline")
    output = [chunk async for chunk in LLMExecutionStep(None).run_stream(context)]

    assert output == [{"content": "private response", "reasoning": ""}]
    assert "private prompt" not in caplog.text
    assert "private response" not in caplog.text
    assert "private reasoning" not in caplog.text
    assert "input_chars=14" in caplog.text
    assert "output_chars=16" in caplog.text
    assert "reasoning_chars=17" in caplog.text
