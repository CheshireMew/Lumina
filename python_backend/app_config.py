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
    1. ./Lumina_Data (Portable Mode - sibling of executable/script)
    2. LUMINA_DATA_PATH env var
    3. %APPDATA%/Lumina (Standard Mode)
    """
    # 1. Check for local "Lumina_Data" (Portable)
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
        
    # 2. Env Var
    if os.environ.get("LUMINA_DATA_PATH"):
        env_path = Path(os.environ["LUMINA_DATA_PATH"])
        if not env_path.exists():
            try:
                env_path.mkdir(parents=True, exist_ok=True)
            except Exception as e:
                logger.error(f"Failed to create LUMINA_DATA_PATH: {e}")
        return env_path
        
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

DATA_ROOT = _resolve_data_root()
CONFIG_ROOT = DATA_ROOT  # Configs now live in Data Root by default

# Ensure basic dirs exist
(DATA_ROOT / "logs").mkdir(exist_ok=True)
(DATA_ROOT / "database").mkdir(exist_ok=True)

# --- Configuration Models ---

class MemoryConfig(BaseModel):
    provider: str = Field(default="surreal") # 'surreal' or 'postgres'
    url: str = Field(default="ws://127.0.0.1:8001/rpc")
    
    # Root Credentials (Admin / Schema Migration)
    root_user: str = Field(default="root")
    root_password: str = Field(default="root")
    
    # Application Credentials (Least Privilege)
    app_user: str = Field(default="lumina_app")
    app_password: str = Field(default="lumina_secure_pass")
    
    namespace: str = Field(default="lumina")
    database: str = Field(default="memory")
    character_id: str = Field(default="hiyori")  # Default character

class LLMConfig(BaseModel):
    api_key: str = Field(default="")
    base_url: str = Field(default="http://localhost:11434/v1")
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
    enable_voiceprint_filter: bool = False
    voiceprint_threshold: float = 0.45 
    voiceprint_profile: str = "default"
    fish_audio_api_key: str = ""
    fish_audio_api_url: str = "https://api.fish.audio/v1"
    
    api_key: str = Field(default="")
    max_results: int = 5

class SearchConfig(BaseModel):
    provider: str = "brave" # or "duckduckgo"
    enabled: bool = True

class BilibiliConfig(BaseModel):
    enabled: bool = False
    room_id: int = 21743919 # Default room

class PluginGroupsConfig(BaseModel):
    # Mapping Plugin ID -> Group ID
    # e.g. "mcp.obs": "recording_software", "system.cam": "recording_software"
    assignments: Dict[str, str] = {}
    
    # Mapping Plugin ID -> Category (skill, tts, stt, system, other)
    custom_categories: Dict[str, str] = {}

    # Mapping Group ID -> Behavior ('exclusive' or 'independent')
    group_behaviors: Dict[str, str] = {}

class BraveConfig(BaseModel):
    api_key: str = ""
    
class NetworkConfig(BaseModel):
    host: str = "127.0.0.1"
    memory_port: int = 8010
    stt_port: int = 8765
    tts_port: int = 8766
    surreal_port: int = 8001
    bind_localhost_only: bool = True # Security Hardening: Default to Localhost only

    @property
    def stt_url(self) -> str:
        return f"http://{self.host}:{self.stt_port}"

    @property
    def tts_url(self) -> str:
        return f"http://{self.host}:{self.tts_port}"

    @property
    def memory_url(self) -> str:
        return f"http://{self.host}:{self.memory_port}"

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

    def _initialize(self):
        self._memory_config = MemoryConfig()
        self._llm_config = LLMConfig()
        self._stt_config = STTConfig()
        self._tts_config = TTSConfig()
        self._audio_config = AudioConfig()
        self._network_config = NetworkConfig()
        self._models_config = ModelsConfig()
        self._brave_config = BraveConfig()
        self._search_config = SearchConfig()
        self._bilibili_config = BilibiliConfig()
        self._plugin_groups_config = PluginGroupsConfig()
        self.load_configs()
    
    def load_configs(self):
        """Load all configurations from JSON files and Environment variables"""
        
        # 0. Load Network Config (New)
        # Look in project_root/config/ports.json (Dev) or DATA_ROOT/ports.json (Prod/Fallback)
        ports_path = BASE_DIR.parent / "config" / "ports.json"
        if not ports_path.exists():
             ports_path = CONFIG_ROOT / "ports.json"
             
        if ports_path.exists():
            try:
                with open(ports_path, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    self._network_config = NetworkConfig(**data)
            except Exception as e:
                logger.error(f"Failed to load ports.json: {e}")
        

        
        # 1. Load Memory Config
        # Try DATA_ROOT first, then bundle fallback (optional, skipping complexity for now)
        mem_path = CONFIG_ROOT / "memory_config.json"
        if mem_path.exists():
            try:
                with open(mem_path, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    # Support legacy simplified format if needed, or straight mapping
                    self._memory_config = MemoryConfig(**data)
                    # Also load LLM settings if they were mixed in memory_config (legacy behavior)
                    if "base_url" in data or "api_key" in data:
                        self._llm_config = LLMConfig(**data)
            except Exception as e:
                logger.error(f"Failed to load memory_config.json: {e}")

        # Sync memory URL to network/surreal_port to avoid mismatched defaults
        # [FIX] Run AFTER loading config file so Network Config (Authority) overrides file staledata
        try:
            host = self._network_config.host
            surreal_port = getattr(self._network_config, "surreal_port", None)
            if surreal_port:
                self._memory_config.url = f"ws://{host}:{surreal_port}/rpc"
        except Exception as e:
            logger.error(f"Failed to sync memory URL with network config: {e}")

        # 2. Load STT Config
        stt_path = CONFIG_ROOT / "stt_config.json"
        if stt_path.exists():
            try:
                with open(stt_path, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    self._stt_config = STTConfig(**data)
            except Exception as e:
                logger.error(f"Failed to load stt_config.json: {e}")

        # 3. Load Audio Config
        audio_path = CONFIG_ROOT / "audio_config.json"
        if audio_path.exists():
            try:
                with open(audio_path, "r", encoding="utf-8-sig") as f:
                    data = json.load(f)
                    self._audio_config = AudioConfig(**data)
            except Exception as e:
                logger.error(f"Failed to load audio_config.json: {e}")
                
        # 4. Plugin Groups (Independent)
        groups_path = CONFIG_ROOT / "plugin_groups.json"
        if groups_path.exists():
            try:
                with open(groups_path, "r", encoding="utf-8") as f:
                    self._plugin_groups_config = PluginGroupsConfig(**json.load(f))
            except Exception as e:
                logger.error(f"Failed to load plugin_groups.json: {e}")

        # 3. Environment Overrides (Higher Priority)
        self._apply_env_overrides()

    def save(self):
        """
        Save current configuration to JSON files in CONFIG_ROOT.
        Supports: memory_config.json, stt_config.json, audio_config.json, plugin_groups.json
        """
        try:
            # 1. Audio Config
            audio_path = CONFIG_ROOT / "audio_config.json"
            with open(audio_path, "w", encoding="utf-8") as f:
                json.dump(self._audio_config.model_dump(), f, indent=4, ensure_ascii=False)
            
            # 2. STT Config
            stt_path = CONFIG_ROOT / "stt_config.json"
            with open(stt_path, "w", encoding="utf-8") as f:
                json.dump(self._stt_config.model_dump(), f, indent=4, ensure_ascii=False)

            # 3. Plugin Groups
            groups_path = CONFIG_ROOT / "plugin_groups.json"
            with open(groups_path, "w", encoding="utf-8") as f:
                json.dump(self._plugin_groups_config.model_dump(), f, indent=4, ensure_ascii=False)

            # 3. TTS Config? (If needed, currently just defaulting)
            # 4. Search Config? (If needed)
            
            logger.info("Configuration saved successfully.")
        except Exception as e:
            logger.error(f"Failed to save configuration: {e}")
        
    def _apply_env_overrides(self):
        # LLM
        if os.environ.get("OPENAI_API_KEY"):
            self._llm_config.api_key = os.environ["OPENAI_API_KEY"]
        if os.environ.get("OPENAI_BASE_URL"):
            self._llm_config.base_url = os.environ["OPENAI_BASE_URL"]
        if os.environ.get("LLM_MODEL"):
            self._llm_config.model = os.environ["LLM_MODEL"]
            
        # Memory
        if os.environ.get("SURREAL_URL"):
            self._memory_config.url = os.environ["SURREAL_URL"]
        
        # Root Creds
        if os.environ.get("SURREAL_ROOT_USER"):
            self._memory_config.root_user = os.environ["SURREAL_ROOT_USER"]
        if os.environ.get("SURREAL_ROOT_PASS"):
            self._memory_config.root_password = os.environ["SURREAL_ROOT_PASS"]
            
        # App Creds
        if os.environ.get("SURREAL_APP_USER"):
            self._memory_config.app_user = os.environ["SURREAL_APP_USER"]
        if os.environ.get("SURREAL_APP_PASS"):
            self._memory_config.app_password = os.environ["SURREAL_APP_PASS"]

        # Brave Search
        if os.environ.get("BRAVE_API_KEY"):
            self._brave_config.api_key = os.environ["BRAVE_API_KEY"]
            
        # Search Provider
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
    def brave(self) -> BraveConfig:
        return self._brave_config

    @property
    def search(self) -> SearchConfig:
        return self._search_config


    @property
    def bilibili(self) -> BilibiliConfig:
        return self._bilibili_config

    @property
    def plugin_groups(self) -> PluginGroupsConfig:
        return self._plugin_groups_config
        
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

