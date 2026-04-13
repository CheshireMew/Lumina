"""
Hello World 示例插件
====================

展示如何使用 Lumina SDK 开发插件。
"""

from lumina import Plugin as BasePlugin, lumina
from lumina.hook import HookContext, HookResult


class Plugin(BasePlugin):
    """
    Hello World 示例插件
    
    功能：
    - 在加载时打招呼
    - 在 TTS 输出前添加问候语
    """
    
    async def load(self, context):
        """插件加载时调用"""
        await super().load(context)
        lumina.log.info("Hello World 插件已加载！")
        
        # 保存一些数据
        await lumina.storage.set("load_count", 
            (await lumina.storage.get("load_count", 0)) + 1
        )
        
        count = await lumina.storage.get("load_count")
        lumina.log.info(f"这是第 {count} 次加载此插件")
    
    async def unload(self):
        """插件卸载时调用"""
        lumina.log.info("Hello World 插件再见！")
        await super().unload()
    
    # 注册 Hook：在 TTS 输出前添加问候语
    @lumina.hook("tts.before_speak", priority=50)
    async def add_greeting(self, ctx: HookContext) -> HookResult:
        """在 TTS 文本前添加问候语"""
        text = ctx.data
        
        # 如果文本以"你好"开头，不修改
        if text.startswith("你好"):
            return HookResult.next(text)
        
        # 添加问候语
        new_text = f"你好！{text}"
        lumina.log.debug(f"添加问候语: {text} -> {new_text}")
        
        return HookResult.next(new_text)
