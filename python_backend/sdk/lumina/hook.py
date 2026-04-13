"""
Hook 系统
=========

允许插件介入系统管道，修改或拦截数据流。

Example:
    @lumina.hook("audio.before_transcribe")
    async def my_filter(ctx: HookContext) -> HookResult:
        cleaned = denoise(ctx.data)
        return HookResult.next(cleaned)
"""

import logging
from typing import Any, Callable, Dict, List, Optional
from dataclasses import dataclass
from enum import Enum

logger = logging.getLogger("Lumina.SDK.Hook")


class HookAction(Enum):
    """Hook 执行结果动作"""
    NEXT = "next"      # 继续执行，传递数据
    SKIP = "skip"      # 跳过后续 Hook
    ABORT = "abort"    # 终止整个管道


@dataclass
class HookContext:
    """Hook 上下文"""
    data: Any                          # 当前数据
    metadata: Dict[str, Any]           # 元信息
    hook_name: str                     # Hook 名称
    plugin_id: str                     # 调用插件 ID


@dataclass
class HookResult:
    """Hook 执行结果"""
    action: HookAction
    data: Any = None
    reason: str = ""
    
    @classmethod
    def next(cls, data: Any = None) -> "HookResult":
        """继续执行，传递修改后的数据"""
        return cls(action=HookAction.NEXT, data=data)
    
    @classmethod
    def skip(cls) -> "HookResult":
        """跳过后续 Hook，但继续管道"""
        return cls(action=HookAction.SKIP)
    
    @classmethod
    def abort(cls, reason: str = "") -> "HookResult":
        """终止整个管道"""
        return cls(action=HookAction.ABORT, reason=reason)


@dataclass
class HookRegistration:
    """Hook 注册信息"""
    hook_name: str
    handler: Callable
    plugin_id: str
    priority: int = 50
    after: List[str] = None
    before: List[str] = None


class HookManager:
    """
    Hook 管理器
    
    管理所有 Hook 的注册和执行。
    """
    
    _instance: Optional["HookManager"] = None

    @classmethod
    def instance(cls) -> Optional["HookManager"]:
        return cls._instance

    def __init__(self, container):
        self._container = container
        self._hooks: Dict[str, List[HookRegistration]] = {}
        HookManager._instance = self
    
    def register(
        self,
        hook_name: str,
        handler: Callable,
        plugin_id: str,
        priority: int = 50,
        after: List[str] = None,
        before: List[str] = None
    ):
        """
        注册 Hook
        
        Args:
            hook_name: Hook 名称（如 "audio.before_transcribe"）
            handler: 处理函数
            plugin_id: 插件 ID
            priority: 优先级（数字越大越先执行）
            after: 在哪些插件之后执行
            before: 在哪些插件之前执行
        """
        if hook_name not in self._hooks:
            self._hooks[hook_name] = []
        
        registration = HookRegistration(
            hook_name=hook_name,
            handler=handler,
            plugin_id=plugin_id,
            priority=priority,
            after=after or [],
            before=before or []
        )
        
        self._hooks[hook_name].append(registration)
        self._sort_hooks(hook_name)
        
        logger.debug(f"Hook 已注册: {hook_name} by {plugin_id}")
    
    def _sort_hooks(self, hook_name: str):
        """按优先级和依赖排序 Hook"""
        hooks = self._hooks.get(hook_name, [])
        # 简单实现：按 priority 降序排序
        hooks.sort(key=lambda h: -h.priority)
    
    async def execute(
        self,
        hook_name: str,
        data: Any,
        metadata: Dict[str, Any] = None
    ) -> tuple[Any, bool]:
        """
        执行 Hook 链
        
        Args:
            hook_name: Hook 名称
            data: 初始数据
            metadata: 元信息
        
        Returns:
            (最终数据, 是否继续)
        """
        hooks = self._hooks.get(hook_name, [])
        if not hooks:
            return data, True
        
        current_data = data
        metadata = metadata or {}
        
        for hook in hooks:
            ctx = HookContext(
                data=current_data,
                metadata=metadata,
                hook_name=hook_name,
                plugin_id=hook.plugin_id
            )
            
            try:
                result = await hook.handler(ctx)
                
                if not isinstance(result, HookResult):
                    # 如果没有返回 HookResult，假设 next
                    result = HookResult.next(result)
                
                if result.action == HookAction.ABORT:
                    logger.info(f"Hook {hook_name} terminated by {hook.plugin_id}: {result.reason}")
                    return current_data, False
                
                if result.action == HookAction.SKIP:
                    break
                
                if result.data is not None:
                    current_data = result.data
                    
            except Exception as e:
                logger.error(f"Hook {hook_name} execution failed ({hook.plugin_id}): {e}")
                # 继续执行其他 Hook
        
        return current_data, True

    async def trigger(
        self,
        hook_name: str,
        data: Any,
        metadata: Dict[str, Any] = None
    ) -> HookResult:
        """
        Compatibility wrapper around execute().
        """
        current_data, should_continue = await self.execute(
            hook_name,
            data,
            metadata=metadata,
        )
        if should_continue:
            return HookResult.next(current_data)
        return HookResult.abort("Hook chain aborted")
    
    def unregister(self, plugin_id: str):
        """注销插件的所有 Hook"""
        for hook_name in self._hooks:
            self._hooks[hook_name] = [
                h for h in self._hooks[hook_name] if h.plugin_id != plugin_id
            ]


def hook(
    name: str,
    priority: int = 50,
    after: List[str] = None,
    before: List[str] = None
):
    """
    Hook 装饰器
    
    Example:
        @lumina.hook("audio.before_transcribe", priority=100)
        async def my_hook(ctx: HookContext) -> HookResult:
            return HookResult.next(ctx.data)
    """
    def decorator(func):
        # 标记为 Hook，由系统在加载时注册
        func._hook_info = {
            "name": name,
            "priority": priority,
            "after": after or [],
            "before": before or []
        }
        return func
    return decorator
