"""Memory Router."""

import logging
from typing import Any, Optional

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel

from routers.deps import (
    get_companion_interaction_recorder,
    get_companion_context_resolver,
    get_memory_service,
    get_session_manager,
)
from schemas.requests import AddMemoryRequest, SearchRequest
from services.companion.interaction import CompanionInteraction

logger = logging.getLogger("MemoryRouter")

router = APIRouter(tags=["Memory"])


def _require_memory(memory_service: Any):
    if not memory_service:
        raise HTTPException(status_code=503, detail="Memory service unavailable")
    return memory_service


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
    if not memory_service.encoder:
        raise HTTPException(status_code=500, detail="Embedding encoder not ready")

    query_vec = memory_service.encoder(query)
    if hasattr(query_vec, "tolist"):
        query_vec = query_vec.tolist()
    return query_vec


@router.post("/add")
async def add_memory(
    request: AddMemoryRequest,
    memory_service=Depends(get_memory_service),
    context_resolver=Depends(get_companion_context_resolver),
    interaction_recorder=Depends(get_companion_interaction_recorder),
):
    memory_service = _require_memory(memory_service)
    context = context_resolver.resolve(user_id=request.user_id, character_id=request.character_id)

    user_input = ""
    ai_response = ""
    for message in reversed(request.messages):
        if message.role == "assistant" and not ai_response:
            ai_response = message.content
        elif message.role == "user" and not user_input:
            user_input = message.content

    if not user_input and not ai_response:
        return {"status": "skipped", "reason": "Empty interaction"}

    try:
        result = await interaction_recorder.record(
            CompanionInteraction(
                companion_context=context,
                user_message=user_input,
                assistant_message=ai_response,
                user_name=request.user_name,
                companion_name=request.companion_name,
                save_history=False,
                log_memory=True,
                notify_soul_driver=False,
                strict=True,
            )
        )

        return {
            "status": "success",
            "id": str(result.memory_log_id or ""),
            "storage": memory_service.driver_id,
        }
    except Exception as exc:
        logger.error("Failed to add memory: %s", exc, exc_info=True)
        raise HTTPException(status_code=500, detail=str(exc))


@router.post("/search")
async def search_memory(
    request: SearchRequest,
    memory_service=Depends(get_memory_service),
    context_resolver=Depends(get_companion_context_resolver),
):
    memory_service = _require_memory(memory_service)
    context = context_resolver.resolve(user_id=request.user_id, character_id=request.character_id)

    try:
        query_vec = _encode_query(memory_service, request.query)
        results = await memory_service.search_episodic(
            query_vec,
            context,
            limit=request.limit,
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
    context_resolver=Depends(get_companion_context_resolver),
):
    memory_service = _require_memory(memory_service)
    context = context_resolver.resolve(user_id=request.user_id, character_id=request.character_id)

    try:
        query_vec = _encode_query(memory_service, request.query)
        results = await memory_service.search_episodic_hybrid(
            query=request.query,
            query_vector=query_vec,
            context=context,
            limit=request.limit,
        )
        logger.info("Memory hybrid search '%s' -> %s hits", request.query, len(results))
        return _serialize_memory_rows(results, "hybrid_score")
    except HTTPException:
        raise
    except Exception as exc:
        logger.error("Failed to hybrid-search memory: %s", exc, exc_info=True)
        raise HTTPException(status_code=500, detail=str(exc))


class ClearContextRequest(BaseModel):
    user_id: Optional[str] = None
    character_id: Optional[str] = None


@router.post("/context/clear")
async def clear_context(
    request: ClearContextRequest,
    session_manager=Depends(get_session_manager),
    context_resolver=Depends(get_companion_context_resolver),
):
    try:
        context = context_resolver.resolve(
            user_id=request.user_id,
            character_id=request.character_id,
        )

        await session_manager.clear_history(context)

        from routers.gateway import gateway_service

        await gateway_service.publish_session_reset(source="api.clear_context")
        return {"status": "success", "message": "Short-term context cleared"}
    except Exception as exc:
        logger.error("Failed to clear context: %s", exc, exc_info=True)
        raise HTTPException(status_code=500, detail=str(exc))


@router.get("/all")
async def get_all_memories(
    character_id: Optional[str] = None,
    memory_service=Depends(get_memory_service),
    context_resolver=Depends(get_companion_context_resolver),
):
    memory_service = _require_memory(memory_service)
    context = context_resolver.resolve(character_id=character_id)

    try:
        results = await memory_service.get_all_conversations(context)
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
    character_id: Optional[str] = None,
    limit: int = 3,
    memory_service=Depends(get_memory_service),
    context_resolver=Depends(get_companion_context_resolver),
):
    memory_service = _require_memory(memory_service)
    context = context_resolver.resolve(character_id=character_id)

    try:
        results = await memory_service.get_inspiration(context, limit=limit)
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
