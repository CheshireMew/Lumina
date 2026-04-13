"""
LuminaSDK - 核心 SDK 类
=======================

提供所有 SDK 模块的统一访问入口。
"""

from .modules.tts import TTSModule
from .modules.stt import STTModule
from .modules.llm import LLMModule
from .modules.memory import MemoryModule
from .modules.ui import UIModule
from .modules.storage import StorageModule
from .modules.config import ConfigModule
from .modules.log import LogModule
from .hook import HookManager, hook as hook_decorator


class LuminaSDK:
    """
    Lumina SDK 核心类
    
    提供所有模块的访问入口：
        lumina.tts.speak("你好")
        lumina.llm.chat("问个问题")
        lumina.storage.set("key", value)
    """
    
    def __init__(self):
        # 延迟初始化标志
        self._initialized = False
        
        # 模块实例（延迟创建）
        self._tts: TTSModule = None
        self._stt: STTModule = None
        self._llm: LLMModule = None
        self._memory: MemoryModule = None
        self._ui: UIModule = None
        self._storage: StorageModule = None
        self._config: ConfigModule = None
        self._log: LogModule = None
        self._hook: HookManager = None
        
        # 内部服务容器引用（由系统注入）
        self._container = None
    
    def _ensure_initialized(self):
        """确保 SDK 已初始化"""
        if not self._initialized:
            raise RuntimeError(
                "Lumina SDK 尚未初始化。请确保在插件 load(context) 之后使用 SDK。"
            )
    
    def _initialize(self, container):
        """
        由系统调用，注入服务容器
        
        Args:
            container: Lumina 服务容器
        """
        self._container = container
        self._initialized = True
        
        # 创建模块实例
        self._tts = TTSModule(container)
        self._stt = STTModule(container)
        self._llm = LLMModule(container)
        self._memory = MemoryModule(container)
        self._ui = UIModule(container)
        self._storage = StorageModule(container)
        self._config = ConfigModule(container)
        self._log = LogModule(container)
        self._hook = HookManager(container)
    
    # ========== 模块访问器 ==========
    
    @property
    def tts(self) -> TTSModule:
        """语音合成模块"""
        self._ensure_initialized()
        return self._tts
    
    @property
    def stt(self) -> STTModule:
        """语音识别模块"""
        self._ensure_initialized()
        return self._stt
    
    @property
    def llm(self) -> LLMModule:
        """AI 对话模块"""
        self._ensure_initialized()
        return self._llm
    
    @property
    def memory(self) -> MemoryModule:
        """记忆系统模块"""
        self._ensure_initialized()
        return self._memory
    
    @property
    def ui(self) -> UIModule:
        """界面交互模块"""
        self._ensure_initialized()
        return self._ui
    
    @property
    def storage(self) -> StorageModule:
        """持久化存储模块"""
        self._ensure_initialized()
        return self._storage
    
    @property
    def config(self) -> ConfigModule:
        """配置读写模块"""
        self._ensure_initialized()
        return self._config
    
    @property
    def log(self) -> LogModule:
        """日志模块"""
        self._ensure_initialized()
        return self._log
    
    def hook(self, name: str, priority: int = 50, after=None, before=None):
        """Hook 装饰器入口。"""
        return hook_decorator(name, priority=priority, after=after, before=before)

    @property
    def hooks(self) -> HookManager:
        """Hook 管理器。"""
        self._ensure_initialized()
        return self._hook
