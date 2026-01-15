
import logging
import json
import httpx
import asyncio
import time
from fastapi import APIRouter, Request, HTTPException
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
from typing import List, Optional, Dict, Any

logger = logging.getLogger("FreeLLMRouter")

# from llm.manager import llm_manager
from app_config import config as app_config
from services.container import services

# Search Skill Imports
try:
    from plugins.skills.brave_search import BraveSearch
except ImportError:
    BraveSearch = None

try:
    from plugins.skills.ddg_search import DuckDuckGoSearch
except ImportError:
    DuckDuckGoSearch = None

router = APIRouter(
    # prefix="/free-llm", # ⚙️ Disabled prefix to serve as default /v1 handler
    tags=["Unified LLM"]
)

def _get_soul_client():
    from services.container import services
    return services.soul_client

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

# --- Tool Definitions ---

WEB_SEARCH_TOOL = {
    "type": "function",
    "function": {
        "name": "web_search",
        "description": "Search the internet for real-time information, news, or facts not in your internal knowledge.",
        "strict": True, # DeepSeek Compatible
        "parameters": {
            "type": "object",
            "properties": {
                "query": {
                    "type": "string",
                    "description": "The search query, optimized for a search engine."
                }
            },
            "required": ["query"],
            "additionalProperties": False
        }
    }
}

async def handle_tool_call(tool_name: str, args: dict) -> str:
    """Execute tool and return string result"""
    if tool_name == "web_search":
        provider = app_config.search.provider # "brave" or "duckduckgo"
        logger.info(f"[UnifiedLLM] Web Search requested via provider: {provider}")
        
        # 1. Brave Search
        if provider == "brave":
            if not app_config.brave.api_key:
                 return "Error: Brave Search is configured but BRAVE_API_KEY is missing."
            if not BraveSearch:
                 return "Error: BraveSearch plugin not loaded."
            
            searcher = BraveSearch(api_key=app_config.brave.api_key, max_results=3)
            return await searcher.search(args.get("query", ""))
            
        # 2. DuckDuckGo (No Key)
        elif provider == "duckduckgo":
            if not DuckDuckGoSearch:
                 return "Error: duckduckgo-search library not found. System cannot perform search."
            
            searcher = DuckDuckGoSearch(max_results=3)
            return await searcher.search(args.get("query", ""))
            
        else:
            return f"Error: Unknown search provider '{provider}' configured."
    
    return f"Error: Unknown tool '{tool_name}'"


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
async def chat_completions(request: ChatCompletionRequest):
    """
    Unified Chat Endpoint (Phase 19).
    Delegates to UnifiedChatProcessor for RAG, Tools, and LLM.
    """
    soul_client = _get_soul_client()
    
    # Update Heartbeat
    if soul_client:
        soul_client.update_last_interaction()
    
    # Import processor
    from services.unified_chat import unified_chat
    
    # Convert Pydantic messages to dicts
    messages = [{"role": m.role, "content": m.content} for m in request.messages]
    
    # Extract user_id and character_id from context if available
    user_id = "default_user"
    character_id = "default_char"
    if soul_client:
        character_id = soul_client.character_id or character_id
    
    try:
        if request.stream:
            async def stream_generator():
                async for token in unified_chat.process(
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
            full_response = ""
            async for token in unified_chat.process(
                messages=messages,
                user_id=user_id,
                character_id=character_id,
                enable_rag=True,
                enable_tools=True,
                model=request.model,
                temperature=request.temperature,
                stream=False,
            ):
                full_response += token
            
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

async def _sse_formatter(generator):
    """Ensure output is SSE format"""
    async for chunk in generator:
        # If chunk is already formatted (string starting with data:), yield
        if isinstance(chunk, str) and chunk.startswith("data:"):
            yield chunk
        elif isinstance(chunk, str):
            # Raw text chunk? Wrap it
            yield _mock_chunk(chunk, "unified-model")
        else:
            # OpenAI Chunk Object? Verify and yield
            try:
                # If valid object with model_dump_json (Pydantic/Library)
                if hasattr(chunk, "model_dump_json"):
                     yield "data: " + chunk.model_dump_json() + "\n\n"
                else:
                     # Dictionary?
                     yield "data: " + json.dumps(chunk) + "\n\n"
            except:
                yield "data: [DONE]\n\n"
                
    yield "data: [DONE]\n\n"

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
