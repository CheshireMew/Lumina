"""Memory Router."""

import logging
from typing import Any, Optional

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel

from memory.inspection import (
    MemoryInspectionService,
    list_inspection_tables,
    serialize_memory_rows,
    serialize_value,
)
from routers.deps import (
    get_companion_interaction_recorder,
    get_companion_context_resolver,
    get_companion_runtime,
    get_memory_service,
)
from schemas.requests import AddMemoryRequest, SearchRequest
from services.companion.interaction import CompanionInteraction

logger = logging.getLogger("MemoryRouter")

router = APIRouter(tags=["Memory"])


def _require_memory(memory_service: Any):
    if not memory_service:
        raise HTTPException(status_code=503, detail="Memory service unavailable")
    return memory_service


def _encode_query(memory_service: Any, query: str) -> list[float]:
    if not memory_service.encoder:
        raise HTTPException(status_code=500, detail="Embedding encoder not ready")

    query_vec = memory_service.encoder(query)
    if hasattr(query_vec, "tolist"):
        query_vec = query_vec.tolist()
    return query_vec


def _inspection_service(memory_service: Any, context_resolver: Any) -> MemoryInspectionService:
    return MemoryInspectionService(_require_memory(memory_service), context_resolver)


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
            "id": str(result.turn_id or ""),
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
        results = await memory_service.search_memory_items(
            query_vec,
            context,
            limit=request.limit,
        )
        logger.info("Memory search '%s' -> %s hits", request.query, len(results))
        return serialize_memory_rows(results, "score")
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
        results = await memory_service.search_memory_items_hybrid(
            query=request.query,
            query_vector=query_vec,
            context=context,
            limit=request.limit,
        )
        logger.info("Memory hybrid search '%s' -> %s hits", request.query, len(results))
        return serialize_memory_rows(results, "hybrid_score")
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
    companion_runtime=Depends(get_companion_runtime),
):
    try:
        from core.protocol import EventPacket, EventType

        await companion_runtime.reset_session(
            EventPacket(
                session_id=0,
                type=EventType.CONTROL_SESSION,
                source="api.clear_context",
                payload={
                    "action": "reset",
                    "user_id": request.user_id,
                    "character_id": request.character_id,
                },
            )
        )
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
        results = await memory_service.get_all_turns(context)
        memories = []
        for row in results:
            memories.append(
                {
                    "id": str(row.get("id", "")),
                    "content": row.get("content", row.get("narrative", "")),
                    "role": row.get("role", "user"),
                    "created_at": serialize_value(row.get("created_at", "")),
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
                "created_at": serialize_value(row.get("created_at", "")),
            }
            for row in results
        ]
    except Exception as exc:
        logger.error("Failed to fetch inspiration: %s", exc, exc_info=True)
        raise HTTPException(status_code=500, detail=str(exc))


@router.get("/inspection")
async def inspect_memory(
    character_id: Optional[str] = None,
    memory_service=Depends(get_memory_service),
    context_resolver=Depends(get_companion_context_resolver),
):
    try:
        return await _inspection_service(memory_service, context_resolver).overview(character_id)
    except Exception as exc:
        logger.error("Memory inspection failed: %s", exc, exc_info=True)
        return {
            "status": "success",
            "turns": [],
            "memories": [],
        }


@router.get("/inspection/status")
async def inspect_processing_status(
    character_id: Optional[str] = None,
    memory_service=Depends(get_memory_service),
    context_resolver=Depends(get_companion_context_resolver),
):
    try:
        return await _inspection_service(memory_service, context_resolver).processing_status(character_id)
    except Exception as exc:
        logger.error("Memory processing status failed: %s", exc, exc_info=True)
        return {
            "status": "success",
            "turns": {"unprocessed": 0, "total": 0, "threshold": 20, "progress_percent": 0},
            "memories": {
                "active": {"unconsolidated": 0, "total": 0, "threshold": 20, "progress_percent": 0},
            },
        }


@router.get("/inspection/tables")
async def inspect_tables():
    return list_inspection_tables()


@router.get("/inspection/table/{table_name}")
async def inspect_table(
    table_name: str,
    limit: int = 50,
    character_id: Optional[str] = None,
    memory_service=Depends(get_memory_service),
    context_resolver=Depends(get_companion_context_resolver),
):
    try:
        return await _inspection_service(memory_service, context_resolver).table_rows(
            table_name,
            limit=limit,
            character_id=character_id,
        )
    except Exception as exc:
        logger.error("Memory table inspection failed: %s", exc, exc_info=True)
        return {"status": "error", "data": [], "detail": str(exc)}


class InspectionQueryRequest(BaseModel):
    query: str


class InspectionRecordRequest(BaseModel):
    data: dict[str, Any]


@router.post("/inspection/query")
async def inspect_query(
    request: InspectionQueryRequest,
    memory_service=Depends(get_memory_service),
    context_resolver=Depends(get_companion_context_resolver),
):
    try:
        return await _inspection_service(memory_service, context_resolver).select_query(request.query)
    except PermissionError as exc:
        raise HTTPException(403, str(exc))
    except ValueError as exc:
        raise HTTPException(400, str(exc))
    except Exception as exc:
        logger.error("Memory inspection query failed: %s", exc, exc_info=True)
        return {"status": "error", "detail": str(exc)}


@router.delete("/inspection/record/{table_name}/{record_safe_id}")
async def delete_inspection_record(
    table_name: str,
    record_safe_id: str,
    memory_service=Depends(get_memory_service),
    context_resolver=Depends(get_companion_context_resolver),
):
    try:
        return await _inspection_service(memory_service, context_resolver).delete_record(table_name, record_safe_id)
    except PermissionError as exc:
        raise HTTPException(403, str(exc))
    except ValueError as exc:
        raise HTTPException(400, str(exc))
    except Exception as exc:
        logger.error("Memory inspection delete failed: %s", exc, exc_info=True)
        raise HTTPException(500, str(exc))


@router.post("/inspection/record/{table_name}/new")
async def create_inspection_record(
    table_name: str,
    request: InspectionRecordRequest,
    memory_service=Depends(get_memory_service),
    context_resolver=Depends(get_companion_context_resolver),
):
    try:
        return await _inspection_service(memory_service, context_resolver).create_record(table_name, request.data)
    except PermissionError as exc:
        raise HTTPException(403, str(exc))
    except ValueError as exc:
        raise HTTPException(400, str(exc))
    except Exception as exc:
        logger.error("Memory inspection create failed: %s", exc, exc_info=True)
        raise HTTPException(500, str(exc))


@router.put("/inspection/record/{table_name}/{record_safe_id}")
async def update_inspection_record(
    table_name: str,
    record_safe_id: str,
    request: InspectionRecordRequest,
    memory_service=Depends(get_memory_service),
    context_resolver=Depends(get_companion_context_resolver),
):
    try:
        return await _inspection_service(memory_service, context_resolver).update_record(
            table_name,
            record_safe_id,
            request.data,
        )
    except PermissionError as exc:
        raise HTTPException(403, str(exc))
    except ValueError as exc:
        raise HTTPException(400, str(exc))
    except Exception as exc:
        logger.error("Memory inspection update failed: %s", exc, exc_info=True)
        raise HTTPException(500, str(exc))
