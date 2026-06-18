from __future__ import annotations

import logging
from typing import Any, Callable, Dict, List, Optional

from config.models import (
    LLMConfig,
    LLMFeatureRoute as FeatureRoute,
    LLMProviderConfig as ProviderConfig,
)
from core.interfaces.driver import BaseLLMDriver

logger = logging.getLogger("LLMManager")


class LLMManager:
    def __init__(self, app_settings):
        if app_settings is None:
            raise ValueError("LLMManager requires app settings")

        self.app_settings = app_settings
        self.config: LLMConfig = app_settings.llm
        self.drivers: Dict[str, BaseLLMDriver] = {}
        self._driver_factories: Dict[str, Callable[[str], BaseLLMDriver]] = {}
        self._driver_descriptors: Dict[str, Dict[str, Any]] = {}
        self._drivers_loaded = False
        self._parameter_calculator = None
        self._register_builtin_driver_types()

    def _register_builtin_driver_types(self):
        from llm.drivers.deepseek_driver import DeepSeekDriver
        from llm.drivers.gemini_driver import GeminiDriver
        from llm.drivers.openai_driver import OpenAIDriver
        from llm.drivers.pollinations_driver import PollinationsDriver

        builtin_drivers = {
            "openai": (
                lambda provider_id: OpenAIDriver(id=provider_id),
                {
                    "display_name": "OpenAI Compatible",
                    "description": "OpenAI and OpenAI-compatible chat completion APIs.",
                },
            ),
            "deepseek": (
                lambda provider_id: DeepSeekDriver(id=provider_id),
                {
                    "display_name": "DeepSeek",
                    "description": "DeepSeek API using the OpenAI-compatible protocol.",
                },
            ),
            "gemini": (
                lambda provider_id: GeminiDriver(id=provider_id),
                {
                    "display_name": "Gemini",
                    "description": "Google Gemini through the OpenAI-compatible endpoint.",
                },
            ),
            "pollinations": (
                lambda provider_id: PollinationsDriver(id=provider_id),
                {
                    "display_name": "Pollinations",
                    "description": "Pollinations free chat completion provider.",
                },
            ),
        }
        for type_id, (factory, metadata) in builtin_drivers.items():
            self.register_driver_type(type_id, factory, metadata)

    def save_config(self):
        self.app_settings.save()

    def register_driver_type(
        self,
        type_id: str,
        factory: Callable[[str], BaseLLMDriver],
        metadata: Optional[Dict[str, Any]] = None,
    ):
        self._driver_factories[type_id] = factory
        self._driver_descriptors[type_id] = dict(metadata or {})
        self._drivers_loaded = False
        logger.info("Registered LLM driver type: %s", type_id)

    def unregister_driver_type(self, type_id: str):
        self._driver_factories.pop(type_id, None)
        self._driver_descriptors.pop(type_id, None)
        self._drivers_loaded = False
        logger.info("Unregistered LLM driver type: %s", type_id)

    def list_driver_types(self) -> List[Dict[str, Any]]:
        return [
            {"type": type_id, **descriptor}
            for type_id, descriptor in sorted(self._driver_descriptors.items())
        ]

    def _initialize_drivers(self):
        self.drivers.clear()
        if not self._driver_factories:
            logger.warning("No LLM driver types are registered.")
            self._drivers_loaded = True
            return

        for provider_id, provider in self.config.providers.items():
            if not provider.enabled:
                continue

            factory = self._driver_factories.get(provider.type)
            if not factory:
                logger.warning(
                    "Unknown LLM provider type '%s' for '%s'. Available: %s",
                    provider.type,
                    provider_id,
                    sorted(self._driver_factories),
                )
                continue

            try:
                driver = factory(provider_id)
                if not isinstance(driver, BaseLLMDriver):
                    raise TypeError(f"{provider.type} factory did not return BaseLLMDriver")
                driver.load_config(provider.model_dump())
                self.drivers[provider_id] = driver
                logger.info("Loaded LLM provider instance %s [%s]", provider_id, provider.type)
            except Exception as exc:
                logger.error("Failed to instantiate LLM provider %s: %s", provider_id, exc)

        self._drivers_loaded = True

    def _ensure_drivers_initialized(self):
        if self._drivers_loaded:
            return
        self._initialize_drivers()

    def _require_route(self, feature: str) -> FeatureRoute:
        route = self.config.routes.get(feature)
        if route is None:
            raise KeyError(f"Unknown LLM route: {feature}")
        return route

    def _require_provider_config(self, provider_id: str) -> ProviderConfig:
        provider = self.config.providers.get(provider_id)
        if provider is None:
            raise KeyError(f"Unknown LLM provider: {provider_id}")
        return provider

    def _require_active_driver(self, feature: str) -> BaseLLMDriver:
        self._ensure_drivers_initialized()
        provider_id = self._resolve_provider_id(feature)
        self._require_provider_config(provider_id)

        driver = self.drivers.get(provider_id)
        if driver is None:
            self._initialize_drivers()
            driver = self.drivers.get(provider_id)

        if driver is None:
            raise ValueError(f"LLM provider '{provider_id}' is not active for route '{feature}'.")

        return driver

    async def get_driver(self, feature: str = "chat") -> BaseLLMDriver:
        return self._require_active_driver(feature)

    def get_client(self, feature: str = "chat") -> Any:
        provider_id = self._resolve_provider_id(feature)
        driver = self._require_active_driver(feature)

        if driver and getattr(driver, "client", None) is not None:
            return driver.client

        if driver and driver.config.get("base_url"):
            try:
                from openai import AsyncOpenAI
            except ModuleNotFoundError as exc:
                raise RuntimeError(
                    "The openai package is required to create an OpenAI-compatible client."
                ) from exc

            return AsyncOpenAI(
                base_url=driver.config.get("base_url"),
                api_key=driver.config.get("api_key"),
                timeout=60.0,
                max_retries=2,
            )

        if driver:
            raise ValueError(
                f"LLM provider '{provider_id}' does not expose an OpenAI-compatible client."
            )

        raise ValueError(f"Could not resolve LLM client for route '{feature}'.")

    def get_model_name(self, feature: str) -> str:
        return self._require_route(feature).model

    def get_parameters(self, feature: str = "chat", soul_state: Optional[Dict] = None) -> Dict:
        route = self._require_route(feature)
        base_params = {
            "temperature": route.temperature,
            "top_p": route.top_p,
            "presence_penalty": route.presence_penalty,
            "frequency_penalty": route.frequency_penalty,
        }

        if self._parameter_calculator and soul_state:
            try:
                return self._parameter_calculator(base_params, soul_state, feature=feature)
            except Exception:
                pass

        return base_params

    def _resolve_provider_id(self, feature: str) -> str:
        return self._require_route(feature).provider_id

    def set_parameter_calculator(self, func):
        self._parameter_calculator = func

    def list_providers(self) -> List[ProviderConfig]:
        return list(self.config.providers.values())

    def get_route(self, feature: str) -> Optional[FeatureRoute]:
        return self.config.routes.get(feature)

    def list_routes(self) -> List[FeatureRoute]:
        return list(self.config.routes.values())

    def update_provider(self, provider_id: str, updates: Dict[str, Any]):
        current = self.config.providers.get(provider_id)
        merged = (current.model_dump() if current else {"id": provider_id, "enabled": True})
        merged.update(updates)

        provider_type = merged.get("type", "openai")
        if provider_type not in self._driver_factories:
            raise ValueError(f"Unknown LLM provider type: {provider_type}")

        self.config.providers[provider_id] = ProviderConfig(**merged)
        self.save_config()
        self._drivers_loaded = False

    def update_route(self, feature: str, **kwargs):
        if feature not in self.config.routes:
            raise KeyError(feature)

        provider_id = kwargs.get("provider_id")
        if provider_id is not None:
            self._require_provider_config(provider_id)

        route = self.config.routes[feature]
        payload = route.model_dump()
        payload.update(kwargs)
        self.config.routes[feature] = FeatureRoute(**payload)
        self.save_config()

    def register_route(
        self,
        feature: str,
        default_model: str,
        provider_id: Optional[str] = None,
    ):
        if feature in self.config.routes:
            return

        if not provider_id:
            raise ValueError("provider_id is required when registering an LLM route.")

        self._require_provider_config(provider_id)
        logger.info("Registering new LLM route: %s", feature)
        self.config.routes[feature] = FeatureRoute(
            feature=feature,
            provider_id=provider_id,
            model=default_model,
            temperature=0.7,
            top_p=1.0,
            presence_penalty=0.0,
            frequency_penalty=0.0,
        )
        self.save_config()
