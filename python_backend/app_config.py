"""
Centralized Configuration for Lumina Backend.
Provides type-safe access to application settings via ConfigManager.
"""
import os
import json
import logging
import sys
from pathlib import Path
from typing import Dict, Any, Optional
from pydantic import BaseModel, Field

# Setup logging
logger = logging.getLogger("ConfigManager")

# Import SecretManager (lazy to avoid circular imports)
def _get_secret_manager():
    from security.secrets import SecretManager
    return SecretManager.instance()

try:
    import yaml
except ImportError:
    yaml = None
    logger.warning("PyYAML not installed. YAML config support disabled.")

# Load .env (Phase 27)
from dotenv import load_dotenv, find_dotenv
env_file = find_dotenv(usecwd=True) 
if env_file:
    logger.info(f"Loading environment variables from: {env_file}")
    load_dotenv(env_file)
else:
    logger.debug("No .env file found (Searching CWD)")

# --- Constants ---

IS_FROZEN = getattr(sys, 'frozen', False)

if IS_FROZEN:
    BASE_DIR = Path(sys._MEIPASS) # type: ignore
    CONFIG_ROOT = Path(sys.executable).parent
else:
    BASE_DIR = Path(__file__).parent.absolute()
    # In pure dev mode, config root might be project root or local data
    # We default CONFIG_ROOT to RESOLVED DATA ROOT in next steps, but providing a default here:
    CONFIG_ROOT = BASE_DIR # Fallback

# Determine Environment
ENV_VAR = os.getenv("LUMINA_ENV", "").lower()
IS_DEV = (not IS_FROZEN) or (ENV_VAR == "dev") or (ENV_VAR == "development")

# --- Data Path Resolution ---

def _resolve_data_root() -> Path:
    """
    Resolve the root directory for user data (configs, logs, db).
    Priority:
    1. LUMINA_DATA_PATH env var (Orchestrator override)
    2. ./Lumina_Data (Portable Mode - sibling of executable/script)
    3. %APPDATA%/Lumina (Standard Mode)
    """
    # 1. Env Var (Highest Priority)
    if os.environ.get("LUMINA_DATA_PATH"):
        env_path = Path(os.environ["LUMINA_DATA_PATH"])
        if not env_path.exists():
            try:
                env_path.mkdir(parents=True, exist_ok=True)
                logger.info(f"Created LUMINA_DATA_PATH: {env_path}")
                return env_path
            except Exception as e:
                logger.error(f"Failed to create LUMINA_DATA_PATH: {e}")
                # Fallthrough or crash? Better to fail loud or fallthrough?
                # Fallthrough might be safer if path is invalid.
        else:
             logger.info(f"Using LUMINA_DATA_PATH: {env_path}")
             return env_path
             
    # 2. Check for local "Lumina_Data" (Portable)
    # If frozen, executable is in a folder (e.g. dist/Lumina). We look in that folder.
    # If dev, we look in project root (parent of python_backend).
    
    if IS_FROZEN:
        exe_dir = Path(sys.executable).parent
        portable_dir = exe_dir / "Lumina_Data"
    else:
        # Dev mode: e:\Work\Code\Lumina (parent of python_backend)
        project_root = BASE_DIR.parent
        portable_dir = project_root / "Lumina_Data"
        
    if portable_dir.exists():
        logger.info(f"Portable Mode Detected: {portable_dir}")
        return portable_dir
    
    # [DEV MODE DEFAULT] Auto-create local data in dev
    if not IS_FROZEN:
        try:
            portable_dir.mkdir(parents=True, exist_ok=True)
            logger.info(f"Dev Mode: Auto-created local data dir: {portable_dir}")
            return portable_dir
        except Exception:
            pass # Fallback to AppData if write permission fails
        
    # 3. Standard AppData
    # Windows: %APPDATA%/Lumina
    # Linux/Mac: ~/.config/lumina
    home = Path.home()
    if sys.platform == "win32":
        app_data = home / "AppData" / "Roaming" / "Lumina"
    else:
        app_data = home / ".config" / "lumina"
        
    if not app_data.exists():
        try:
            app_data.mkdir(parents=True, exist_ok=True)
        except Exception as e:
            # Fallback to temp if strictly read-only system (unlikely but safe)
            import tempfile
            return Path(tempfile.gettempdir()) / "Lumina"
            
    return app_data

# Global Data Root Constant (Exported)
DATA_ROOT = _resolve_data_root()
CONFIG_ROOT = DATA_ROOT  # Configs now live in Data Root by default

# Ensure basic dirs exist
(DATA_ROOT / "logs").mkdir(exist_ok=True)
(DATA_ROOT / "database").mkdir(exist_ok=True)

# --- Configuration Models ---

class PostgresConfig(BaseModel):
    host: str = Field(default="localhost")
    port: int = Field(default=5432)
    user: str = Field(default="lumina_user")
    password: str = Field(default="lumina_password")
    database: str = Field(default="lumina_db")

class MemoryConfig(BaseModel):
    provider: str = Field(default="surreal") # 'surreal' or 'postgres'
    url: str = Field(default="ws://127.0.0.1:8001/rpc")
    
    # PostgreSQL Configuration
    postgres: PostgresConfig = Field(default_factory=PostgresConfig)
    
    # Root Credentials (Admin / Schema Migration)
    root_user: str = Field(default="root")
    root_password: str = Field(default="root")
    
    # Application Credentials (Least Privilege)
    app_user: str = Field(default="lumina_app")
    app_password: str = Field(default="")
    
    namespace: str = Field(default="lumina")
    database: str = Field(default="memory")
    character_id: str = Field(default="hiyori")  # Default character
    
    # Context Management
    history_limit: int = Field(default=20, ge=0, le=200) # Increased max
    overflow_strategy: str = Field(default="slide", pattern="^(slide|reset)$")

class LLMConfig(BaseModel):
    api_key: str = Field(default="")
    base_url: str = Field(default="https://api.deepseek.com/v1") # Aligned with Frontend default
    model: str = Field(default="deepseek-chat")

class STTConfig(BaseModel):
    provider: str = "sense-voice"
    model: str = "base"
    device: str = "cuda"
    compute_type: str = "float16"
    language: str = "zh"

class TTSConfig(BaseModel):
    provider: str = "edge-tts"
    voice: str = "zh-CN-XiaoxiaoNeural"

class AudioConfig(BaseModel):
    device_name: Optional[str] = None
    enable_voiceprint_filter: bool = True
    voiceprint_threshold: float = 0.45 
    voiceprint_profile: str = "default"


class SearchConfig(BaseModel):
    provider: str = "brave" # or "duckduckgo"
    enabled: bool = True


class PluginGroupsConfig(BaseModel):
    # Mapping Plugin ID -> Group ID
    # e.g. "mcp.obs": "recording_software", "system.cam": "recording_software"
    assignments: Dict[str, str] = {}
    
    # Mapping Plugin ID -> Category (skill, tts, stt, system, other)
    custom_categories: Dict[str, str] = {}

    # Mapping Group ID -> Behavior ('exclusive' or 'independent')
    group_behaviors: Dict[str, str] = {}

class PluginsConfig(BaseModel):
    """Global Plugin State Configuration"""
    disabled_plugins: list[str] = Field(default_factory=list)
    # [Architecture 4.0] Pre-warm Core Services (STT/TTS) on Startup
    prewarm_core: bool = Field(default=True)
    
    # [Refactor] Generic Plugin Settings (provider_id -> config dict)
    # Replaces hardcoded BraveConfig, BilibiliConfig, etc.
    settings: Dict[str, Dict[str, Any]] = Field(default_factory=dict)

class WorkerNodeConfig(BaseModel):
    host: str = "127.0.0.1"
    port: int
    id: str

class NetworkConfig(BaseModel):
    host: str = "127.0.0.1"
    memory_port: int = 8010
    stt_port: int = 8765
    tts_port: int = 8766
    surreal_port: int = 8001
    bind_localhost_only: bool = True 
    
    # [Architecture 5.2] Explicit Worker Registry
    workers: Dict[str, WorkerNodeConfig] = Field(default_factory=dict)

    @property
    def stt_url(self) -> str:
        return f"http://{self.host}:{self.stt_port}"

    @property
    def tts_url(self) -> str:
        return f"http://{self.host}:{self.tts_port}"

    @property
    def memory_url(self) -> str:
        return f"http://{self.host}:{self.memory_port}"

    def get_worker_url(self, worker_id: str) -> str:
        """Resolve worker URL with config fallback."""
        if worker_id in self.workers:
            w = self.workers[worker_id]
            return f"http://{w.host}:{w.port}"
        
        # Legacy Fallbacks
        if worker_id == "stt_server": return self.stt_url
        if worker_id == "tts_server": return self.tts_url
        
        raise ValueError(f"Unknown worker: {worker_id}")

class ModelsConfig(BaseModel):
    # Placeholder for standardized model paths
    stt_model_path: Optional[str] = None
    tts_model_path: Optional[str] = None
    embedding_model_name: str = "text-embedding-3-small"

    
class ConfigManager:
    _instance = None
    
    def __new__(cls):

        if cls._instance is None:
            cls._instance = super(ConfigManager, cls).__new__(cls)
            cls._instance._initialize()
        return cls._instance
    
    @property
    def is_dev(self) -> bool:
        return IS_DEV
    
    _frozen = False

    def __init__(self):
        # Default Initialization
        self._initialize()
        
    def freeze(self):
        """Lock configuration to prevent runtime modification."""
        self._frozen = True
        logger.info("🔒 Configuration Frozen (Immutable)")

    def __setattr__(self, key, value):
        if getattr(self, "_frozen", False):
            if not key.startswith("_"):
                raise TypeError(f"Configuration is frozen. Cannot modify '{key}'")
        super().__setattr__(key, value)

    def _initialize(self):
        self._memory_config = MemoryConfig()
        self._llm_config = LLMConfig()
        self._stt_config = STTConfig()
        self._tts_config = TTSConfig()
        self._audio_config = AudioConfig()
        self._network_config = NetworkConfig()
        # [Refactor] Removed hardcoded specific configs
        # self._brave_config = BraveConfig()
        # self._bilibili_config = BilibiliConfig()
        self._search_config = SearchConfig()
        self._plugin_groups_config = PluginGroupsConfig()
        self._plugins_config = PluginsConfig()
        self.load_configs()
    
    def load_configs(self):
        """
        Load configuration.
        Strategy: Single Source of Truth (YAML).
        1. If config.yaml exists -> LOAD IT. Ignore JSONs.
        2. If config.yaml missing -> LOAD JSONs (Legacy), MERGE, SAVE YAML, RENAME JSONs.
        """
        yaml_path = CONFIG_ROOT / "config.yaml"
        
        # [SCENARIO A] Standard Load (YAML Exists)
        if yaml_path.exists():
            if not yaml:
                logger.error("❌ YAML config exists but PyYAML not installed. Cannot load.")
                return

            try:
                with open(yaml_path, "r", encoding="utf-8") as f:
                    data = yaml.safe_load(f) or {}
                
                logger.info(f"📄 Loaded unified config from {yaml_path}")
                # [Finalize]
                self._hydrate_from_dict(data)
                logger.info("✅ Configuration Loaded & Applied")
                
                self.freeze()
                
                # [0. Load Network Config Override]
                self._load_ports_override()
                
            except Exception as e:
                logger.error(f"❌ Failed to load config.yaml: {e}")
                
            # Apply Env Overrides (Always high priority)
            self._apply_env_overrides()
            # Ensure URL sync after all overrides
            self._sync_memory_url()
            return

        # [SCENARIO B] First Run / Migration (YAML Missing)
        logger.info("⚠️ config.yaml not found. Attempting migration from legacy JSONs...")
        
        self._load_legacy_jsons()
        
        # [0. Load Network Config Override]
        self._load_ports_override()

        # Secrets Generation (Critical for First Run)
        self._ensure_secrets()
        
        # Sync memory URL to network/surreal_port to avoid mismatched defaults
        self._sync_memory_url()

        # Save to new YAML
        self.save()
        
        # Archive Legacy JSONs
        self._archive_legacy_jsons()
        
        # Apply Env Overrides
        self._apply_env_overrides()

    def _load_ports_override(self):
        """
        Check for ports.json (Bootstrap Override).
        Dev: Look in project_root/config/ports.json
        Prod: Look in CONFIG_ROOT/config/ports.json
        """
        # Strategy: Match Electron's lookup
        # Dev: BASE_DIR (python_backend) / ../config/ports.json
        # Prod: CONFIG_ROOT (DATA_ROOT) / config / ports.json
        
        paths_to_try = [
            BASE_DIR.parent / "config" / "ports.json", # Dev
            CONFIG_ROOT / "config" / "ports.json",     # Prod
            CONFIG_ROOT / "ports.json"                  # Fallback Root
        ]
        
        for p in paths_to_try:
            if p.exists():
                try:
                    with open(p, "r", encoding="utf-8") as f:
                        data = json.load(f)
                        # We only update network config from ports.json
                        # Expect keys like: stt_port, tts_port, memory_port, surreal_port
                        # NetworkConfig handles the mapping
                        self._network_config = NetworkConfig(**{**self._network_config.model_dump(), **data})
                        logger.info(f"🔌 Ports overridden by {p}")
                        return
                except Exception as e:
                    logger.error(f"Failed to load ports.json override from {p}: {e}")

    def _sync_memory_url(self):
        """Sync memory URL to network/surreal_port to avoid mismatched defaults"""
        # [Fix] Do not overwrite if SURREAL_URL env var is explicitly set
        if os.environ.get("SURREAL_URL"):
            return

        try:
            host = self._network_config.host
            surreal_port = self._network_config.surreal_port
            self._memory_config.url = f"ws://{host}:{surreal_port}/rpc"
            logger.debug(f"🔗 Synced Memory URL: {self._memory_config.url}")
        except Exception as e:
            logger.error(f"Failed to sync memory URL: {e}")

    def _hydrate_from_dict(self, data: Dict[str, Any]):
        """Populate config objects from dictionary"""
        try:
            if "network" in data: self._network_config = NetworkConfig(**data["network"])
            if "memory" in data: self._memory_config = MemoryConfig(**data["memory"])
            if "llm" in data: self._llm_config = LLMConfig(**data["llm"])
            if "stt" in data: self._stt_config = STTConfig(**data["stt"])
            if "tts" in data: self._tts_config = TTSConfig(**data["tts"])
            if "audio" in data: self._audio_config = AudioConfig(**data["audio"])
            if "search" in data: self._search_config = SearchConfig(**data["search"])
            
            # [Refactor] Migration Logic: Brave/Bilibili -> plugins.settings
            plugins_data = data.get("plugins", {})
            plugin_settings = plugins_data.get("settings", {})
            
            if "brave" in data:
                 plugin_settings.setdefault("brave", data["brave"])
            if "bilibili" in data:
                 plugin_settings.setdefault("bilibili", data["bilibili"])
                 
            # Re-inject updated settings into plugins_data
            plugins_data["settings"] = plugin_settings
            
            if "models" in data: self._models_config = ModelsConfig(**data["models"])
            if "plugin_groups" in data: self._plugin_groups_config = PluginGroupsConfig(**data["plugin_groups"])
            if "plugins" in data: self._plugins_config = PluginsConfig(**plugins_data)
        except Exception as e:
            logger.error(f"Hydration Error: {e}")
            
    # ... legacy json loading ...
    
    def _register_config_secrets(self):
        """
        Register config-based secrets as fallbacks in SecretManager.
        Called after config loading, before env overrides.
        """
        try:
            from security.secrets import SecretManager, SecretKey
            sm = SecretManager.instance()
            
            # LLM
            if self._llm_config.api_key:
                sm.set_config_fallback(SecretKey.OPENAI_API_KEY, self._llm_config.api_key)
            
            # Brave Search
            brave_settings = self._plugins_config.settings.get("brave", {})
            if brave_settings.get("api_key"):
                sm.set_config_fallback(SecretKey.BRAVE_API_KEY, brave_settings["api_key"])
            
            # Database
            if self._memory_config.root_password:
                sm.set_config_fallback(SecretKey.SURREAL_ROOT_PASS, self._memory_config.root_password)
            if self._memory_config.app_password:
                sm.set_config_fallback(SecretKey.SURREAL_APP_PASS, self._memory_config.app_password)
            if self._memory_config.postgres.password:
                sm.set_config_fallback(SecretKey.POSTGRES_PASSWORD, self._memory_config.postgres.password)
                
            logger.debug("🔐 Registered config secrets as fallbacks")
        except ImportError:
            logger.warning("SecretManager not available, skipping secret registration")

    def save(self):
        """
        Save current configuration to Unified config.yaml.
        Legacy JSON files are NO LONGER updated.
        """
        if not yaml:
            logger.error("Cannot save config: PyYAML not installed.")
            return

        try:
            yaml_path = CONFIG_ROOT / "config.yaml"
            
            # Construct dictionary
            data = {
                "network": self._network_config.model_dump(),
                "memory": self._memory_config.model_dump(),
                "llm": self._llm_config.model_dump(),
                "stt": self._stt_config.model_dump(),
                "tts": self._tts_config.model_dump(),
                "audio": self._audio_config.model_dump(),
                "search": self._search_config.model_dump(),
                # [Refactor] Removed hardcoded top-level keys
                # "brave": self._brave_config.model_dump(),
                # "bilibili": self._bilibili_config.model_dump(),
                "models": self._models_config.model_dump(),
                "plugin_groups": self._plugin_groups_config.model_dump(),
                "plugins": self._plugins_config.model_dump()
            }
            
            with open(yaml_path, "w", encoding="utf-8") as f:
                yaml.dump(data, f, allow_unicode=True, default_flow_style=False)
            
            logger.info(f"✅ Configuration saved to {yaml_path}")
            
        except Exception as e:
            logger.error(f"Failed to save configuration: {e}")
        
    def _apply_env_overrides(self):
        """
        Apply environment variable overrides.
        Uses SecretManager for sensitive values (API keys, passwords).
        """
        # First, register config values as fallbacks
        self._register_config_secrets()
        
        # Network Ports (Launcher/Electron Override) - Not secrets
        if os.environ.get("LUMINA_MEMORY_PORT"):
            self._network_config.memory_port = int(os.environ["LUMINA_MEMORY_PORT"])
        if os.environ.get("LUMINA_STT_PORT"):
            self._network_config.stt_port = int(os.environ["LUMINA_STT_PORT"])
        if os.environ.get("LUMINA_TTS_PORT"):
            self._network_config.tts_port = int(os.environ["LUMINA_TTS_PORT"])
        if os.environ.get("LUMINA_SURREAL_PORT"):
            self._network_config.surreal_port = int(os.environ["LUMINA_SURREAL_PORT"])

        # === Use SecretManager for Sensitive Values ===
        try:
            from security.secrets import SecretManager, SecretKey
            sm = SecretManager.instance()
            
            # LLM API Key
            api_key = sm.get(SecretKey.OPENAI_API_KEY)
            if api_key:
                self._llm_config.api_key = api_key
                logger.info(f"🔑 LLM API Key loaded from: {sm.get_source(SecretKey.OPENAI_API_KEY)}")
            
            # Brave Search API Key
            brave_key = sm.get(SecretKey.BRAVE_API_KEY)
            if brave_key:
                if "brave" not in self._plugins_config.settings:
                    self._plugins_config.settings["brave"] = {}
                self._plugins_config.settings["brave"]["api_key"] = brave_key
            
            # Database Passwords
            surreal_root = sm.get(SecretKey.SURREAL_ROOT_PASS)
            if surreal_root:
                self._memory_config.root_password = surreal_root
            
            surreal_app = sm.get(SecretKey.SURREAL_APP_PASS)
            if surreal_app:
                self._memory_config.app_password = surreal_app
                
            pg_pass = sm.get(SecretKey.POSTGRES_PASSWORD)
            if pg_pass:
                self._memory_config.postgres.password = pg_pass
                
        except ImportError:
            # Fallback: Direct env var access (legacy)
            logger.warning("⚠️ SecretManager not available, using direct env vars")
            if os.environ.get("OPENAI_API_KEY"):
                self._llm_config.api_key = os.environ["OPENAI_API_KEY"]
            if os.environ.get("BRAVE_API_KEY"):
                if "brave" not in self._plugins_config.settings:
                    self._plugins_config.settings["brave"] = {}
                self._plugins_config.settings["brave"]["api_key"] = os.environ["BRAVE_API_KEY"]
            if os.environ.get("SURREAL_ROOT_PASS"):
                self._memory_config.root_password = os.environ["SURREAL_ROOT_PASS"]
            if os.environ.get("SURREAL_APP_PASS"):
                self._memory_config.app_password = os.environ["SURREAL_APP_PASS"]

        # Non-secret overrides (URLs, usernames, etc.) - Direct env access
        if os.environ.get("OPENAI_BASE_URL"):
            self._llm_config.base_url = os.environ["OPENAI_BASE_URL"]
        if os.environ.get("LLM_MODEL"):
            self._llm_config.model = os.environ["LLM_MODEL"]
        if os.environ.get("SURREAL_URL"):
            self._memory_config.url = os.environ["SURREAL_URL"]
        if os.environ.get("SURREAL_ROOT_USER"):
            self._memory_config.root_user = os.environ["SURREAL_ROOT_USER"]
        if os.environ.get("SURREAL_APP_USER"):
            self._memory_config.app_user = os.environ["SURREAL_APP_USER"]
        if os.environ.get("SEARCH_PROVIDER"):
            self._search_config.provider = os.environ["SEARCH_PROVIDER"]

    @property
    def memory(self) -> MemoryConfig:
        return self._memory_config

    @property
    def llm(self) -> LLMConfig:
        return self._llm_config
        
    @property
    def stt(self) -> STTConfig:
        return self._stt_config

    @property
    def tts(self) -> TTSConfig:
        return self._tts_config

    @property
    def audio(self) -> AudioConfig:
        return self._audio_config
    
    @property
    def search(self) -> SearchConfig:
        return self._search_config

    @property
    def plugin_groups(self) -> PluginGroupsConfig:
        return self._plugin_groups_config
        
    @property
    def plugins(self) -> PluginsConfig:
        return self._plugins_config
        
    @property
    def network(self) -> NetworkConfig:
        return self._network_config

    @property
    def models(self) -> ModelsConfig:
        return self._models_config

    class PathsConfig:
        def __init__(self, base, models):
            self.base_dir = base
            self.models_dir = models

    @property
    def paths(self):
        from app_config import MODELS_DIR
        return self.PathsConfig(BASE_DIR, MODELS_DIR)
        
    @property
    def base_dir(self) -> Path:
        return BASE_DIR
        
    @property
    def data_root(self) -> Path:
        return DATA_ROOT

    @property
    def config_root(self) -> Path:
        return CONFIG_ROOT

# Global Singleton Accessor
config = ConfigManager()

# Legacy Constants for Backward Compatibility
# 鈿?Fix: Always use local project "models" directory if not frozen, to avoid C: drive bloat
if IS_FROZEN:
    MODELS_DIR = BASE_DIR / "models"
else:
    MODELS_DIR = BASE_DIR.parent / "models"

# Helper for resolving paths
def get_model_path(model_name: str) -> Path:
    """Resolve model path (local vs bundled)"""
    # Check Config Root first (User provided models)
    local_path = CONFIG_ROOT / "models" / model_name
    if local_path.exists():
        return local_path
        
    # Check Bundle path
    bundle_path = BASE_DIR / "models" / model_name
    return bundle_path

