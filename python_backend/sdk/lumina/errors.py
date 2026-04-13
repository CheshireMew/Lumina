"""
Lumina SDK 错误类
=================

所有 SDK 错误的定义。
"""


class LuminaError(Exception):
    """Lumina SDK 基础错误"""
    pass


class TimeoutError(LuminaError):
    """操作超时"""
    pass


class PermissionError(LuminaError):
    """权限不足"""
    pass


class NotFoundError(LuminaError):
    """资源不存在"""
    pass


class DriverError(LuminaError):
    """驱动错误（TTS/STT/LLM 等）"""
    pass


class ConfigError(LuminaError):
    """配置错误"""
    pass


class HookError(LuminaError):
    """Hook 执行错误"""
    pass
