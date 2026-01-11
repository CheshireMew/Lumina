
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

router = APIRouter(
    # prefix="/free-llm", # ⚡ Disabled prefix to serve as default /v1 handler
    tags=["Free LLM (Pollinations.ai)"]
)

# Global Deps
soul_client = None

def inject_dependencies(soul=None):
    global soul_client
    if soul:
        soul_client = soul

# OpenAI-compatible Request Models
class ChatMessage(BaseModel):
    role: str
    content: str
    name: Optional[str] = None

class ChatCompletionRequest(BaseModel):
    model: str = "gpt-4o-mini"
    messages: List[ChatMessage]
    stream: bool = False
    max_tokens: Optional[int] = None
    temperature: Optional[float] = 0.7

async def stream_pollinations_response(messages: List[ChatMessage], model: str):
    """
    Generator for streaming Pollinations.ai response.
    Since API is non-streaming, we fetch full text and yield chunks.
    """
    
    # Map incoming model config to Pollinations-friendly names
    # Default: 'openai' -> GPT-4o-mini equivalent
    target_model = "openai" 
    if "mistral" in model.lower(): target_model = "mistral"
    if "llama" in model.lower(): target_model = "llama"
    
    url = f"https://text.pollinations.ai/{target_model}"
    headers = {"Content-Type": "application/json"}
    
    # Pollinations expects just the messages list in body implies context
    # format: {"messages": [...], "seed": ..., "model": ...}
    payload = {
        "messages": [{"role": m.role, "content": m.content} for m in messages],
        "seed": 42,
        "model": target_model
    }

    async with httpx.AsyncClient(headers=headers, timeout=120.0) as client:
        try:
            # Standard POST (Non-streaming)
            resp = await client.post(url, json=payload)
            
            if resp.status_code != 200:
                logger.error(f"[FreeLLM] Pollinations Error: {resp.status_code} - {resp.text}")
                yield f"data: {json.dumps({'error': f'Backing API Error: {resp.status_code}'})}\n\n"
                # Fallback message
                err_msg = f"⚠️ Pollinations API Error ({resp.status_code}). Please try again."
                yield _mock_chunk(err_msg, model)
                yield "data: [DONE]\n\n"
                return

            # Pollinations returns OpenAI-compatible JSON
            # We must parse it to get the actual text content
            try:
                response_json = resp.json()
                # Check for direct text (unlikely) or OpenAI format
                if isinstance(response_json, str):
                    content = response_json
                else:
                    content = response_json.get("choices", [{}])[0].get("message", {}).get("content", "")
                    
                # Logging reasoning if available (DeepSeek/R1 feature via Pollinations)
                reasoning = response_json.get("choices", [{}])[0].get("message", {}).get("reasoning_content")
                if reasoning:
                    logger.info(f"[FreeLLM] Model Reasoning: {reasoning[:100]}...")

            except Exception as json_err:
                logger.warning(f"[FreeLLM] Failed to parse JSON, assuming raw text: {json_err}")
                content = resp.text

            if not content:
                content = "(No response content received)"
            
            # ⚡ Mock Streaming to satisfy Frontend
            # Split by words/chars to simulate typing effect
            chunk_size = 4 
            for i in range(0, len(content), chunk_size):
                chunk = content[i:i+chunk_size]
                yield _mock_chunk(chunk, model)
                # tiny sleep to simulate generation time (optional, makes it feel real)
                await asyncio.sleep(0.01)
                
            yield "data: [DONE]\n\n"
            
        except Exception as e:
            logger.error(f"[FreeLLM] Connection Error: {e}")
            err_msg = f"⚠️ Network Error: {str(e)}\n\n(Pollinations.ai is unreachable. Please checks your network or switch to Custom Provider)"
            yield _mock_chunk(err_msg, model)
            yield "data: [DONE]\n\n"

def _mock_chunk(content: str, model: str) -> str:
    """Helper to create OpenAI-compatible delta chunk"""
    return "data: " + json.dumps({
        "id": "chatcmpl-pollinations",
        "object": "chat.completion.chunk",
        "created": 1700000000,
        "model": model,
        "choices": [{
            "index": 0,
            "delta": {"content": content},
            "finish_reason": None
        }]
    }) + "\n\n"

@router.post("/v1/chat/completions")
async def chat_completions(request: ChatCompletionRequest):
    """
    OpenAI-Compatible Endpoint backed by Pollinations.ai (Free/No-Key)
    """
    logger.info(f"[FreeLLM] Request for model: {request.model} (Stream: {request.stream})")
    
    # ⚡ Update Last Interaction to prevent Proactive Chat coming up
    if soul_client:
        soul_client.update_last_interaction()
        logger.debug("[FreeLLM] Active interaction detected -> Resetting Heartbeat Idle Timer")
    
    # Handle Non-Streaming Request (Used by Extractor/Dreaming)
    if not request.stream:
        # Standard synchronous response logic
        return await _handle_non_streaming(request.messages, request.model)

    return StreamingResponse(
        stream_pollinations_response(request.messages, request.model),
        media_type="text/event-stream"
    )

async def _handle_non_streaming(messages: List[ChatMessage], model: str):
    """Fetch full response and return standard ChatCompletion JSON"""
    # ⚡ Use standard OpenAI endpoint logic
    target_model = "openai" 
    
    # Pollinations 404s on /mistral, so we must use /openai but pass model in body if supported
    # Or just fallback to 'openai' (gpt-4o-mini equivalent) which is most reliable on their free tier.
    
    url = "https://text.pollinations.ai/openai"
    headers = {"Content-Type": "application/json"}
    
    payload = {
        "messages": [{"role": m.role, "content": m.content} for m in messages],
        "seed": 42,
        "model": target_model, # Pollinations might ignore this on /openai endpoint but worth sending
        "jsonMode": True # Hint for JSON
    }

    async with httpx.AsyncClient(headers=headers, timeout=120.0) as client:
        try:
            resp = await client.post(url, json=payload)
            if resp.status_code != 200:
                logger.error(f"[FreeLLM] Pollinations Error Status: {resp.status_code} Body: {resp.text}")
                raise HTTPException(status_code=resp.status_code, detail=f"Pollinations Error: {resp.text}")
            
            logger.info(f"[FreeLLM] Raw Pollinations Response: {resp.text[:500]}...") # Log 500 chars

            # Extract content
            try:
                response_json = resp.json()
                logger.info(f"[FreeLLM] Full Response JSON: {json.dumps(response_json, ensure_ascii=False)[:1000]}") # Log structure

                if isinstance(response_json, str):
                    content = response_json
                else:
                    # Handle case where content might be None (common in reasoning models)
                    msg_obj = response_json.get("choices", [{}])[0].get("message", {})
                    content = msg_obj.get("content") or "" 
                    reasoning = msg_obj.get("reasoning_content")

                    if not content and reasoning:
                        logger.warning("[FreeLLM] ⚠️ Model returned only reasoning content, no final answer!")
                        # Optional: Fallback to reasoning if desperate? No, formatting will be wrong.
            except Exception as e:
                logger.error(f"[FreeLLM] JSON Parse/Extract Error: {e}")
                content = resp.text
                
            # Construct Standard OpenAI ChatCompletion Object
            return {
                "id": "chatcmpl-pollinations-static",
                "object": "chat.completion",
                "created": int(time.time()),
                "model": model,
                "choices": [{
                    "index": 0,
                    "message": {
                        "role": "assistant",
                        "content": content
                    },
                    "finish_reason": "stop"
                }],
                "usage": {
                    "prompt_tokens": 0,
                    "completion_tokens": 0,
                    "total_tokens": 0
                }
            }
        except Exception as e:
            logger.error(f"[FreeLLM] Non-streaming error: {e}")
            raise HTTPException(status_code=500, detail=str(e))
