
"""
Admin Router
Safe replacements for deleted Debug endpoints.
Provides restricted access to the active memory store for frontend management tools.
"""
import logging
import re
from typing import Dict, Optional, Any
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from routers.deps import get_memory_service

logger = logging.getLogger("AdminRouter")

router = APIRouter(prefix="/admin", tags=["Admin"])


def _require_memory_system(memory_system):
    if not memory_system:
        raise HTTPException(status_code=503, detail="Memory service unavailable")
    if not getattr(memory_system, "available", True):
        detail = getattr(memory_system, "degraded_reason", None) or "Memory backend unavailable"
        raise HTTPException(status_code=503, detail=detail)
    return memory_system


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

# --- Schemas ---

class SafeQueryRequest(BaseModel):
    query: str

class UpdateRecordRequest(BaseModel):
    # Dynamic dict for updates
    data: Dict[str, Any]



# --- Endpoints ---

@router.get("/tables")
async def get_tables():
    """List allowed tables for inspection."""
    # White-list to prevent system table leak
    ALLOWED_TABLES = [
        {"name": "episodic_memory", "info": "Long-term episodic memories"},
        {"name": "conversation_log", "info": "Raw conversation history"},
        {"name": "knowledge_facts", "info": "Crystallized knowledge facts"},
        {"name": "knowledge_graph_nodes", "info": "Graph Nodes"},
        {"name": "knowledge_graph_edges", "info": "Graph Edges"},
        {"name": "user_profile", "info": "User profiles"},
        {"name": "character_profile", "info": "Character active profiles"}
    ]
    return {"tables": ALLOWED_TABLES}



@router.get("/table/{table_name}")
async def get_table_data(
    table_name: str,
    limit: int = 50,
    character_id: Optional[str] = None,
    memory_system=Depends(get_memory_service),
):
    """Get data from a table (Safe Read via QueryBuilder)."""
    try:
        memory_system = _require_memory_system(memory_system)
        # [Refactored] Use Dynamic QueryBuilder from Driver
        qb = memory_system.driver.get_query_builder()
        
        # [Phase 12] Use SafeQueryBuilder
        # This prevents injections via table_name or character_id construction
        where_clause = {"character_id": character_id} if character_id else None
        
        query, params = qb.select(table_name, where=where_clause, limit=limit)
        
        logger.info(f"[Admin] Reading table {table_name} (Safe): {query} | {params}")
        
        response = await memory_system.driver.query(query, params)
        return {"status": "success", "data": _serialize_rows(response)}

    except Exception as e:
        logger.error(f"[Admin] Read Error: {e}", exc_info=True)
        return {"status": "error", "data": [], "detail": str(e)}

@router.post("/query")
async def safe_query(request: SafeQueryRequest, memory_system=Depends(get_memory_service)):
    """Execute a Safe SELECT Query."""
    memory_system = _require_memory_system(memory_system)
    q = request.query.strip().upper()
    
    # 1. Security: Prevent Multiple Statements
    if ";" in q:
         raise HTTPException(400, "Multiple statements (semicolon) are not allowed.")

    # 2. Security: Block Dangerous Keywords (Word Boundaries)
    # Match standalone keywords only (e.g. DELETE, DROP) to avoid blocking columns like 'UPDATE_TIME'
    # Keywords: DELETE, UPDATE, INSERT, CREATE, DROP, ALTER, GRANT, REVOKE, TRUNCATE, REPLACE
    forbidden_pattern = r'\b(DELETE|UPDATE|INSERT|CREATE|DROP|ALTER|GRANT|REVOKE|TRUNCATE|REPLACE)\b'
    
    if re.search(forbidden_pattern, q):
        raise HTTPException(403, "Only SELECT queries are allowed. Modification keywords detected.")

    if not q.startswith("SELECT"):
         raise HTTPException(400, "Query must start with SELECT.")
         
    try:
        logger.info(f"[Admin] Executing Safe Query: {request.query}")
        results = await memory_system.driver.query(request.query)
        return {"status": "success", "result": _serialize_rows(results)}
    except Exception as e:
        logger.error(f"[Admin] Query Error: {e}", exc_info=True)
        return {"status": "error", "detail": str(e)}

@router.delete("/record/{table_name}/{record_safe_id}")
async def delete_record(table_name: str, record_safe_id: str, memory_system=Depends(get_memory_service)):
    """Safe Delete Record."""
    memory_system = _require_memory_system(memory_system)
    # Validate Inputs
    if not table_name.replace("_", "").isalnum():
         raise HTTPException(400, "Invalid table name")
    
    # Allow deletion?
    ALLOWED_DELETE = ["episodic_memory", "conversation_log", "knowledge_facts", "knowledge_graph_edges", "knowledge_graph_nodes"]
    if table_name not in ALLOWED_DELETE:
        raise HTTPException(403, f"Deletion not allowed for table '{table_name}'")

    try:
        logger.info(f"[Admin] Deleting {record_safe_id}")
        await memory_system.driver.delete(table_name, record_safe_id)
        return {"status": "success", "id": record_safe_id}
    except Exception as e:
        logger.error(f"[Admin] Delete Error: {e}", exc_info=True)
        raise HTTPException(500, str(e))

@router.post("/record/{table_name}/new")
async def create_record(table_name: str, request: UpdateRecordRequest, memory_system=Depends(get_memory_service)):
    """Create New Record."""
    memory_system = _require_memory_system(memory_system)
    if table_name not in ["episodic_memory", "conversation_log", "knowledge_facts", "user_profile"]:
         raise HTTPException(403, "Creation restricted for this table.")
         
    try:
        logger.info(f"[Admin] Creating in {table_name}: {request.data.keys()}")
        # Driver.create(table, data) -> returns ID string
        new_id = await memory_system.driver.create(table_name, request.data)
        return {"status": "success", "id": new_id}
    except Exception as e:
        logger.error(f"[Admin] Create Error: {e}", exc_info=True)
        raise HTTPException(500, str(e))

@router.put("/record/{table_name}/{record_safe_id}")
async def update_record(table_name: str, record_safe_id: str, request: UpdateRecordRequest, memory_system=Depends(get_memory_service)):
    """Safe Update (Merge)."""
    memory_system = _require_memory_system(memory_system)
    if table_name not in ["episodic_memory", "conversation_log", "knowledge_facts", "user_profile", "character_profile"]:
         raise HTTPException(403, "Update restricted to content tables.")

    try:
        # Remove protected fields
        safe_data = request.data.copy()
        for k in ["id", "created_at", "uuid"]:
            if k in safe_data: del safe_data[k]
            
        logger.info(f"[Admin] Updating {record_safe_id} with {safe_data.keys()}")
        await memory_system.driver.update(table_name, record_safe_id, safe_data)
        return {"status": "success"}
    except Exception as e:
         raise HTTPException(500, str(e))


# =============================================================================
# Debug / Monitoring Endpoints
# =============================================================================

@router.get("/debug/errors")
async def get_error_stats():
    """Get error monitoring statistics."""
    from services.error_monitor import get_error_monitor
    monitor = get_error_monitor()
    return {
        "stats": monitor.get_stats(),
        "recent_errors": monitor.get_recent_errors(limit=20)
    }


@router.get("/debug/errors/{error_type}")
async def get_errors_by_type(error_type: str, limit: int = 10):
    """Get recent errors of a specific type."""
    from services.error_monitor import get_error_monitor
    monitor = get_error_monitor()
    return {
        "error_type": error_type,
        "errors": monitor.get_errors_by_type(error_type, limit)
    }


@router.get("/debug/system")
async def get_system_stats():
    """Get system-wide statistics."""
    from services.error_monitor import get_error_monitor
    from services.http_client import get_http_stats
    from core.events.bus import get_event_bus
    
    stats = {
        "error_monitor": get_error_monitor().get_stats(),
        "http_client": get_http_stats(),
    }
    
    # EventBus stats if available
    bus = get_event_bus()
    if hasattr(bus, 'get_stats'):
        stats["event_bus"] = bus.get_stats()
    
    return stats

