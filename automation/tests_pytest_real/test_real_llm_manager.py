import pytest

from config.loader import ConfigBundle
from config.models import LLMConfig, LLMFeatureRoute, LLMProviderConfig
from core.interfaces.driver import BaseLLMDriver
from llm.manager import LLMManager


class FakeLLMDriver(BaseLLMDriver):
    def __init__(self, provider_id: str):
        super().__init__(provider_id, f"Fake {provider_id}", "Fake LLM driver")
        self.calls = []
        self.client = None

    async def load(self):
        return None

    async def chat_completion(
        self,
        messages: list,
        model: str,
        temperature: float = 0.7,
        stream: bool = False,
        **kwargs,
    ):
        self.calls.append(
            {
                "messages": messages,
                "model": model,
                "temperature": temperature,
                "stream": stream,
                **kwargs,
            }
        )
        if stream:
            async def chunks():
                for chunk in ["hello", " ", "world"]:
                    yield chunk

            return chunks()
        return f"{model}:{messages[-1]['content']}"

    async def list_models(self) -> list:
        return list(self.config.get("models", []))


class ConfigStub:
    def __init__(self, llm: LLMConfig | None = None):
        self.llm = llm or ConfigBundle().llm
        self.saved = 0

    def save(self):
        self.saved += 1


@pytest.fixture
def llm_manager():
    manager = LLMManager(ConfigStub())
    manager.register_driver_type(
        "pollinations",
        lambda provider_id: FakeLLMDriver(provider_id),
        {"display_name": "Fake Pollinations"},
    )
    manager.register_driver_type(
        "fake",
        lambda provider_id: FakeLLMDriver(provider_id),
        {"display_name": "Fake Provider"},
    )
    return manager


def test_llm_manager_requires_explicit_app_settings():
    with pytest.raises(ValueError, match="requires app settings"):
        LLMManager(None)


def test_llm_manager_creates_default_routes(llm_manager: LLMManager):
    assert set(["chat", "memory", "dreaming", "evolution", "proactive", "vision"]).issubset(
        llm_manager.config.routes
    )
    assert llm_manager.get_model_name("chat") == "gpt-4o-mini"
    assert llm_manager.get_model_name("vision") == "gpt-4o"


def test_driver_type_registration_controls_provider_loading(llm_manager: LLMManager):
    driver_types = llm_manager.list_driver_types()

    assert {"type": "fake", "display_name": "Fake Provider"} in driver_types
    assert {"type": "pollinations", "display_name": "Fake Pollinations"} in driver_types


def test_llm_manager_does_not_backfill_missing_routes():
    settings = ConfigStub(
        LLMConfig(
            providers={
                "free_tier": LLMProviderConfig(
                    id="free_tier",
                    type="pollinations",
                    api_key="none",
                    models=["gpt-4o-mini"],
                    enabled=True,
                )
            },
            routes={
                "chat": LLMFeatureRoute(
                    feature="chat",
                    provider_id="free_tier",
                    model="gpt-4o-mini",
                )
            },
        )
    )

    manager = LLMManager(settings)

    assert set(manager.config.routes) == {"chat"}
    with pytest.raises(KeyError, match="Unknown LLM route"):
        manager.get_model_name("vision")


def test_llm_manager_does_not_resolve_unified_config_env_placeholders(monkeypatch):
    monkeypatch.setenv("OPENAI_API_KEY", "env-secret")
    settings = ConfigStub(
        LLMConfig(
            providers={
                "custom_provider": LLMProviderConfig(
                    id="custom_provider",
                    type="openai",
                    base_url="${OPENAI_BASE_URL}",
                    api_key="${OPENAI_API_KEY}",
                    models=["custom-model"],
                    enabled=True,
                )
            },
            routes={
                "chat": LLMFeatureRoute(
                    feature="chat",
                    provider_id="custom_provider",
                    model="custom-model",
                )
            },
        )
    )

    manager = LLMManager(settings)

    assert manager.config.providers["custom_provider"].api_key == "${OPENAI_API_KEY}"
    assert manager.config.providers["custom_provider"].base_url == "${OPENAI_BASE_URL}"


def test_register_route_requires_explicit_provider(llm_manager: LLMManager):
    with pytest.raises(ValueError, match="provider_id is required"):
        llm_manager.register_route("analysis", default_model="analysis-model")


@pytest.mark.anyio
async def test_get_driver_resolves_route_provider(llm_manager: LLMManager):
    llm_manager.update_provider(
        "analysis_provider",
        {
            "type": "fake",
            "base_url": "https://example.invalid/v1",
            "api_key": "test",
            "models": ["analysis-model"],
        },
    )
    llm_manager.register_route(
        "analysis",
        default_model="analysis-model",
        provider_id="analysis_provider",
    )

    driver = await llm_manager.get_driver("analysis")

    assert isinstance(driver, FakeLLMDriver)
    assert driver.id == "analysis_provider"
    assert driver.config["models"] == ["analysis-model"]


def test_update_provider_rejects_unknown_driver_type(llm_manager: LLMManager):
    with pytest.raises(ValueError, match="Unknown LLM provider type"):
        llm_manager.update_provider("bad_provider", {"type": "missing"})


def test_update_route_is_the_single_model_switching_api(llm_manager: LLMManager):
    llm_manager.update_route("chat", model="gpt-4.1-mini", temperature=0.2)

    assert llm_manager.get_model_name("chat") == "gpt-4.1-mini"
    assert llm_manager.get_parameters("chat")["temperature"] == 0.2


def test_update_route_requires_existing_feature(llm_manager: LLMManager):
    with pytest.raises(KeyError):
        llm_manager.update_route("unknown_feature", model="x")


def test_update_route_requires_existing_provider(llm_manager: LLMManager):
    with pytest.raises(KeyError, match="Unknown LLM provider"):
        llm_manager.update_route("chat", provider_id="missing_provider")


def test_route_lookup_requires_existing_feature(llm_manager: LLMManager):
    with pytest.raises(KeyError, match="Unknown LLM route"):
        llm_manager.get_model_name("unknown_feature")

    with pytest.raises(KeyError, match="Unknown LLM route"):
        llm_manager.get_parameters("unknown_feature")


@pytest.mark.anyio
async def test_get_driver_rejects_inactive_route_provider_without_fallback(llm_manager: LLMManager):
    llm_manager.config.providers["custom_provider"] = LLMProviderConfig(
        id="custom_provider",
        type="missing_driver_type",
        enabled=True,
        models=["custom-model"],
    )
    llm_manager.update_route("chat", provider_id="custom_provider", model="custom-model")

    with pytest.raises(ValueError, match="custom_provider"):
        await llm_manager.get_driver("chat")


@pytest.mark.anyio
async def test_get_driver_rejects_disabled_route_provider(llm_manager: LLMManager):
    llm_manager.update_provider("free_tier", {"enabled": False})

    with pytest.raises(ValueError, match="free_tier"):
        await llm_manager.get_driver("chat")


def test_parameter_calculator_can_override_route_parameters(llm_manager: LLMManager):
    def calculator(base_params, soul_state, feature):
        assert feature == "chat"
        return {**base_params, "temperature": soul_state["temperature"]}

    llm_manager.set_parameter_calculator(calculator)

    assert llm_manager.get_parameters("chat", soul_state={"temperature": 0.95})["temperature"] == 0.95


@pytest.mark.anyio
async def test_driver_chat_completion_uses_route_model(llm_manager: LLMManager):
    driver = await llm_manager.get_driver("chat")
    model = llm_manager.get_model_name("chat")

    response = await driver.chat_completion(
        [{"role": "user", "content": "hello"}],
        model=model,
        temperature=llm_manager.get_parameters("chat")["temperature"],
    )

    assert response == "gpt-4o-mini:hello"
    assert driver.calls[0]["model"] == "gpt-4o-mini"


@pytest.mark.anyio
async def test_driver_streaming_completion(llm_manager: LLMManager):
    driver = await llm_manager.get_driver("chat")
    stream = await driver.chat_completion(
        [{"role": "user", "content": "hello"}],
        model=llm_manager.get_model_name("chat"),
        stream=True,
    )

    chunks = [chunk async for chunk in stream]

    assert "".join(chunks) == "hello world"


def test_list_providers_and_routes_reflect_current_config(llm_manager: LLMManager):
    providers = {provider.id for provider in llm_manager.list_providers()}
    routes = {route.feature for route in llm_manager.list_routes()}

    assert {"free_tier", "custom_provider"}.issubset(providers)
    assert {"chat", "memory", "dreaming", "evolution", "proactive", "vision"}.issubset(routes)
