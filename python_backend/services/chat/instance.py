from services.chat.pipeline import ChatPipeline

def create_chat_pipeline(llm_manager, list_tools, resolve_tool):
    return ChatPipeline(llm_manager, list_tools, resolve_tool)
