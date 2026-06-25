from __future__ import annotations

from typing import Any

from config.models import CUSTOM_LLM_PROVIDER_ID, FREE_LLM_PROVIDER_ID, POLLINATIONS_BASE_URL
from core.services.service_registry import get_service_registry
from schemas.runtime_settings import RuntimeLlmSettings


class ConfigService:
    def __init__(self, container):
        self.container = container

    @property
    def config(self):
        return self.container.get_config()

    def _get_llm_manager(self):
        return self.container.get_llm_manager()

    def get_registered_service(self, name: str) -> Any:
        return get_service_registry().resolve(name, container=self.container)

    def get_llm_runtime_settings(self) -> RuntimeLlmSettings:
        config = self.config
        llm_manager = self._get_llm_manager()
        route = llm_manager.get_route("chat")
        if route is None:
            raise KeyError("Unknown LLM route: chat")
        provider_id = route.provider_id
        provider = llm_manager.config.providers.get(provider_id)
        if provider is None:
            raise KeyError(f"Unknown LLM provider: {provider_id}")

        return RuntimeLlmSettings(
            providerId=provider_id,
            apiKey=provider.api_key or "",
            baseUrl=provider.base_url or "",
            model=route.model or "",
            temperature=route.temperature,
            topP=route.top_p,
            presencePenalty=route.presence_penalty,
            frequencyPenalty=route.frequency_penalty,
            historyLimit=config.memory.history_limit,
            overflowStrategy=config.memory.overflow_strategy,
        )

    def update_llm_runtime(
        self,
        *,
        api_key: str | None,
        base_url: str | None,
        model: str | None,
        temperature: float | None = None,
        top_p: float | None = None,
        presence_penalty: float | None = None,
        frequency_penalty: float | None = None,
        history_limit: int | None = None,
        overflow_strategy: str | None = None,
        provider_id: str | None = None,
    ) -> None:
        dreaming_service = self.get_registered_service("dreaming_service")
        if dreaming_service:
            dreaming_service.update_llm_config(
                api_key=api_key,
                base_url=base_url,
                model=model,
            )

        llm_manager = self._get_llm_manager()
        config = self.config
        target_provider_id = provider_id or CUSTOM_LLM_PROVIDER_ID
        if target_provider_id not in llm_manager.config.providers:
            raise KeyError(f"Unknown LLM provider: {target_provider_id}")

        if target_provider_id == CUSTOM_LLM_PROVIDER_ID:
            provider_updates = {
                "type": "openai",
                "base_url": base_url or "",
                "api_key": api_key or "",
            }
            if model:
                provider_updates["models"] = [model]

            llm_manager.update_provider(CUSTOM_LLM_PROVIDER_ID, provider_updates)
        elif target_provider_id == FREE_LLM_PROVIDER_ID:
            provider_updates = {
                "type": "pollinations",
                "base_url": base_url or POLLINATIONS_BASE_URL,
                "api_key": api_key or "",
            }
            if model:
                provider_updates["models"] = [model]

            llm_manager.update_provider(FREE_LLM_PROVIDER_ID, provider_updates)

        for route in llm_manager.list_routes():
            route_updates = {"provider_id": target_provider_id}
            if model:
                route_updates["model"] = model
            if temperature is not None:
                route_updates["temperature"] = temperature
            if top_p is not None:
                route_updates["top_p"] = top_p
            if presence_penalty is not None:
                route_updates["presence_penalty"] = presence_penalty
            if frequency_penalty is not None:
                route_updates["frequency_penalty"] = frequency_penalty
            llm_manager.update_route(route.feature, **route_updates)

        if history_limit is not None:
            config.memory.history_limit = history_limit
        if overflow_strategy is not None:
            config.memory.overflow_strategy = overflow_strategy
        config.save()

    def set_selected_provider(self, capability: str, provider_id: str, *, persist: bool = True):
        self._set_selected_provider(capability, provider_id, persist=persist)

    def clear_selected_provider(self, capability: str, *, persist: bool = True):
        config = self.config
        config.capabilities.selected_providers.pop(capability, None)
        if persist:
            config.save()

    def set_provider_desired_state(self, provider_id: str, enabled: bool, *, persist: bool = True):
        config = self.config
        config.set_provider_desired_state(provider_id, enabled)
        if persist:
            config.save()

    def set_provider_setting(self, provider_id: str, key: str, value: Any):
        config = self.config
        config.capabilities.settings.setdefault(provider_id, {})
        config.capabilities.settings[provider_id][key] = value
        config.save()

    def _set_selected_provider(self, capability: str, provider_id: str, *, persist: bool):
        config = self.config
        config.set_selected_provider(capability, provider_id)
        if persist:
            config.save()
