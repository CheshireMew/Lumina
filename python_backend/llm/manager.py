import logging
import json
import os
from pathlib import Path
from typing import Dict, Any, Optional, List
from pydantic import BaseModel, Field

# Use Config from app_config for singleton nature (or load independently)
# To avoid circular imports, we might prefer loading config here or relying on app_config injection
# But LLMManager config is separate (llm_registry.json) usually.

from core.interfaces.driver import BaseLLMDriver
# Concrete drivers loaded dynamically

from openai import AsyncOpenAI

logger = logging.getLogger("LLMManager")

# --- Configuration Models ---
class ProviderConfig(BaseModel):
    id: str
    type: str = "openai" # openai, deepseek, pollinations
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
        from app_config import ConfigManager
        self.config_path = ConfigManager().config_root / "llm_registry.json"
            
        self.config: LLMConfig = self.load_config()
        self.drivers: Dict[str, BaseLLMDriver] = {}
        self._parameter_calculator = None
        
        self._initialize_drivers()
        self._ensure_routes_exist()

    def _resolve_env_vars(self, config: LLMConfig) -> LLMConfig:
        """Expand ${VAR} in api_keys"""
        # We modify provider configs in-place or create new
        # Doing simple string replace on relevant fields
        for pid, provider in config.providers.items():
             if provider.api_key and provider.api_key.startswith("${") and provider.api_key.endswith("}"):
                  var_name = provider.api_key[2:-1]
                  env_val = os.getenv(var_name)
                  if env_val:
                       provider.api_key = env_val
                  else:
                       logger.warning(f"Creating provider {pid}: Env var {var_name} not found.")
                       
             if provider.base_url and provider.base_url.startswith("${") and provider.base_url.endswith("}"):
                  var_name = provider.base_url[2:-1]
                  env_val = os.getenv(var_name)
                  if env_val:
                       provider.base_url = env_val
                       
        return config

    def load_config(self) -> LLMConfig:
        if self.config_path.exists():
            try:
                with open(self.config_path, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    conf = LLMConfig(**data)
                    return self._resolve_env_vars(conf)
            except Exception as e:
                logger.error(f"Failed to load LLM config: {e}")
                return self._create_default_config()
        else:
            return self._create_default_config()

    def save_config(self, config: Optional[LLMConfig] = None):
        if config:
            self.config = config
        
        try:
            self.config_path.parent.mkdir(parents=True, exist_ok=True)
            with open(self.config_path, "w", encoding="utf-8") as f:
                json.dump(self.config.model_dump(), f, indent=4, ensure_ascii=False)
        except Exception as e:
            logger.error(f"Failed to save LLM config: {e}")

    def _create_default_config(self) -> LLMConfig:
        host = os.getenv("HOST", "127.0.0.1")
        port = os.getenv("PORT", "8000")
        
        providers = {
            "free_tier": ProviderConfig(
                id="free_tier",
                type="pollinations", # Use native driver now
                base_url="", # Pollinations generic handling
                api_key="none",
                models=["gpt-4o-mini", "claude-3-haiku"]
            ),
            "custom_provider": ProviderConfig(
                id="custom_provider",
                type="openai",
                base_url="https://api.openai.com/v1",
                api_key="",
                enabled=True
            )
        }
        
        routes = {
            "chat": FeatureRoute(feature="chat", provider_id="free_tier", model="gpt-4o-mini"),
            "memory": FeatureRoute(feature="memory", provider_id="free_tier", model="gpt-4o-mini"),
            "dreaming": FeatureRoute(feature="dreaming", provider_id="free_tier", model="gpt-4o-mini"),
            "evolution": FeatureRoute(feature="evolution", provider_id="free_tier", model="gpt-4o-mini"),
            "proactive": FeatureRoute(feature="proactive", provider_id="free_tier", model="gpt-4o-mini")
        }
        
        conf = LLMConfig(providers=providers, routes=routes)
        self.save_config(conf)
        return conf

    def _initialize_drivers(self):
        """Instantiate drivers from config using dynamic discovery"""
        self.drivers.clear()
        
        # 1. Discover available driver classes via PluginLoader
        from services.plugin_loader import PluginLoader
        
        # Construct path: python_backend/plugins/drivers/llm
        # We are in python_backend/llm/manager.py
        base_dir = os.path.dirname(os.path.abspath(__file__))
        drivers_dir = os.path.join(base_dir, "..", "plugins", "drivers", "llm")
        
        # Load prototypes to get the mapping of type -> class
        # PluginLoader returns instances, we use them to get the class and default ID
        prototypes = PluginLoader.load_plugins(drivers_dir, BaseLLMDriver)
        
        driver_classes = {}
        for proto in prototypes:
            # key: default ID (e.g. "openai", "deepseek", "pollinations") -> value: Class
            driver_classes[proto.id] = proto.__class__
            logger.info(f"Discovered LLM Driver Type: {proto.id}")

        # 2. Instantiate providers based on Config
        for p_id, p_conf in self.config.providers.items():
            if not p_conf.enabled and p_id != "free_tier": 
                continue
                
            driver_class = driver_classes.get(p_conf.type)
            
            if driver_class:
                try:
                    # Instantiate specific driver for this provider
                    # We pass the provider ID as the driver ID so they match
                    driver = driver_class(id=p_id)
                    driver.load_config(p_conf.model_dump())
                    self.drivers[p_id] = driver
                    logger.info(f"Loaded Driver: {p_id} [Type: {p_conf.type}]")
                except Exception as e:
                    logger.error(f"Failed to instantiate LLM driver {p_id}: {e}")
            else:
                logger.warning(f"Unknown driver type '{p_conf.type}' for provider '{p_id}'. Available: {list(driver_classes.keys())}")

    def _ensure_routes_exist(self):
        defaults = ["chat", "memory", "dreaming", "evolution", "proactive"]
        changed = False
        fallback = list(self.config.providers.keys())[0] if self.config.providers else "free_tier"
        
        for feat in defaults:
            if feat not in self.config.routes:
                self.config.routes[feat] = FeatureRoute(
                    feature=feat, provider_id=fallback, model="gpt-4o-mini"
                )
                changed = True
        
        if changed: self.save_config()

    # --- Public API ---

    async def get_driver(self, feature: str = "chat") -> BaseLLMDriver:
        """Get high-level Driver for a feature"""
        provider_id = self._resolve_provider_id(feature)
        
        if provider_id not in self.drivers:
             # Try refreshing?
             self._initialize_drivers()
             
        if provider_id not in self.drivers:
             # Fallback
             fallback_id = list(self.drivers.keys())[0] if self.drivers else None
             if fallback_id:
                 logger.warning(f"Driver {provider_id} not active, fallback to {fallback_id}")
                 return self.drivers[fallback_id]
             raise ValueError("No LLM Drivers available.")
             
        return self.drivers[provider_id]

    def get_client(self, feature: str = "chat") -> Any:
        """
        Get raw client (AsyncOpenAI) for legacy/advanced usage.
        Blocking (Sync) method to maintain compat with existing code.
        """
        provider_id = self._resolve_provider_id(feature)
        driver = self.drivers.get(provider_id)
        
        # Fallback
        if not driver and self.drivers:
            driver = list(self.drivers.values())[0]
            
        if driver and hasattr(driver, 'client'):
             # Lazy Load check (Synchronously hacky or assume loaded)
             # OpenAIDriver load is async. 
             # But if we access .client and it's None, we have a problem in sync context.
             # Ideally drivers are loaded on startup.
             
             if driver.client is None:
                 # Emergency sync init
                 logger.warning(f"Lazy-loading client synchronously for {driver.id}")
                 driver.client = AsyncOpenAI(
                    base_url=driver.config.get("base_url"),
                    api_key=driver.config.get("api_key"),
                    timeout=60.0,
                    max_retries=2
                 )
             return driver.client
             
        # Emergency Fallback
        logger.error(f"Could not resolve client for {feature}, returning dumb client")
        return AsyncOpenAI(base_url="http://localhost:8000/free-llm/v1", api_key="none")

    def get_model_name(self, feature: str) -> str:
        route = self.config.routes.get(feature)
        if route: return route.model
        return "gpt-4o-mini" 
    
    def get_parameters(self, feature: str = "chat", soul_state: Optional[Dict] = None) -> Dict:
        """Get generation parameters (temperature, etc)"""
        route = self.config.routes.get(feature)
        
        base_params = {
            "temperature": route.temperature if route else 0.7,
            "top_p": route.top_p if route else 1.0,
            "presence_penalty": route.presence_penalty if route else 0.0,
            "frequency_penalty": route.frequency_penalty if route else 0.0
        }
        
        if self._parameter_calculator and soul_state:
             try:
                 return self._parameter_calculator(base_params, soul_state, feature=feature)
             except Exception:
                 pass
                 
        return base_params

    def _resolve_provider_id(self, feature: str) -> str:
        route = self.config.routes.get(feature)
        if route: return route.provider_id
        return "free_tier"

    def set_parameter_calculator(self, func):
        self._parameter_calculator = func
        
    def list_providers(self) -> List[ProviderConfig]:
        return list(self.config.providers.values())

    def get_route(self, feature: str) -> Optional[FeatureRoute]:
        """
        Get the route configuration for a specific feature.
        Returns None if the feature is not configured.
        """
        return self.config.routes.get(feature)
        
    def list_routes(self) -> List[FeatureRoute]:
        return list(self.config.routes.values())
    
    def update_provider(self, provider_id: str, updates: Dict[str, Any]):
        if provider_id not in self.config.providers:
            # Create new if needed? Or error
            if "type" in updates: # Assumption: creating new
                 pass
            else:
                 raise KeyError(f"Provider {provider_id} not found")
        
        if provider_id in self.config.providers:
            provider = self.config.providers[provider_id]
            # Update fields
            d = provider.model_dump()
            d.update(updates)
            # Retain non-update fields that might be missing in 'updates'
            # (Strictly speaking Pydantic copy is safer)
            self.config.providers[provider_id] = ProviderConfig(**d)
        else:
            # New
            updates["id"] = provider_id
            self.config.providers[provider_id] = ProviderConfig(**updates)
            
        self.save_config()
        self._initialize_drivers() # Reload drivers

    def update_route(self, feature: str, **kwargs):
        if feature not in self.config.routes:
             raise KeyError(feature)
        
        route = self.config.routes[feature]
        d = route.model_dump()
        d.update(kwargs)
        self.config.routes[feature] = FeatureRoute(**d)
        self.save_config()

    def register_route(self, feature: str, default_model: str = "gpt-4o-mini"):
        """
        Register a new route dynamically (e.g. from a plugin).
        """
        if feature not in self.config.routes:
            provider_id = list(self.config.providers.keys())[0] if self.config.providers else "free_tier"
            logger.info(f"🆕 Registering new LLM Route: {feature}")
            self.config.routes[feature] = FeatureRoute(
                feature=feature, 
                provider_id=provider_id, 
                model=default_model,
                temperature=0.7,
                top_p=1.0,
                presence_penalty=0.0,
                frequency_penalty=0.0
            )
            self.save_config()

# Global Singleton Removed
# llm_manager = LLMManager()
