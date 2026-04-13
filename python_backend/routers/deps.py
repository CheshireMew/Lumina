from fastapi import Depends, HTTPException
from services.container import services, ServiceContainer
from typing import Any


def get_container() -> ServiceContainer:
    return services


def get_vision_service(c: ServiceContainer = Depends(get_container)) -> Any:
    return c.get_vision()


def get_stt_service(c: ServiceContainer = Depends(get_container)) -> Any:
    return c.get_stt()


def get_tts_service(c: ServiceContainer = Depends(get_container)) -> Any:
    return c.get_tts()


def get_llm_service(c: ServiceContainer = Depends(get_container)) -> Any:
    return c.get_llm_manager()


def get_memory_service(c: ServiceContainer = Depends(get_container)) -> Any:
    return c.get_memory()


def get_config_service(c: ServiceContainer = Depends(get_container)) -> Any:
    return c.get_config()


def get_config_controller(c: ServiceContainer = Depends(get_container)) -> Any:
    from services.config_service import ConfigService

    return ConfigService(c)


def get_runtime_service_dep(c: ServiceContainer = Depends(get_container)) -> Any:
    from services.runtime_service import RuntimeService

    return RuntimeService(c)


def get_plugin_service(c: ServiceContainer = Depends(get_container)) -> Any:
    return c.get_plugin_service()


def get_system_plugin_manager(c: ServiceContainer = Depends(get_container)) -> Any:
    manager = c.system_plugin_manager
    if not manager:
        raise HTTPException(status_code=503, detail="Plugin Manager unavailable")
    return manager


def get_optional_system_plugin_manager(c: ServiceContainer = Depends(get_container)) -> Any:
    return c.system_plugin_manager


def get_soul_service(c: ServiceContainer = Depends(get_container)) -> Any:
    soul = c.soul
    if not soul:
        raise HTTPException(status_code=503, detail="Soul Service not initialized")
    return soul


def get_optional_soul_service(c: ServiceContainer = Depends(get_container)) -> Any:
    return c.soul


def get_chat_turn_service(c: ServiceContainer = Depends(get_container)) -> Any:
    return c.get_chat_turn_service()


def get_session_manager(c: ServiceContainer = Depends(get_container)) -> Any:
    session_manager = c.session_manager
    if not session_manager:
        raise HTTPException(status_code=503, detail="Session Manager not initialized")
    return session_manager


def get_character_service() -> Any:
    return services.get_character_service()
