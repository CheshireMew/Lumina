"""
UI 模块
=======

界面交互功能。

Example:
    await lumina.ui.notify("任务完成！")
    await lumina.ui.toast("正在处理...")
"""

import logging
from typing import Optional, Dict, Any, List

logger = logging.getLogger("Lumina.SDK.UI")


class UIModule:
    """
    界面交互模块
    
    Methods:
        notify(message, type) - 显示通知
        toast(message) - 显示 Toast
        register_widget(id, component, slot) - 注册 Widget
    """
    
    def __init__(self, container):
        self._container = container
        self._registered_widgets: List[Dict[str, Any]] = []
    
    async def notify(
        self,
        message: str,
        *,
        type: str = "info",
        title: str = None,
        duration: int = 5000,
        **kwargs
    ) -> None:
        """
        显示通知
        
        Args:
            message: 通知内容
            type: 类型 (info/success/warning/error)
            title: 标题（可选）
            duration: 显示时长（毫秒）
        
        Example:
            await lumina.ui.notify("任务完成！", type="success")
        """
        event_bus = getattr(self._container, 'event_bus', None)
        if event_bus:
            try:
                await event_bus.emit("ui.notification", {
                    "message": message,
                    "type": type,
                    "title": title,
                    "duration": duration,
                    **kwargs
                })
            except Exception as e:
                logger.warning(f"Failed to send notification: {e}")
        else:
            logger.info(f"[UI.Notify] {type.upper()}: {message}")
    
    async def toast(self, message: str, duration: int = 3000) -> None:
        """
        显示 Toast
        
        Args:
            message: 消息内容
            duration: 显示时长（毫秒）
        
        Example:
            await lumina.ui.toast("正在处理...")
        """
        event_bus = getattr(self._container, 'event_bus', None)
        if event_bus:
            try:
                await event_bus.emit("ui.toast", {
                    "message": message,
                    "duration": duration
                })
            except Exception as e:
                logger.warning(f"Failed to send Toast: {e}")
        else:
            logger.info(f"[UI.Toast] {message}")
    
    async def show_dialog(
        self,
        title: str,
        content: str,
        *,
        buttons: List[str] = None,
        **kwargs
    ) -> Optional[str]:
        """
        显示对话框
        
        Args:
            title: 标题
            content: 内容
            buttons: 按钮列表
        
        Returns:
            用户点击的按钮文本
        """
        event_bus = getattr(self._container, 'event_bus', None)
        if event_bus:
            try:
                # 发送对话框事件并等待响应
                await event_bus.emit("ui.dialog", {
                    "title": title,
                    "content": content,
                    "buttons": buttons or ["确定"],
                    **kwargs
                })
            except Exception as e:
                logger.warning(f"Failed to show dialog: {e}")
        return None
    
    def register_widget(
        self,
        id: str,
        component: str,
        slot: str,
        *,
        props: Dict[str, Any] = None,
        **kwargs
    ) -> None:
        """
        注册 Widget 到 UI 插槽
        
        Args:
            id: Widget ID
            component: 组件文件路径
            slot: 插槽位置 (sidebar/toolbar/panel)
            props: 组件属性
        
        Example:
            lumina.ui.register_widget(
                id="my_widget",
                component="widgets/MyWidget.tsx",
                slot="sidebar"
            )
        """
        widget = {
            "id": id,
            "component": component,
            "slot": slot,
            "props": props or {},
            **kwargs
        }
        self._registered_widgets.append(widget)
        logger.info(f"Widget registered: {id} -> {slot}")
    
    def get_registered_widgets(self) -> List[Dict[str, Any]]:
        """获取所有注册的 Widget"""
        return self._registered_widgets
