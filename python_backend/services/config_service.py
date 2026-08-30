from __future__ import annotations

from typing import Any
from urllib.parse import urlparse

from config.models import (
    CUSTOM_LLM_PROVIDER_ID,
    FREE_LLM_PROVIDER_ID,
    LLMFeatureRoute,
    LLMProviderConfig,
    POLLINATIONS_BASE_URL,
    AudioConfig,
)
from schemas.runtime_settings import RuntimeLlmSettings


class ConfigService:
    def __init__(self, config, llm_manager):
        self.config = config
        self.llm_manager = llm_manager

    def get_llm_runtime_settings(self) -> RuntimeLlmSettings:
        config = self.config
        llm_manager = self.llm_manager
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
            thinkingEnabled=route.include_reasoning,
            historyLimit=min(config.memory.history_limit, 5)
            if provider_id == FREE_LLM_PROVIDER_ID
            else config.memory.history_limit,
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
        thinking_enabled: bool | None = None,
        history_limit: int | None = None,
        overflow_strategy: str | None = None,
        provider_id: str | None = None,
    ) -> None:
        llm_manager = self.llm_manager
        config = self.config
        target_provider_id = provider_id or CUSTOM_LLM_PROVIDER_ID
        candidate_llm = config.llm.model_copy(deep=True)
        candidate_memory = config.memory.model_copy(deep=True)
        candidate_capabilities = config.capabilities.model_copy(deep=True)
        if target_provider_id not in candidate_llm.providers:
            raise KeyError(f"Unknown LLM provider: {target_provider_id}")

        normalized_model = (model or "").strip()
        normalized_base_url = (base_url or "").strip().rstrip("/")
        normalized_api_key = (api_key or "").strip()
        if not normalized_model:
            raise ValueError("请选择或填写一个模型。")
        if target_provider_id == CUSTOM_LLM_PROVIDER_ID:
            parsed_url = urlparse(normalized_base_url)
            if parsed_url.scheme not in {"http", "https"} or not parsed_url.hostname:
                raise ValueError("API 地址必须是有效的 HTTP 或 HTTPS 地址。")
            is_local_service = parsed_url.hostname in {"localhost", "127.0.0.1", "::1"}
            if not normalized_api_key and not is_local_service:
                raise ValueError("远程自定义服务需要填写 API 密钥。")
        if target_provider_id == FREE_LLM_PROVIDER_ID:
            if not normalized_api_key:
                raise ValueError("Pollinations 需要填写 API 密钥。")
            history_limit = min(history_limit if history_limit is not None else 5, 5)

        current_provider = candidate_llm.providers[target_provider_id]
        provider_payload = current_provider.model_dump()
        if target_provider_id == CUSTOM_LLM_PROVIDER_ID:
            provider_payload.update({
                "type": "openai",
                "base_url": normalized_base_url,
                "api_key": normalized_api_key,
            })
            provider_payload["models"] = [normalized_model]
        elif target_provider_id == FREE_LLM_PROVIDER_ID:
            provider_payload.update({
                "type": "pollinations",
                "base_url": POLLINATIONS_BASE_URL,
                "api_key": normalized_api_key,
            })
            provider_payload["models"] = [normalized_model]
        candidate_llm.providers[target_provider_id] = LLMProviderConfig(**provider_payload)

        route_payload = candidate_llm.routes["chat"].model_dump()
        route_updates: dict[str, Any] = {"provider_id": target_provider_id}
        route_updates["model"] = normalized_model
        if temperature is not None:
            route_updates["temperature"] = temperature
        if top_p is not None:
            route_updates["top_p"] = top_p
        if presence_penalty is not None:
            route_updates["presence_penalty"] = presence_penalty
        if frequency_penalty is not None:
            route_updates["frequency_penalty"] = frequency_penalty
        if thinking_enabled is not None:
            route_updates["include_reasoning"] = thinking_enabled
        route_payload.update(route_updates)
        candidate_llm.routes["chat"] = LLMFeatureRoute(**route_payload)
        candidate_capabilities.selected_providers["llm"] = target_provider_id

        if history_limit is not None:
            candidate_memory.history_limit = history_limit
        if overflow_strategy is not None:
            candidate_memory.overflow_strategy = overflow_strategy

        config.replace_sections(
            llm=candidate_llm,
            memory=candidate_memory,
            capabilities=candidate_capabilities,
        )
        self._refresh_llm_manager(llm_manager)

    def update_llm_provider(self, provider_id: str, updates: dict[str, Any]) -> None:
        config = self.config
        manager = self.llm_manager
        candidate = config.llm.model_copy(deep=True)
        current = candidate.providers.get(provider_id)
        payload = current.model_dump() if current else {
            "id": provider_id,
            "enabled": True,
        }
        payload.update(updates)
        known_types = {item["type"] for item in manager.list_driver_types()}
        if payload.get("type", "openai") not in known_types:
            raise ValueError(f"Unknown LLM provider type: {payload.get('type')}")
        candidate.providers[provider_id] = LLMProviderConfig(**payload)
        config.replace_sections(llm=candidate)
        self._refresh_llm_manager(manager)

    def update_llm_route(self, feature: str, updates: dict[str, Any]) -> None:
        config = self.config
        manager = self.llm_manager
        candidate_llm = config.llm.model_copy(deep=True)
        if feature not in candidate_llm.routes:
            raise KeyError(feature)
        provider_id = updates.get("provider_id")
        if provider_id is not None and provider_id not in candidate_llm.providers:
            raise KeyError(f"Unknown LLM provider: {provider_id}")
        payload = candidate_llm.routes[feature].model_dump()
        payload.update(updates)
        candidate_llm.routes[feature] = LLMFeatureRoute(**payload)

        if feature == "chat":
            candidate_capabilities = config.capabilities.model_copy(deep=True)
            candidate_capabilities.selected_providers["llm"] = candidate_llm.routes[feature].provider_id
            config.replace_sections(
                llm=candidate_llm,
                capabilities=candidate_capabilities,
            )
        else:
            config.replace_sections(llm=candidate_llm)
        self._refresh_llm_manager(manager)

    def _refresh_llm_manager(self, manager: Any) -> None:
        manager.reload_config(self.config.llm)

    def set_selected_provider(self, capability: str, provider_id: str, *, persist: bool = True):
        self._set_selected_provider(capability, provider_id, persist=persist)

    def clear_selected_provider(self, capability: str, *, persist: bool = True):
        config = self.config
        candidate = config.capabilities.model_copy(deep=True)
        candidate.selected_providers.pop(capability, None)
        self._commit_capabilities(candidate, persist=persist)

    def set_provider_desired_state(self, provider_id: str, enabled: bool, *, persist: bool = True):
        config = self.config
        candidate = config.capabilities.model_copy(deep=True)
        candidate.desired_state[provider_id] = enabled
        self._commit_capabilities(candidate, persist=persist)

    def set_provider_setting(self, provider_id: str, key: str, value: Any):
        config = self.config
        candidate = config.capabilities.model_copy(deep=True)
        candidate.settings.setdefault(provider_id, {})
        candidate.settings[provider_id][key] = value
        self._commit_capabilities(candidate, persist=True)

    def update_audio_runtime(self, **updates: Any) -> AudioConfig:
        config = self.config
        payload = config.audio.model_dump()
        payload.update({key: value for key, value in updates.items() if value is not None})
        candidate = AudioConfig(**payload)
        config.replace_sections(audio=candidate)
        return config.audio

    def _set_selected_provider(self, capability: str, provider_id: str, *, persist: bool):
        if not provider_id:
            raise ValueError("Selected provider id is required")
        config = self.config
        candidate = config.capabilities.model_copy(deep=True)
        candidate.selected_providers[capability] = provider_id
        candidate.desired_state.setdefault(provider_id, True)
        self._commit_capabilities(candidate, persist=persist)

    def _commit_capabilities(self, candidate, *, persist: bool) -> None:
        self.config.replace_sections(capabilities=candidate, persist=persist)
