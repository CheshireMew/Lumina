from __future__ import annotations

from typing import Any

from core.services.service_registry import get_service_registry
from schemas.runtime_settings import RuntimeLlmSettings


class ConfigService:
    def __init__(self, container):
        self.container = container

    @property
    def config(self):
        return self.container.get_config()

    def _get_llm_manager(self):
        if not self.container.has_service("llm_manager"):
            return None
        return self.container.get_llm_manager()

    def get_registered_service(self, name: str) -> Any:
        return get_service_registry().resolve(name, container=self.container)

    def get_llm_runtime_settings(self) -> RuntimeLlmSettings:
        config = self.config
        llm_manager = self._get_llm_manager()
        route = llm_manager.get_route("chat") if llm_manager else None
        provider_id = route.provider_id if route else config.get_selected_provider("llm")
        provider_type = "free" if provider_id == "free_tier" else "custom"
        provider = (
            llm_manager.config.providers.get(provider_id)
            if llm_manager and provider_type == "custom"
            else None
        )

        return RuntimeLlmSettings(
            providerType=provider_type,
            apiKey=(provider.api_key if provider else config.llm.api_key if provider_type == "custom" else "") or "",
            baseUrl=(provider.base_url if provider else config.llm.base_url if provider_type == "custom" else "") or "",
            model=(route.model if route else config.llm.model) or config.llm.model,
            temperature=route.temperature if route else 0.7,
            topP=route.top_p if route else 1.0,
            presencePenalty=route.presence_penalty if route else 0.0,
            frequencyPenalty=route.frequency_penalty if route else 0.0,
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
        provider_type: str | None = None,
    ) -> None:
        dreaming_service = self.get_registered_service("dreaming_service")
        if dreaming_service:
            dreaming_service.update_llm_config(
                api_key=api_key,
                base_url=base_url,
                model=model,
            )

        llm_manager = self._get_llm_manager()
        if llm_manager:
            target_provider_id = "free_tier" if provider_type == "free" else "custom_provider"
            if target_provider_id == "custom_provider":
                provider_updates = {
                    "type": "openai",
                    "base_url": base_url or "",
                    "api_key": api_key or "",
                }
                if model:
                    provider_updates["models"] = [model]

                llm_manager.update_provider("custom_provider", provider_updates)

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
            self.config.set_selected_provider("llm", target_provider_id)

        config = self.config
        if provider_type != "free" and base_url is not None:
            config.llm.base_url = base_url
        if provider_type != "free" and api_key is not None:
            config.llm.api_key = api_key
        if model is not None:
            config.llm.model = model
        if history_limit is not None:
            config.memory.history_limit = history_limit
        if overflow_strategy is not None:
            config.memory.overflow_strategy = overflow_strategy
        config.save()

    def set_selected_provider(self, capability: str, provider_id: str, *, persist: bool = True):
        self._set_selected_provider(capability, provider_id, persist=persist)

    def clear_selected_provider(self, capability: str, *, persist: bool = True):
        config = self.config
        config.plugins.selected_providers.pop(capability, None)
        if persist:
            config.save()

    def set_plugin_desired_state(self, plugin_id: str, enabled: bool, *, persist: bool = True):
        config = self.config
        config.set_plugin_desired_state(plugin_id, enabled)
        if persist:
            config.save()

    def set_plugin_setting(self, plugin_id: str, key: str, value: Any):
        config = self.config
        config.plugins.settings.setdefault(plugin_id, {})
        config.plugins.settings[plugin_id][key] = value
        config.save()

    def _set_selected_provider(self, capability: str, provider_id: str, *, persist: bool):
        config = self.config
        config.set_selected_provider(capability, provider_id)
        if persist:
            config.save()
