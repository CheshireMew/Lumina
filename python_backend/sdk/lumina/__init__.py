"""
Lumina Plugin SDK
=================

让第三方开发者能轻松开发功能强大的插件。

Usage:
    from lumina import Plugin, lumina
    
    class MyPlugin(Plugin):
        async def load(self, context):
            await super().load(context)
            await lumina.tts.speak("插件已加载")

SDK Modules:
    lumina.llm      - AI 对话
    lumina.tts      - 语音合成
    lumina.stt      - 语音识别
    lumina.memory   - 记忆系统
    lumina.ui       - 界面交互
    lumina.storage  - 持久化存储
    lumina.config   - 配置读写
    lumina.log      - 日志
    lumina.hook     - 管道 Hook
"""

from .plugin import Plugin
from .sdk import LuminaSDK

# 全局 SDK 实例（插件通过这个访问所有功能）
lumina = LuminaSDK()

# 版本信息
__version__ = "0.1.0"
__all__ = ["Plugin", "lumina", "__version__"]
