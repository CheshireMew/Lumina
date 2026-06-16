from dependency_injector import containers, providers


class LuminaContainer(containers.DeclarativeContainer):
    config = providers.Object(None)
    event_bus = providers.Object(None)
    gateway = providers.Object(None)

    memory_service = providers.Object(None)
    llm_manager = providers.Object(None)

    system_plugin_manager = providers.Object(None)
    process_manager = providers.Object(None)
    reconciliation_service = providers.Object(None)
    capability_registry = providers.Object(None)
    capability_package_registry = providers.Object(None)
    plugin_state_aggregator = providers.Object(None)
    automation_service = providers.Object(None)

    soul = providers.Object(None)
    mcp_host = providers.Object(None)
    batch_manager = providers.Object(None)
    session_manager = providers.Object(None)
    skill_manager = providers.Object(None)
    chat_pipeline = providers.Object(None)
    chat_turn_service = providers.Object(None)
    chat_bridge = providers.Object(None)

    tts = providers.Object(None)
    stt = providers.Object(None)
    vision = providers.Object(None)

    ticker = providers.Object(None)
    config_watcher = providers.Object(None)
    prewarm_task = providers.Object(None)

    plugin_service = providers.Object(None)
    plugin_sync = providers.Object(None)
    character_service = providers.Object(None)
