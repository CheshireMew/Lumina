from __future__ import annotations

import json
import logging
import os
from typing import Any, Callable, Dict, List, Optional

from openai import AsyncOpenAI
from pydantic import BaseModel

from core.interfaces.driver import BaseLLMDriver

logger = logging.getLogger("LLMManager")


class ProviderConfig(BaseModel):
    id: str
    type: str = "openai"
    base_url: str = ""
    api_key: str = ""
    models: List[str] = []
    enabled: bool = True


class FeatureRoute(BaseModel):
    feature: str
    provider_id: str
    model: str
    temperature: float = 0.7
    top_p: float = 1.0
    presence_penalty: float = 0.0
    frequency_penalty: float = 0.0


class LLMConfig(BaseModel):
    providers: Dict[str, ProviderConfig] = {}
    routes: Dict[str, FeatureRoute] = {}


class LLMManager:
    def __init__(self):
        from app_config import config

        self.config_path = config.config_root / "llm_registry.json"
        self.config: LLMConfig = self.load_config()
        self.drivers: Dict[str, BaseLLMDriver] = {}
        self._driver_factories: Dict[str, Callable[[str], BaseLLMDriver]] = {}
        self._driver_descriptors: Dict[str, Dict[str, Any]] = {}
        self._drivers_loaded = False
        self._parameter_calculator = None

        self._ensure_routes_exist()

    def _resolve_env_vars(self, config: LLMConfig) -> LLMConfig:
        for provider in config.providers.values():
            if provider.api_key.startswith("${") and provider.api_key.endswith("}"):
                env_val = os.getenv(provider.api_key[2:-1], "")
                if env_val:
                    provider.api_key = env_val
            if provider.base_url.startswith("${") and provider.base_url.endswith("}"):
                env_val = os.getenv(provider.base_url[2:-1], "")
                if env_val:
                    provider.base_url = env_val
        return config

    def load_config(self) -> LLMConfig:
        if not self.config_path.exists():
            return self._create_default_config()

        try:
            with open(self.config_path, "r", encoding="utf-8") as f:
                data = json.load(f)
            return self._resolve_env_vars(LLMConfig(**data))
        except Exception as exc:
            logger.error("Failed to load LLM config: %s", exc)
            return self._create_default_config()

    def save_config(self, config: Optional[LLMConfig] = None):
        if config is not None:
            self.config = config

        try:
            self.config_path.parent.mkdir(parents=True, exist_ok=True)
            with open(self.config_path, "w", encoding="utf-8") as f:
                json.dump(self.config.model_dump(), f, indent=4, ensure_ascii=False)
        except Exception as exc:
            logger.error("Failed to save LLM config: %s", exc)

    def _create_default_config(self) -> LLMConfig:
        conf = LLMConfig(
            providers={
                "free_tier": ProviderConfig(
                    id="free_tier",
                    type="pollinations",
                    base_url="",
                    api_key="none",
                    models=["gpt-4o-mini", "claude-3-haiku"],
                ),
                "custom_provider": ProviderConfig(
                    id="custom_provider",
                    type="openai",
                    base_url="https://api.openai.com/v1",
                    api_key="",
                    models=[],
                    enabled=True,
                ),
            },
            routes={
                "chat": FeatureRoute(feature="chat", provider_id="free_tier", model="gpt-4o-mini"),
                "memory": FeatureRoute(feature="memory", provider_id="free_tier", model="gpt-4o-mini"),
                "dreaming": FeatureRoute(feature="dreaming", provider_id="free_tier", model="gpt-4o-mini"),
                "evolution": FeatureRoute(feature="evolution", provider_id="free_tier", model="gpt-4o-mini"),
                "proactive": FeatureRoute(feature="proactive", provider_id="free_tier", model="gpt-4o-mini"),
            },
        )
        self.save_config(conf)
        return conf

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
            if not provider.enabled and provider_id != "free_tier":
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

    def _ensure_routes_exist(self):
        defaults = ["chat", "memory", "dreaming", "evolution", "proactive"]
        changed = False
        fallback = list(self.config.providers.keys())[0] if self.config.providers else "free_tier"

        for feature in defaults:
            if feature not in self.config.routes:
                self.config.routes[feature] = FeatureRoute(
                    feature=feature,
                    provider_id=fallback,
                    model="gpt-4o-mini",
                )
                changed = True

        if changed:
            self.save_config()

    async def get_driver(self, feature: str = "chat") -> BaseLLMDriver:
        self._ensure_drivers_initialized()
        provider_id = self._resolve_provider_id(feature)

        if provider_id not in self.drivers:
            self._initialize_drivers()

        if provider_id not in self.drivers:
            fallback_id = next(iter(self.drivers), None)
            if fallback_id:
                logger.warning("LLM provider %s not active, falling back to %s", provider_id, fallback_id)
                return self.drivers[fallback_id]
            raise ValueError("No LLM providers available.")

        return self.drivers[provider_id]

    def get_client(self, feature: str = "chat") -> Any:
        self._ensure_drivers_initialized()
        provider_id = self._resolve_provider_id(feature)
        driver = self.drivers.get(provider_id)
        if not driver and self.drivers:
            driver = next(iter(self.drivers.values()))

        if driver and getattr(driver, "client", None) is not None:
            return driver.client

        if driver and driver.config.get("base_url"):
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

        raise ValueError(f"Could not resolve LLM client for {feature}.")

    def get_model_name(self, feature: str) -> str:
        route = self.config.routes.get(feature)
        if route:
            return route.model
        return "gpt-4o-mini"

    def get_parameters(self, feature: str = "chat", soul_state: Optional[Dict] = None) -> Dict:
        route = self.config.routes.get(feature)
        base_params = {
            "temperature": route.temperature if route else 0.7,
            "top_p": route.top_p if route else 1.0,
            "presence_penalty": route.presence_penalty if route else 0.0,
            "frequency_penalty": route.frequency_penalty if route else 0.0,
        }

        if self._parameter_calculator and soul_state:
            try:
                return self._parameter_calculator(base_params, soul_state, feature=feature)
            except Exception:
                pass

        return base_params

    def _resolve_provider_id(self, feature: str) -> str:
        route = self.config.routes.get(feature)
        if route:
            return route.provider_id
        return next(iter(self.config.providers), "free_tier")

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

        route = self.config.routes[feature]
        payload = route.model_dump()
        payload.update(kwargs)
        self.config.routes[feature] = FeatureRoute(**payload)
        self.save_config()

    def register_route(self, feature: str, default_model: str = "gpt-4o-mini"):
        if feature in self.config.routes:
            return

        provider_id = next(iter(self.config.providers), "free_tier")
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
