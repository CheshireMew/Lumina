"""Memory Router."""

import logging
from typing import Any, Optional

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel

from routers.deps import (
    get_llm_service,
    get_memory_service,
    get_optional_soul_service,
    get_session_manager,
)
from schemas.requests import AddMemoryRequest, SearchRequest

logger = logging.getLogger("MemoryRouter")

router = APIRouter(tags=["Memory"])


def _require_memory(memory_service: Any):
    if not memory_service:
        raise HTTPException(status_code=503, detail="Memory service unavailable")
    if not getattr(memory_service, "available", True):
        detail = getattr(memory_service, "degraded_reason", None) or "Memory backend unavailable"
        raise HTTPException(status_code=503, detail=detail)
    return memory_service


def _resolve_character_id(memory_service: Any, character_id: Optional[str]) -> str:
    if character_id:
        return character_id
    if memory_service and hasattr(memory_service, "character_id"):
        return memory_service.character_id
    return "default"


def _serialize_value(value: Any) -> Any:
    if isinstance(value, (str, int, float, bool, list, dict, type(None))):
        return value
    return str(value)


def _serialize_memory_rows(rows: list[dict[str, Any]], score_key: str) -> list[dict[str, Any]]:
    serialized: list[dict[str, Any]] = []
    for row in rows:
        serialized.append(
            {
                "id": str(row.get("id", "")),
                "content": row.get("content", row.get("narrative", "")),
                "score": _serialize_value(row.get(score_key, 0)),
                "created_at": _serialize_value(row.get("created_at", "")),
                "importance": _serialize_value(row.get("importance", 1)),
            }
        )
    return serialized


def _encode_query(memory_service: Any, query: str) -> list[float]:
    encoder = getattr(memory_service, "encoder", None)
    if not encoder:
        raise HTTPException(status_code=500, detail="Embedding encoder not ready")

    query_vec = encoder(query)
    if hasattr(query_vec, "tolist"):
        query_vec = query_vec.tolist()
    return query_vec


@router.post("/add")
async def add_memory(
    request: AddMemoryRequest,
    memory_service=Depends(get_memory_service),
    soul_client=Depends(get_optional_soul_service),
):
    memory_service = _require_memory(memory_service)
    character_id = _resolve_character_id(memory_service, request.character_id)

    user_input = ""
    ai_response = ""
    for message in reversed(request.messages):
        if message.role == "assistant" and not ai_response:
            ai_response = message.content
        elif message.role == "user" and not user_input:
            user_input = message.content

    if not user_input and not ai_response:
        return {"status": "skipped", "reason": "Empty interaction"}

    narrative = f"{request.user_name}: {user_input or '(Silence)'}\n{request.character_name}: {ai_response}"

    try:
        log_id = await memory_service.log_conversation(
            character_id=character_id,
            narrative=narrative,
        )

        if soul_client:
            soul_client.update_last_interaction()

        driver_id = getattr(getattr(memory_service, "driver", None), "id", "memory")
        return {"status": "success", "id": str(log_id), "storage": driver_id}
    except Exception as exc:
        logger.error("Failed to add memory: %s", exc, exc_info=True)
        raise HTTPException(status_code=500, detail=str(exc))


@router.post("/search")
async def search_memory(
    request: SearchRequest,
    memory_service=Depends(get_memory_service),
    llm_manager=Depends(get_llm_service),
):
    memory_service = _require_memory(memory_service)
    character_id = _resolve_character_id(memory_service, request.character_id)

    try:
        query_vec = _encode_query(memory_service, request.query)
        target_table = "episodic_memory"
        final_limit = request.limit

        route = llm_manager.get_route("memory")
        if route and route.provider_id == "free_tier":
            target_table = "conversation_log"
            final_limit = min(request.limit, 3)

        results = await memory_service.search(
            query_vec,
            character_id,
            limit=final_limit,
            target_table=target_table,
        )
        logger.info("Memory search '%s' -> %s hits", request.query, len(results))
        return _serialize_memory_rows(results, "score")
    except HTTPException:
        raise
    except Exception as exc:
        logger.error("Failed to search memory: %s", exc, exc_info=True)
        raise HTTPException(status_code=500, detail=str(exc))


@router.post("/search/hybrid")
async def search_memory_hybrid(
    request: SearchRequest,
    memory_service=Depends(get_memory_service),
    llm_manager=Depends(get_llm_service),
):
    memory_service = _require_memory(memory_service)
    character_id = _resolve_character_id(memory_service, request.character_id)

    try:
        query_vec = _encode_query(memory_service, request.query)
        target_table = "episodic_memory"
        final_limit = request.limit

        route = llm_manager.get_route("memory")
        if route and route.provider_id == "free_tier":
            target_table = "conversation_log"
            final_limit = min(request.limit, 3)

        results = await memory_service.search_hybrid(
            query=request.query,
            query_vector=query_vec,
            character_id=character_id,
            limit=final_limit,
            target_table=target_table,
        )
        logger.info("Memory hybrid search '%s' -> %s hits", request.query, len(results))
        return _serialize_memory_rows(results, "hybrid_score")
    except HTTPException:
        raise
    except Exception as exc:
        logger.error("Failed to hybrid-search memory: %s", exc, exc_info=True)
        raise HTTPException(status_code=500, detail=str(exc))


class ClearContextRequest(BaseModel):
    user_id: Optional[str] = "default_user"
    character_id: Optional[str] = "hiyori"


@router.post("/context/clear")
async def clear_context(request: ClearContextRequest, session_manager=Depends(get_session_manager)):
    try:
        character_id = request.character_id or "hiyori"
        user_id = request.user_id or "default_user"

        await session_manager.clear_history(user_id, character_id)

        from routers.gateway import gateway_service

        await gateway_service.start_new_session(source="api.clear_context")
        return {"status": "success", "message": "Short-term context cleared"}
    except Exception as exc:
        logger.error("Failed to clear context: %s", exc, exc_info=True)
        raise HTTPException(status_code=500, detail=str(exc))


@router.get("/all")
async def get_all_memories(
    character_id: str = "hiyori",
    memory_service=Depends(get_memory_service),
):
    memory_service = _require_memory(memory_service)

    try:
        results = await memory_service.get_all_conversations(character_id=character_id)
        memories = []
        for row in results:
            memories.append(
                {
                    "id": str(row.get("id", "")),
                    "content": row.get("content", row.get("narrative", "")),
                    "role": row.get("role", "user"),
                    "created_at": _serialize_value(row.get("created_at", "")),
                }
            )
        return memories
    except Exception as exc:
        logger.error("Failed to fetch memories: %s", exc, exc_info=True)
        raise HTTPException(status_code=500, detail=str(exc))


@router.get("/inspiration")
async def get_inspiration(
    character_id: str = "hiyori",
    limit: int = 3,
    memory_service=Depends(get_memory_service),
):
    memory_service = _require_memory(memory_service)

    try:
        results = await memory_service.get_inspiration(character_id=character_id, limit=limit)
        return [
            {
                "id": str(row.get("id", "")),
                "content": row.get("content", row.get("narrative", "")),
                "created_at": _serialize_value(row.get("created_at", "")),
            }
            for row in results
        ]
    except Exception as exc:
        logger.error("Failed to fetch inspiration: %s", exc, exc_info=True)
        raise HTTPException(status_code=500, detail=str(exc))
