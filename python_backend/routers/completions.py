
import logging
import json
import time
from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
from typing import List, Optional, Dict

logger = logging.getLogger("FreeLLMRouter")

# from llm.manager import llm_manager
from app_config import config as app_config
from routers.deps import get_chat_turn_service, get_soul_service

router = APIRouter(
    tags=["Unified LLM"]
)

# OpenAI-compatible Request Models
class ChatMessage(BaseModel):
    role: str
    content: str
    name: Optional[str] = None
    tool_calls: Optional[List[Dict]] = None
    tool_call_id: Optional[str] = None

class ChatCompletionRequest(BaseModel):
    model: str = "gpt-4o-mini"
    messages: List[ChatMessage]
    stream: bool = False
    max_tokens: Optional[int] = None
    temperature: Optional[float] = 0.7
    top_p: Optional[float] = None
    presence_penalty: Optional[float] = None
    frequency_penalty: Optional[float] = None

def mask_log(text: str) -> str:
    """Mask sensitive content in logs unless in DEV mode."""
    # Lazy import to avoid circular dependency if needed, or rely on global app_config
    if app_config.is_dev:
        return text
    if not text:
        return ""
    length = len(text)
    if length <= 20: 
        return "*" * length
    return f"{text[:10]}...[HIDDEN:{length-20}]...{text[-10:]}"

# --- Main Logic ---

@router.post("/v1/chat/completions")
async def chat_completions(
    request: ChatCompletionRequest,
    chat_service=Depends(get_chat_turn_service),
    soul_service=Depends(get_soul_service),
):
    """
    Unified Chat Endpoint (Phase 19).
    Delegates to UnifiedChatProcessor for RAG, Tools, and LLM.
    """
    # [Security] Input Guardrails
    from core.security.guardrails import InputGuard
    
    # Check User Permissions? (Checking headers first?)
    # ...
    
    # Check Content
    messages_dicts = [{"role": m.role, "content": m.content} for m in request.messages]
    is_safe, reason = InputGuard.validate_messages(messages_dicts)
    if not is_safe:
        logger.warning(f"🛡️ Blocked Unsafe Request: {reason}")
        raise HTTPException(status_code=400, detail=f"Content Policy Error: {reason}")

    # Update Heartbeat
    soul_service.update_last_interaction()
    
    messages = []
    for m in request.messages:
        msg_dict = {"role": m.role, "content": m.content}
        if m.name: msg_dict["name"] = m.name
        if m.tool_calls: msg_dict["tool_calls"] = m.tool_calls
        if m.tool_call_id: msg_dict["tool_call_id"] = m.tool_call_id
        messages.append(msg_dict)
    
    # Extract user_id and character_id from the active runtime context.
    user_id = "default_user"
    character_id = chat_service.active_character_id()
    
    try:
        if request.stream:
            async def stream_generator():
                async for token in chat_service.stream_response(
                    messages=messages,
                    user_id=user_id,
                    character_id=character_id,
                    enable_rag=True,
                    enable_tools=True,
                    model=request.model,
                    temperature=request.temperature,
                    stream=True,
                ):
                    yield _mock_chunk(token, request.model)
                yield "data: [DONE]\n\n"
            
            return StreamingResponse(stream_generator(), media_type="text/event-stream")
        else:
            # Non-streaming: collect full response
            full_response = await chat_service.collect_response(
                messages=messages,
                user_id=user_id,
                character_id=character_id,
                enable_rag=True,
                enable_tools=True,
                model=request.model,
                temperature=request.temperature,
            )
            
            return {
                "id": "chatcmpl-unified",
                "object": "chat.completion",
                "created": int(time.time()),
                "model": request.model,
                "choices": [{
                    "index": 0,
                    "message": {
                        "role": "assistant",
                        "content": full_response
                    },
                    "finish_reason": "stop"
                }]
            }
    except Exception as e:
        logger.error(f"[UnifiedChat] Generation Error: {e}")
        raise HTTPException(status_code=500, detail=str(e))

def _mock_chunk(content: str, model: str) -> str:
    """Helper to create OpenAI-compatible delta chunk"""
    return "data: " + json.dumps({
        "id": "chatcmpl-unified",
        "object": "chat.completion.chunk",
        "created": int(time.time()),
        "model": model,
        "choices": [{
            "index": 0,
            "delta": {"content": content},
            "finish_reason": None
        }]
    }) + "\n\n"
