"""Memory Router."""

import logging
import re
from typing import Any, Optional

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel

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


def _serialize_value(value: Any) -> Any:
    if isinstance(value, (str, int, float, bool, list, dict, type(None))):
        return value
    return str(value)


def _serialize_rows(rows: Any) -> list[dict[str, Any]]:
    if not rows:
        return []

    serialized: list[dict[str, Any]] = []
    for record in rows:
        if hasattr(record, "keys"):
            row = {key: _serialize_value(record[key]) for key in record.keys()}
        elif isinstance(record, dict):
            row = {key: _serialize_value(value) for key, value in record.items()}
        else:
            row = {"value": _serialize_value(record)}
        serialized.append(row)
    return serialized


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


async def _query_memory(memory_service: Any, sql: str, params: dict | None = None) -> list[dict[str, Any]]:
    rows = await memory_service.driver.query(sql, params or {})
    return _serialize_rows(rows)


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


@router.get("/inspection")
async def inspect_memory(
    character_id: Optional[str] = None,
    memory_service=Depends(get_memory_service),
    context_resolver=Depends(get_companion_context_resolver),
):
    memory_service = _require_memory(memory_service)

    try:
        cid = context_resolver.resolve(character_id=character_id).character_id.lower()
        history = await _query_memory(
            memory_service,
            "SELECT * FROM conversation_log WHERE character_id = $cid ORDER BY created_at DESC LIMIT 100;",
            {"cid": cid},
        )
        facts = await _query_memory(
            memory_service,
            "SELECT * FROM episodic_memory WHERE character_id = $cid ORDER BY created_at DESC LIMIT 100;",
            {"cid": cid},
        )
        nodes = await _query_memory(
            memory_service,
            "SELECT * FROM knowledge_graph_nodes WHERE character_id = $cid LIMIT 200;",
            {"cid": cid},
        )
        edges = await _query_memory(
            memory_service,
            "SELECT * FROM knowledge_graph_edges WHERE character_id = $cid LIMIT 300;",
            {"cid": cid},
        )
        return {
            "status": "success",
            "history": history,
            "facts": facts,
            "user_facts": facts,
            "graph": {"nodes": nodes, "edges": edges},
        }
    except Exception as exc:
        logger.error("Memory inspection failed: %s", exc, exc_info=True)
        return {
            "status": "success",
            "history": [],
            "facts": [],
            "user_facts": [],
            "graph": {"nodes": [], "edges": []},
        }


@router.get("/inspection/status")
async def inspect_processing_status(
    character_id: Optional[str] = None,
    memory_service=Depends(get_memory_service),
    context_resolver=Depends(get_companion_context_resolver),
):
    memory_service = _require_memory(memory_service)

    try:
        cid = context_resolver.resolve(character_id=character_id).character_id.lower()
        conversations = await _query_memory(
            memory_service,
            "SELECT count(*) AS count FROM conversation_log WHERE character_id = $cid;",
            {"cid": cid},
        )
        unprocessed = await _query_memory(
            memory_service,
            "SELECT count(*) AS count FROM conversation_log WHERE character_id = $cid AND is_processed = false;",
            {"cid": cid},
        )
        facts = await _query_memory(
            memory_service,
            "SELECT count(*) AS count FROM episodic_memory WHERE character_id = $cid;",
            {"cid": cid},
        )

        def count(rows: list[dict[str, Any]]) -> int:
            if not rows:
                return 0
            return int(rows[0].get("total") or rows[0].get("count") or 0)

        pending_conversations = count(unprocessed)
        total_facts = count(facts)
        threshold = 20

        return {
            "status": "success",
            "conversations": {
                "unprocessed": pending_conversations,
                "total": count(conversations),
                "threshold": threshold,
                "progress_percent": min(100, int((pending_conversations / threshold) * 100)) if threshold else 0,
            },
            "facts": {
                "user": {"unconsolidated": 0, "total": total_facts, "threshold": threshold, "progress_percent": 0},
                "character": {"unconsolidated": 0, "total": total_facts, "threshold": threshold, "progress_percent": 0},
            },
        }
    except Exception as exc:
        logger.error("Memory processing status failed: %s", exc, exc_info=True)
        return {
            "status": "success",
            "conversations": {"unprocessed": 0, "total": 0, "threshold": 20, "progress_percent": 0},
            "facts": {
                "user": {"unconsolidated": 0, "total": 0, "threshold": 20, "progress_percent": 0},
                "character": {"unconsolidated": 0, "total": 0, "threshold": 20, "progress_percent": 0},
            },
        }


@router.get("/inspection/tables")
async def inspect_tables():
    return {
        "tables": [
            {"name": "episodic_memory", "info": "Long-term episodic memories"},
            {"name": "conversation_log", "info": "Raw conversation history"},
            {"name": "knowledge_facts", "info": "Crystallized knowledge facts"},
            {"name": "knowledge_graph_nodes", "info": "Graph nodes"},
            {"name": "knowledge_graph_edges", "info": "Graph edges"},
            {"name": "user_profile", "info": "User profiles"},
            {"name": "character_profile", "info": "Character active profiles"},
        ]
    }


@router.get("/inspection/table/{table_name}")
async def inspect_table(
    table_name: str,
    limit: int = 50,
    character_id: Optional[str] = None,
    memory_service=Depends(get_memory_service),
):
    memory_service = _require_memory(memory_service)
    try:
        qb = memory_service.driver.get_query_builder()
        where_clause = {"character_id": character_id} if character_id else None
        query, params = qb.select(table_name, where=where_clause, limit=limit)
        rows = await memory_service.driver.query(query, params)
        return {"status": "success", "data": _serialize_rows(rows)}
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
):
    memory_service = _require_memory(memory_service)
    normalized_query = request.query.strip().upper()

    if ";" in normalized_query:
        raise HTTPException(400, "Multiple statements are not allowed.")

    forbidden_pattern = r"\b(DELETE|UPDATE|INSERT|CREATE|DROP|ALTER|GRANT|REVOKE|TRUNCATE|REPLACE)\b"
    if re.search(forbidden_pattern, normalized_query):
        raise HTTPException(403, "Only SELECT queries are allowed.")

    if not normalized_query.startswith("SELECT"):
        raise HTTPException(400, "Query must start with SELECT.")

    try:
        rows = await memory_service.driver.query(request.query)
        return {"status": "success", "result": _serialize_rows(rows)}
    except Exception as exc:
        logger.error("Memory inspection query failed: %s", exc, exc_info=True)
        return {"status": "error", "detail": str(exc)}


@router.delete("/inspection/record/{table_name}/{record_safe_id}")
async def delete_inspection_record(
    table_name: str,
    record_safe_id: str,
    memory_service=Depends(get_memory_service),
):
    memory_service = _require_memory(memory_service)
    if not table_name.replace("_", "").isalnum():
        raise HTTPException(400, "Invalid table name")

    allowed_delete = {
        "episodic_memory",
        "conversation_log",
        "knowledge_facts",
        "knowledge_graph_edges",
        "knowledge_graph_nodes",
    }
    if table_name not in allowed_delete:
        raise HTTPException(403, f"Deletion not allowed for table '{table_name}'")

    try:
        await memory_service.driver.delete(table_name, record_safe_id)
        return {"status": "success", "id": record_safe_id}
    except Exception as exc:
        logger.error("Memory inspection delete failed: %s", exc, exc_info=True)
        raise HTTPException(500, str(exc))


@router.post("/inspection/record/{table_name}/new")
async def create_inspection_record(
    table_name: str,
    request: InspectionRecordRequest,
    memory_service=Depends(get_memory_service),
):
    memory_service = _require_memory(memory_service)
    if table_name not in {"episodic_memory", "conversation_log", "knowledge_facts", "user_profile"}:
        raise HTTPException(403, "Creation restricted for this table.")

    try:
        new_id = await memory_service.driver.create(table_name, request.data)
        return {"status": "success", "id": new_id}
    except Exception as exc:
        logger.error("Memory inspection create failed: %s", exc, exc_info=True)
        raise HTTPException(500, str(exc))


@router.put("/inspection/record/{table_name}/{record_safe_id}")
async def update_inspection_record(
    table_name: str,
    record_safe_id: str,
    request: InspectionRecordRequest,
    memory_service=Depends(get_memory_service),
):
    memory_service = _require_memory(memory_service)
    if table_name not in {"episodic_memory", "conversation_log", "knowledge_facts", "user_profile", "character_profile"}:
        raise HTTPException(403, "Update restricted to content tables.")

    try:
        safe_data = request.data.copy()
        for key in ["id", "created_at", "uuid"]:
            safe_data.pop(key, None)
        await memory_service.driver.update(table_name, record_safe_id, safe_data)
        return {"status": "success"}
    except Exception as exc:
        logger.error("Memory inspection update failed: %s", exc, exc_info=True)
        raise HTTPException(500, str(exc))
