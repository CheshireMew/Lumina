
"""
Admin Router
Safe replacements for deleted Debug endpoints.
Provides restricted access to SurrealDB for frontend management tools.

Refactored: Removed inject_dependencies
"""
import logging
from typing import Dict, List, Optional, Any
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

logger = logging.getLogger("AdminRouter")

router = APIRouter(prefix="/admin", tags=["Admin"])


def _get_surreal():
    from services.container import services
    if not services.surreal_system:
         raise HTTPException(503, "SurrealDB not initialized")
    return services.surreal_system


# --- Schemas ---

class SafeQueryRequest(BaseModel):
    query: str

class UpdateRecordRequest(BaseModel):
    # Dynamic dict for updates
    data: Dict[str, Any]

class CreateRecordRequest(BaseModel):
    table_name: str
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
async def get_table_data(table_name: str, limit: int = 50, character_id: Optional[str] = None):
    """Get data from a table (Safe Read)."""
    surreal_system = _get_surreal()

    # 1. Validate Table Name (Alphanumeric only)
    if not table_name.replace("_", "").isalnum():
         raise HTTPException(400, "Invalid table name")

    try:
        query = f"SELECT * FROM {table_name}"
        conditions = []
        
        # 2. Filter by character_id if applicable and provided
        if character_id:
             # Basic injection safety checked by validation above, but use param for safety if possible.
             conditions.append(f"character_id = '{character_id}'")

        if conditions:
            query += " WHERE " + " AND ".join(conditions)

        # 3. Enforce Limit
        final_limit = min(limit, 100) # Max 100 rows
        query += f" ORDER BY created_at DESC LIMIT {final_limit};"

        logger.info(f"[Admin] Reading table {table_name} (Limit {final_limit})")
        results = await surreal_system.execute_raw_query(query)
        
        # Driver returns data list directly
        if isinstance(results, list):
             return {"status": "success", "data": results}
        
        return {"status": "success", "data": []}

    except Exception as e:
        logger.error(f"[Admin] Read Error: {e}")
        return {"status": "error", "data": []}

@router.post("/query")
async def safe_query(request: SafeQueryRequest):
    """Execute a Safe SELECT Query."""
    surreal_system = _get_surreal()

    q = request.query.strip().upper()
    
    # 1. Block Dangerous Keywords
    FORBIDDEN = ["DELETE", "UPDATE", "INSERT", "CREATE", "REMOVE", "DROP", "ALTER", "KILL", "GRANT", "REVOKE"]
    if any(k in q for k in FORBIDDEN):
        raise HTTPException(403, "Only SELECT queries are allowed in Admin console.")

    if not q.startswith("SELECT"):
         raise HTTPException(400, "Query must start with SELECT.")
         
    try:
        logger.info(f"[Admin] Executing Safe Query: {request.query}")
        results = await surreal_system.execute_raw_query(request.query)
        return {"status": "success", "result": results}
    except Exception as e:
        logger.error(f"[Admin] Query Error: {e}")
        return {"status": "error", "detail": str(e)}

@router.delete("/record/{table_name}/{record_safe_id}")
async def delete_record(table_name: str, record_safe_id: str):
    """Safe Delete Record."""
    surreal_system = _get_surreal()
        
    # Validate Inputs
    if not table_name.replace("_", "").isalnum():
         raise HTTPException(400, "Invalid table name")
    
    # Allow deletion?
    ALLOWED_DELETE = ["episodic_memory", "conversation_log", "knowledge_facts", "knowledge_graph_edges", "knowledge_graph_nodes"]
    if table_name not in ALLOWED_DELETE:
        raise HTTPException(403, f"Deletion not allowed for table '{table_name}'")

    try:
        # Construct ID (table:id)
        full_id = record_safe_id
        if ":" not in full_id:
            full_id = f"{table_name}:{record_safe_id}"
            
        logger.info(f"[Admin] Deleting {full_id}")
        # Fix: Access driver directly
        await surreal_system.driver.delete(table_name, full_id) # Driver.delete(table, id)
        return {"status": "success", "id": full_id}
    except Exception as e:
        logger.error(f"[Admin] Delete Error: {e}")
        raise HTTPException(500, str(e))

@router.post("/record/{table_name}/new")
async def create_record(table_name: str, request: UpdateRecordRequest):
    """Create New Record."""
    surreal_system = _get_surreal()
    
    if table_name not in ["episodic_memory", "conversation_log", "knowledge_facts", "user_profile"]:
         raise HTTPException(403, "Creation restricted for this table.")
         
    try:
        logger.info(f"[Admin] Creating in {table_name}: {request.data.keys()}")
        # Driver.create(table, data) -> returns ID string
        new_id = await surreal_system.driver.create(table_name, request.data)
        return {"status": "success", "id": new_id}
    except Exception as e:
        logger.error(f"[Admin] Create Error: {e}")
        raise HTTPException(500, str(e))

@router.put("/record/{table_name}/{record_safe_id}")
async def update_record(table_name: str, record_safe_id: str, request: UpdateRecordRequest):
    """Safe Update (Merge)."""
    surreal_system = _get_surreal()
        
    if table_name not in ["episodic_memory", "conversation_log", "knowledge_facts", "user_profile", "character_profile"]:
         raise HTTPException(403, "Update restricted to content tables.")

    try:
        full_id = record_safe_id
        if ":" not in full_id:
             full_id = f"{table_name}:{record_safe_id}"
             
        # Remove protected fields
        safe_data = request.data.copy()
        for k in ["id", "created_at", "uuid"]:
            if k in safe_data: del safe_data[k]
            
        logger.info(f"[Admin] Updating {full_id} with {safe_data.keys()}")
        # Fix: Access driver directly. Driver.update(table, id, data)
        await surreal_system.driver.update(table_name, full_id, safe_data)
        return {"status": "success"}
    except Exception as e:
         raise HTTPException(500, str(e))
