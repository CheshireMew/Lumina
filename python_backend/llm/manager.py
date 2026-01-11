import json
import logging
import os
from pathlib import Path
from typing import Dict, Any, Optional, List
from pydantic import BaseModel
from openai import AsyncOpenAI

logger = logging.getLogger("LLMManager")

class ProviderConfig(BaseModel):
    id: str
    type: str = "openai" # openai, azure, anthropic, etc. (currently only openai supported)
    base_url: str
    api_key: str
    models: List[str] = []
    
class FeatureRoute(BaseModel):
    feature: str # "chat", "dreaming", "memory"
    provider_id: str
    model: str
    temperature: float = 0.7
    top_p: float = 1.0
    presence_penalty: float = 0.0
    frequency_penalty: float = 0.0

class LLMConfig(BaseModel):
    providers: Dict[str, ProviderConfig]
    routes: Dict[str, FeatureRoute]

class LLMManager:
    _instance = None
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(LLMManager, cls).__new__(cls)
            cls._instance._initialize()
        return cls._instance
    
    def _initialize(self):
        self.config_path = self._resolve_config_path()
        self.clients: Dict[str, AsyncOpenAI] = {} # Cache clients by provider_id
        self.config: LLMConfig = self._load_or_create_config()
        self._ensure_routes_exist()
        
    def _resolve_config_path(self) -> Path:
        # Try finding it in standard locations
        # 1. Env Var
        if os.environ.get("LUMINA_CONFIG_PATH"):
            return Path(os.environ["LUMINA_CONFIG_PATH"]) / "llm_registry.json"
            
        # 2. Parallel to app_config.py (Dev Mode) usually e:\Work\Code\Lumina\python_backend
        base_dir = Path(__file__).parent.parent
        return base_dir / "llm_registry.json"

    def _load_or_create_config(self) -> LLMConfig:
        if self.config_path.exists():
            try:
                with open(self.config_path, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    return LLMConfig(**data)
            except Exception as e:
                logger.error(f"Failed to load LLM config: {e}. Using defaults.")
        
        # Defaults
        defaults = self._get_default_config()
        try:
            self._save_config_file(defaults)
        except Exception as e:
            logger.error(f"Failed to save default config: {e}")
            
        return defaults

    def _get_default_config(self) -> LLMConfig:
        # Detect environment config for migration/init
        from app_config import config as app_config
        
        # 1. Native Free Tier
        free_provider = ProviderConfig(
            id="free_tier",
            base_url=f"{app_config.llm.base_url.split('/v1')[0]}/free-llm/v1" if "free-llm" in app_config.llm.base_url else f"http://{app_config.network.host}:{app_config.network.memory_port}/free-llm/v1",
            api_key="none",
            models=["gpt-4o-mini", "claude-3-haiku", "llama-3-70b", "mixtral-8x7b"]
        )
        
        # 2. Custom/DeepSeek (Migration)
        custom_base = app_config.llm.base_url
        custom_key = app_config.llm.api_key
        
        # Check if current config is actually the free one, if so, define a DeepSeek preset
        if "free-llm" in custom_base:
            custom_base = "https://api.deepseek.com/v1"
            custom_key = "" # User needs to fill
            
        custom_provider = ProviderConfig(
            id="custom_provider",
            base_url=custom_base,
            api_key=custom_key,
            models=["deepseek-chat", "deepseek-coder"]
        )
        
        providers = {
            "free_tier": free_provider,
            "custom_provider": custom_provider
        }
        
        routes = {
            # Default routes
            "chat": FeatureRoute(feature="chat", provider_id="free_tier", model="gpt-4o-mini", temperature=0.7, top_p=1.0, presence_penalty=0.0, frequency_penalty=0.0),
            "proactive": FeatureRoute(feature="proactive", provider_id="free_tier", model="gpt-4o-mini", temperature=0.9, top_p=0.95, presence_penalty=0.5, frequency_penalty=0.5), # Active, less repetitive
            "dreaming": FeatureRoute(feature="dreaming", provider_id="free_tier", model="gpt-4o-mini", temperature=0.8, top_p=1.0), 
            "memory": FeatureRoute(feature="memory", provider_id="free_tier", model="gpt-4o-mini", temperature=0.1, top_p=1.0), 
            "evolution": FeatureRoute(feature="evolution", provider_id="free_tier", model="gpt-4o-mini", temperature=0.7, top_p=1.0) 
        }
        
        return LLMConfig(providers=providers, routes=routes)

    def _ensure_routes_exist(self):
        """Migration helper: Ensure new routes exist in loaded config"""
        defaults = self._get_default_config()
        changed = False
        for key, route in defaults.routes.items():
            if key not in self.config.routes:
                self.config.routes[key] = route
                changed = True
                logger.info(f"[LLMManager] Auto-added missing route: {key}")
        
        if changed:
            self.save_config()

    def _save_config_file(self, config: LLMConfig):
        with open(self.config_path, 'w', encoding='utf-8') as f:
            f.write(config.model_dump_json(indent=2))

    def save_config(self):
        """Public save method"""
        self._save_config_file(self.config)

    def _get_default_config_host(self):
        from app_config import config
        return config.network.host

    def _get_default_config_port(self):
        from app_config import config
        return config.network.memory_port

    def get_client(self, feature: str = "chat") -> AsyncOpenAI:
        """
        Get an OpenAI client configured for the specific feature.
        """
        route = self.config.routes.get(feature, self.config.routes.get("chat"))
        if not route:
            # Fallback very hard
            logger.warning(f"No route for feature '{feature}', using default.")
            # Create a localized temporary fallback if config is completely broken
            return AsyncOpenAI(base_url=f"http://{self._get_default_config_host()}:{self._get_default_config_port()}/free-llm/v1", api_key="none")

        provider_id = route.provider_id
        provider = self.config.providers.get(provider_id)
        
        if not provider:
            logger.error(f"Provider '{provider_id}' not found for feature '{feature}'. Using Free Tier.")
            provider = self.config.providers.get("free_tier") or list(self.config.providers.values())[0]

        if provider.id not in self.clients:
            # Instantiate Client
            logger.info(f"Instantiating new LLM Client for provider: {provider.id}")
            self.clients[provider.id] = AsyncOpenAI(
                base_url=provider.base_url,
                api_key=provider.api_key,
                timeout=60.0,
                max_retries=2
            )
            
        return self.clients[provider.id]

    def get_model_name(self, feature: str = "chat") -> str:
        route = self.config.routes.get(feature, self.config.routes.get("chat"))
        if route:
            return route.model
        return "gpt-4o-mini" # Fallback

    def get_temperature(self, feature: str = "chat") -> float:
        route = self.config.routes.get(feature, self.config.routes.get("chat"))
        if route:
            return route.temperature
        return 0.7 # Fallback

    # --- Management APIs ---
    
    def list_providers(self) -> List[ProviderConfig]:
        return list(self.config.providers.values())
        
    def list_routes(self) -> List[FeatureRoute]:
        return list(self.config.routes.values())
        
    def update_provider(self, provider_id: str, updates: Dict[str, Any]):
        if provider_id not in self.config.providers:
            raise KeyError(f"Provider {provider_id} does not exist")
        
        provider = self.config.providers[provider_id]
        updated_data = provider.model_dump()
        updated_data.update(updates)
        self.config.providers[provider_id] = ProviderConfig(**updated_data)
        
        # Invalidate cache
        if provider_id in self.clients:
            del self.clients[provider_id]
            
        self.save_config()
        
    def update_route(
        self, 
        feature: str, 
        provider_id: str, 
        model: str, 
        temperature: Optional[float] = None,
        top_p: Optional[float] = None,
        presence_penalty: Optional[float] = None,
        frequency_penalty: Optional[float] = None
    ):
        if provider_id not in self.config.providers:
            raise ValueError(f"Unknown provider: {provider_id}")
            
        route = self.config.routes.get(feature)
        if route:
            route.provider_id = provider_id
            route.model = model
            if temperature is not None:
                route.temperature = temperature
            if top_p is not None:
                route.top_p = top_p
            if presence_penalty is not None:
                route.presence_penalty = presence_penalty
            if frequency_penalty is not None:
                route.frequency_penalty = frequency_penalty
        else:
            self.config.routes[feature] = FeatureRoute(
                feature=feature,
                provider_id=provider_id, # Fix: Missing provider_id in new creation
                model=model,
                temperature=temperature or 0.7,
                top_p=top_p or 1.0,
                presence_penalty=presence_penalty or 0.0,
                frequency_penalty=frequency_penalty or 0.0
            )
        self.save_config()

    def get_parameters(self, feature: str = "chat", soul_state: Optional[Dict[str, Any]] = None) -> Dict[str, float]:
        """Get all generation parameters for a feature, optionally adjusted by soul state"""
        route = self.config.routes.get(feature, self.config.routes.get("chat"))
        if not route:
            return {"temperature": 0.7}
            
        base_params = {
            "temperature": route.temperature,
            "top_p": route.top_p,
            "presence_penalty": route.presence_penalty,
            "frequency_penalty": route.frequency_penalty
        }
        
        # Only apply dynamic adjustments to chat and proactive features if soul state is provided
        if soul_state and feature in ["chat", "proactive"]:
            return self._calculate_dynamic_params(base_params, soul_state, feature=feature)
            
        return base_params

    def _calculate_dynamic_params(self, params: Dict[str, float], soul: Dict[str, Any], feature: str = "chat") -> Dict[str, float]:
        """
        极致细腻算法：引入“双极社交张力”模型 (-3 到 5)
        最深厚的爱与最极端的恨都会激发更高的表达带宽，只有冷漠与陌生才会收缩。
        """
        new_params = params.copy()
        
        # 1. 提取基础变量
        pad = soul.get("pad", {"pleasure": 0.5, "arousal": 0.5, "dominance": 0.5})
        b5 = soul.get("big_five", {"openness": 0.5, "conscientiousness": 0.5, "extraversion": 0.5, "agreeableness": 0.5, "neuroticism": 0.5})
        p, a, d = float(pad.get("pleasure", 0.5)), float(pad.get("arousal", 0.5)), float(pad.get("dominance", 0.5))
        energy = float(soul.get("energy", 100)) / 100.0
        rel_level = int(soul.get("rel_level", 0))
        
        # --- A. 人格底色 (Big Five Baseline) ---
        # 1. 开放性 (Openness): 越高越有创意
        b5_temp_base = (float(b5.get("openness", 0.5)) - 0.5) * 0.4
        b5_top_p_base = (float(b5.get("openness", 0.5)) - 0.5) * 0.2
        
        # 2. 尽责性 (Conscientiousness): 越高越严谨、稳定（降低随机性）
        b5_temp_base -= (float(b5.get("conscientiousness", 0.5)) - 0.5) * 0.3
        b5_top_p_base -= (float(b5.get("conscientiousness", 0.5)) - 0.5) * 0.2
        
        # 3. 外倾性 (Extraversion): 越高越爱交流新话题
        b5_pp_base = (float(b5.get("extraversion", 0.5)) - 0.5) * 0.4
        
        # 4. 宜人性 (Agreeableness): 越高越温和，Topic 切换较温和（低 PP），用词讲究（高 FP）
        b5_pp_base -= (float(b5.get("agreeableness", 0.5)) - 0.5) * 0.2
        b5_fp_base = (float(b5.get("agreeableness", 0.5)) - 0.5) * 0.3
        
        # 5. 神经质 (Neuroticism): 越高，情绪波动对参数的影响放大倍率越大
        emotional_instability = 1.0 + (float(b5.get("neuroticism", 0.5)) - 0.5) * 1.5
        
        # --- B. 动态情绪 (PAD Dynamic Shifts) ---
        # 这里的偏移量会受神经质(Instability)和能量(Energy)的共同缩放
        mood_temp_shift = (p - 0.5) * 0.4 
        mood_top_p_shift = (a - 0.5) * 0.3
        mood_pp_shift = (d - 0.5) * 0.5
        mood_fp_shift = (d - 0.5) * 0.3
        
        # 2. 关系等级矩阵 (Relationship Impact Matrix)
        # 格式: { level: (temp_offset, top_p_offset, pp_offset, fp_offset) }
        rel_matrix = {
            -3: (0.50, 0.20, 0.60, 0.40),  # 死敌: 尖锐、疯狂、讽刺、极度厌恶套话
            -2: (0.25, 0.10, 0.30, 0.20),  # 敌视: 带刺、警惕、语言冷硬
            -1: (-0.30, -0.20, -0.20, -0.10), # 冷漠: 机械、敷衍、低能量交互
            0:  (0.00, 0.00, 0.00, 0.00),  # 陌生: 社交面具 (保持基础配置)
            1:  (0.10, 0.05, 0.05, 0.00),  # 泛泛: 逐渐放松
            2:  (0.20, 0.10, 0.10, 0.05),  # 友人: 舒适、有来有回
            3:  (0.35, 0.15, 0.25, 0.10),  # 知己: 情感流动、共鸣
            4:  (0.50, 0.25, 0.40, 0.20),  # 羁绊: 暧昧、张力、打破常规
            5:  (0.70, 0.35, 0.60, 0.30)   # 伴侣: 彻底释放、灵魂交互、拒绝任何陈词滥调
        }
        
        rel_offsets = rel_matrix.get(rel_level, (0, 0, 0, 0))
        
        # 3. 动态结算
        
        # A. 能量约束
        energy_mod = 1.0
        if energy < 0.2: energy_mod = 0.4
        elif energy > 0.8: energy_mod = 1.2
        
        # 统一计算动态偏移系数 (人格敏感度 * 能量)
        dynamic_factor = energy_mod * emotional_instability
        
        # B. 结合结算 (基础值 + 人格基调 + (动态心情偏移 * 系数) + 关系偏移)
        new_params["temperature"] += b5_temp_base + (mood_temp_shift * dynamic_factor) + rel_offsets[0]
        new_params["top_p"] += b5_top_p_base + (mood_top_p_shift * dynamic_factor) + rel_offsets[1]
        new_params["presence_penalty"] += b5_pp_base + (mood_pp_shift * dynamic_factor) + rel_offsets[2]
        new_params["frequency_penalty"] += b5_fp_base + (mood_fp_shift * dynamic_factor) + rel_offsets[3]
        
        # 4. 特殊情景硬裁剪 (The "Social Mask" at Level 0)
        if rel_level == 0:
            # 陌生人必须保持社交克制
            new_params["temperature"] = min(0.8, new_params["temperature"])
            new_params["top_p"] = min(0.8, new_params["top_p"])
        elif rel_level == -1:
            # 冷漠状态下禁止高活跃
            new_params["temperature"] = min(0.6, new_params["temperature"])
        
        # 5. 精度处理与边界安全
        new_params["temperature"] = float(round(max(0.1, min(2.0, new_params["temperature"])), 2))
        new_params["top_p"] = float(round(max(0.1, min(1.0, new_params["top_p"])), 2))
        new_params["presence_penalty"] = float(round(max(-2.0, min(2.0, new_params["presence_penalty"])), 2))
        new_params["frequency_penalty"] = float(round(max(-2.0, min(2.0, new_params["frequency_penalty"])), 2))
        
        if soul:
            import logging
            logger = logging.getLogger("LLMManager")
            logger.info(f"[LLMManager] Personality & Mood Logic ({feature}):")
            logger.info(f"  - Traits: B5_Temp_Base: {b5_temp_base:.2f}, Instability: {emotional_instability:.2f}")
            logger.info(f"  - State: L:{rel_level}, E:{energy:.2f} | PAD:({p},{a},{d}) -> {new_params}")
            
        return new_params

    def get_route(self, feature: str) -> Optional[FeatureRoute]:
        """Get the route configuration for a specific feature"""
        return self.config.routes.get(feature)

# Global Instance
llm_manager = LLMManager()
