import sys
from pathlib import Path

import pytest

PROJECT_ROOT = Path(__file__).parents[2]
sys.path.append(str(PROJECT_ROOT / "python_backend"))

from llm.drivers import pollinations_driver
from llm.drivers.pollinations_driver import PollinationsDriver


class FakeResponse:
    def __init__(self, data, status_code=200, text=""):
        self._data = data
        self.status_code = status_code
        self.text = text

    def raise_for_status(self):
        return None

    def json(self):
        return self._data


class FakeHttpClient:
    def __init__(self):
        self.requests = []

    async def get(self, url, **kwargs):
        self.requests.append(("GET", url, kwargs))
        return FakeResponse(
            {
                "data": [
                    {
                        "id": "openai",
                        "supported_endpoints": ["/v1/chat/completions"],
                        "output_modalities": ["text"],
                    },
                    {
                        "id": "image-only",
                        "supported_endpoints": ["/v1/images/generations"],
                        "output_modalities": ["image"],
                    },
                ]
            }
        )

    async def post(self, url, **kwargs):
        self.requests.append(("POST", url, kwargs))
        return FakeResponse(
            {"choices": [{"message": {"content": "OK"}}]}
        )


@pytest.fixture
def fake_client(monkeypatch):
    client = FakeHttpClient()

    async def get_http_client():
        return client

    monkeypatch.setattr(pollinations_driver, "get_http_client", get_http_client)
    return client


@pytest.mark.anyio
async def test_pollinations_chat_supports_anonymous_endpoint(fake_client):
    driver = PollinationsDriver()
    driver.load_config({"base_url": "https://gen.pollinations.ai/v1", "api_key": ""})

    response = await driver.chat_completion(
        [{"role": "user", "content": "hello"}],
        model="openai",
    )

    assert response == "OK"
    method, url, kwargs = fake_client.requests[0]
    assert method == "POST"
    assert url == pollinations_driver.POLLINATIONS_ANONYMOUS_CHAT_URL
    assert "Authorization" not in kwargs["headers"]


@pytest.mark.anyio
async def test_pollinations_chat_uses_official_openai_compatible_endpoint(fake_client):
    driver = PollinationsDriver()
    driver.load_config({"base_url": "https://gen.pollinations.ai/v1", "api_key": "sk_test"})

    response = await driver.chat_completion(
        [{"role": "user", "content": "hello"}],
        model="openai",
        temperature=0.2,
        stream=False,
    )

    assert response == "OK"
    method, url, kwargs = fake_client.requests[0]
    assert method == "POST"
    assert url == "https://gen.pollinations.ai/v1/chat/completions"
    assert kwargs["headers"]["Authorization"] == "Bearer sk_test"
    assert kwargs["json"]["model"] == "openai"
    assert kwargs["json"]["temperature"] == 0.2


@pytest.mark.anyio
async def test_pollinations_models_are_loaded_from_remote_model_index(fake_client):
    driver = PollinationsDriver()
    driver.load_config({"base_url": "https://gen.pollinations.ai/v1", "api_key": "sk_test"})

    models = await driver.list_models()

    assert models == ["openai"]
    method, url, _ = fake_client.requests[0]
    assert method == "GET"
    assert url == "https://gen.pollinations.ai/v1/models"
