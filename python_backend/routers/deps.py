from fastapi import Depends
from services.container import services, ServiceContainer
from typing import Any

# Base Container Dependency
def get_container() -> ServiceContainer:
    """Dependency Provider for the global ServiceContainer."""
    return services

# Service Accessors
def get_vision_service(c: ServiceContainer = Depends(get_container)) -> Any:
    """Get the Vision Service (VisionPluginManager)."""
    return c.get_vision()

def get_stt_service(c: ServiceContainer = Depends(get_container)) -> Any:
    """Get the STT Manager."""
    return c.get_stt()

def get_tts_service(c: ServiceContainer = Depends(get_container)) -> Any:
    """Get the TTS Manager."""
    return c.get_tts()

def get_llm_service(c: ServiceContainer = Depends(get_container)) -> Any:
    """Get the LLM Manager."""
    return c.get_llm_manager()

def get_memory_service(c: ServiceContainer = Depends(get_container)) -> Any:
    """Get the SurrealDB Memory System."""
    return c.get_surreal()

def get_config_service(c: ServiceContainer = Depends(get_container)) -> Any:
    """Get the Config Manager."""
    return c.get_config()
