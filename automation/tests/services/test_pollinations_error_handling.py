from unittest.mock import AsyncMock

import httpx
import pytest


@pytest.mark.anyio
async def test_streaming_http_error_reads_body_before_formatting(monkeypatch):
    from llm.drivers import pollinations_driver as module

    async def handler(_request: httpx.Request) -> httpx.Response:
        return httpx.Response(503, json={"error": "provider unavailable"})

    async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as client:
        monkeypatch.setattr(module, "get_http_client", AsyncMock(return_value=client))
        driver = module.PollinationsDriver()
        driver.load_config({"api_key": "test-key"})
        stream = await driver.chat_completion(
            [{"role": "user", "content": "hello"}],
            model="openai",
            stream=True,
        )

        with pytest.raises(RuntimeError) as exc_info:
            async for _ in stream:
                pass

    message = str(exc_info.value)
    assert "Pollinations Error 503" in message
    assert "provider unavailable" in message
    assert "without having called `read()`" not in message


def test_chat_error_classifier_keeps_provider_details_out_of_user_message():
    from services.chat.event_adapter import classify_chat_error

    code, message = classify_chat_error(
        RuntimeError("Pollinations Error 401: secret provider response"),
    )

    assert code == "provider_authentication_failed"
    assert message == "模型服务拒绝了当前凭据，请检查模型设置。"
    assert "secret" not in message


@pytest.mark.anyio
async def test_pollinations_generation_requires_api_key():
    from llm.drivers.pollinations_driver import PollinationsDriver

    driver = PollinationsDriver()

    with pytest.raises(RuntimeError, match="API key is required"):
        await driver.chat_completion(
            [{"role": "user", "content": "hello"}],
            model="openai",
        )


def test_chat_error_classifier_handles_pollinations_payment_required():
    from services.chat.event_adapter import classify_chat_error

    code, message = classify_chat_error(RuntimeError("Pollinations Error 402: internal detail"))

    assert code == "provider_payment_required"
    assert message == "Pollinations 账户额度不足，请检查账户或更换模型服务。"
    assert "internal detail" not in message
