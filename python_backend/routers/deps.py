from fastapi import Depends
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


def get_provider_config_service(c: ServiceContainer = Depends(get_container)) -> Any:
    return c.get_provider_config_service()


def get_soul_service(c: ServiceContainer = Depends(get_container)) -> Any:
    return c.get_soul()


def get_companion_context_resolver(c: ServiceContainer = Depends(get_container)) -> Any:
    return c.get_companion_context_resolver()


def get_companion_interaction_recorder(c: ServiceContainer = Depends(get_container)) -> Any:
    return c.get_companion_interaction_recorder()


def get_chat_turn_service(c: ServiceContainer = Depends(get_container)) -> Any:
    return c.get_chat_turn_service()


def get_companion_runtime(c: ServiceContainer = Depends(get_container)) -> Any:
    return c.get_companion_runtime()


def get_session_manager(c: ServiceContainer = Depends(get_container)) -> Any:
    return c.get_session_manager()


def get_character_service() -> Any:
    return services.get_character_service()
