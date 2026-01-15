"""
Debug Router
Includes: /debug/brain_dump, /debug/processing_status, /debug/surreal/*

Refactored: Removed inject_dependencies
"""
import os
import json
import logging
from typing import Dict, Optional
from pydantic import BaseModel
from fastapi import APIRouter, HTTPException
from core.protocol import EventPacket

logger = logging.getLogger("DebugRouter")

router = APIRouter(prefix="/debug", tags=["Debug"])


def _get_surreal():
    from services.container import services
    if not services.surreal_system:
         # raise HTTPException(503, "SurrealDB not initialized")
         return None
    return services.surreal_system

def _get_dreaming_service():
    from core.events.bus import get_event_bus
    bus = get_event_bus()
    return bus.get_service("dreaming_service") if bus else None

def _get_plugin_manager():
    from services.container import services
    return services.system_plugin_manager


@router.post("/plugins/{plugin_id}/reload")
async def reload_plugin(plugin_id: str):
    """Hot reload a system plugin"""
    system_plugin_manager = _get_plugin_manager()
    if not system_plugin_manager:
        raise HTTPException(status_code=503, detail="System Plugin Manager unavailable")
        
    try:
        success = system_plugin_manager.reload_plugin(plugin_id)
        if success:
             return {"status": "success", "message": f"Plugin {plugin_id} reloaded."}
        else:
             raise HTTPException(status_code=400, detail=f"Failed to reload {plugin_id}")
    except Exception as e:
        logger.error(f"[Debug] Reload error: {e}")
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/force_digest")
async def force_digest_memories():
    """Force Dreaming to digest all unprocessed memories"""
    dreaming_service = _get_dreaming_service()
    
    if not dreaming_service:
        raise HTTPException(status_code=503, detail="Dreaming service not available")
        
    try:
        logger.info("[Debug] Forcing dreaming cycle...")
        await dreaming_service.process_memories(batch_size=10)
        return {"status": "success", "message": "Dreaming cycle triggered"}
    except Exception as e:
        logger.error(f"[Debug] Dreaming error: {e}")
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/brain_dump")
async def brain_dump(character_id: str = "hiyori"):
    """
    Get complete snapshot of character memory.
    Returns: { facts: [], graph: {nodes: [], edges: []}, history: [] }
    """
    surreal_system = _get_surreal()
    
    if not surreal_system:
        return {"status": "error", "message": "SurrealDB not available"}
    
    try:
        
        # 1. Fetch all conversations from SurrealDB
        results = await surreal_system.get_all_conversations(character_id=character_id)
        
        # Format for frontend
        history = []
        for r in results:
            item = {
                "timestamp": r.get("created_at", ""),
                "content": r.get("text", ""),
                "role": r.get("role", "user")
            }
             # Parse "Name: Message" format if present (Migration legacy)
            content = r.get("text", "")
            if ": " in content:
                parts = content.split(": ", 1)
                item["name"] = parts[0]
                item["content"] = parts[1]
                
            history.append(item)

        return {
            "status": "success",
            "facts": [], # TODO: Implement Graph Fact Export from Surreal
            "user_facts": [],
            "graph": {"nodes": [], "edges": []}, # Use /debug/surreal/graph for this
            "history": history
        }
    except Exception as e:
        logger.error(f"[API] Brain Dump Error: {e}")
        return {
            "status": "error",
            "message": str(e),
            "facts": [],
            "graph": {"nodes": [], "edges": []},
            "history": []
        }


@router.get("/processing_status")
async def get_processing_status(character_id: str = "hiyori"):
    """Get real-time status of memory processing pipeline"""
    return {
        "status": "success",
        "conversations": {"unprocessed": 0, "total": 0},
        "facts": {"user": {"unconsolidated": 0, "total": 0}, "character": {"unconsolidated": 0, "total": 0}},
        "message": "Legacy processing status disabled."
    }


@router.post("/memory/merge_entities")
async def trigger_entity_merge():
    """Trigger manual entity duplicate merging based on aliases."""
    surreal_system = _get_surreal()
    if not surreal_system:
         raise HTTPException(status_code=503, detail="SurrealDB not available")
    
    try:
        metrics, logs = await surreal_system.merge_entity_duplicates()
        return {"status": "success", "metrics": metrics, "logs": logs}
    except Exception as e:
        logger.error(f"Merge failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# ==================== SurrealDB Debug Endpoints ====================

class SurrealAddRequest(BaseModel):
    content: str
    character_id: str
    user_id: str = "user_default"
    importance: int = 1
    emotion: Optional[str] = None


class SurrealSearchRequest(BaseModel):
    query: str
    character_id: str
    limit: int = 5


@router.post("/surreal/add", deprecated=True)
async def add_surreal_memory(request: SurrealAddRequest):
    """(Deprecated) Use /admin/record/{table}/new instead"""
    surreal_system = _get_surreal()
    
    if not surreal_system:
        raise HTTPException(status_code=503, detail="SurrealDB not available")
    
    # 鑾峰彇 encoder (Unified)
    encoder = surreal_system.encoder if surreal_system and hasattr(surreal_system, 'encoder') else None
    
    if not encoder:
         raise HTTPException(status_code=500, detail="Embedding encoder not available in SurrealSystem")

    try:
        # Encoder is lambda text->list
        embedding = encoder(request.content)
        
        fact_id = await surreal_system.add_memory(
            content=request.content,
            embedding=embedding,
            character_id=request.character_id,
            user_id=request.user_id,
            importance=request.importance,
            emotion=request.emotion
        )
        return {"status": "success", "id": fact_id}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/surreal/search", deprecated=True)
async def search_surreal_memory(request: SurrealSearchRequest):
    """(Deprecated) Use /memory/search instead"""
    surreal_system = _get_surreal()
    
    if not surreal_system:
        raise HTTPException(status_code=503, detail="SurrealDB not available")
    
    # Use Surreal encoder directy
    encoder = surreal_system.encoder
    if not encoder:
         raise HTTPException(status_code=500, detail="No active embedding model")

    try:
        embedding = encoder(request.query)
        results = await surreal_system.search(embedding, request.character_id, request.limit)
        return {"results": results}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# ==================== SurrealDB Visualization API ====================

class SurrealQueryRequest(BaseModel):
    query: str  # SurrealQL Query Statement


@router.get("/surreal/tables", deprecated=True)
async def get_surreal_tables():
    """(Deprecated) Use /admin/tables instead"""
    surreal_system = _get_surreal()
    
    if not surreal_system:
        raise HTTPException(status_code=503, detail="SurrealDB not available")
    
    try:
        if not surreal_system.db:
            await surreal_system.connect()
        
        result = await surreal_system.execute_raw_query("INFO FOR DB;")
        logger.info(f"[SurrealDB] INFO FOR DB raw result: {result}")
        
        # 瑙f瀽琛ㄤ俊鎭紙鏀寔澶氱鏍煎紡锛?
        tables = []
        
        if result and isinstance(result, list) and len(result) > 0:
            first = result[0]
            
            # 灏濊瘯鏂版牸寮?
            if isinstance(first, dict):
                db_info = first.get('result', first)
                
                # 鐩存帴鏈?tables 瀛楁
                if isinstance(db_info, dict) and 'tables' in db_info:
                    for table_name, table_info in db_info['tables'].items():
                        tables.append({
                            "name": table_name,
                            "info": str(table_info)[:100]
                        })
        
        # 濡傛灉浠嶇劧娌℃湁琛紝灏濊瘯鐩存帴鏌ヨ宸茬煡琛?
        if not tables:
            known_tables = ["fact", "conversation", "character", "user_entity", "observes", "about"]
            for tbl in known_tables:
                try:
                    count_result = await surreal_system.execute_raw_query(f"SELECT count() FROM {tbl} GROUP ALL;")
                    if count_result:
                        tables.append({"name": tbl, "info": "exists"})
                except:
                    pass
        
        return {"status": "success", "tables": tables}
    except Exception as e:
        logger.error(f"[SurrealDB] Get tables error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/surreal/table/{table_name}", deprecated=True)
async def get_surreal_table_data(table_name: str, limit: int = 50, character_id: Optional[str] = None):
    """(Deprecated) Use /admin/table/{table_name} instead"""
    surreal_system = _get_surreal()
    
    if not surreal_system:
        raise HTTPException(status_code=503, detail="SurrealDB not available")
    
    # 瀹夊叏妫€鏌ワ細鐧藉悕鍗?
    ALLOWED_TABLES = {
        "conversation_log", "episodic_memory", "semantic_memory", 
        "user_profile", "soul_state", "characters", "system_prompt_log"
    }
    
    if table_name not in ALLOWED_TABLES:
        # Fallback for dev: check alphanum if not in rigorous list
        if not table_name.replace("_", "").isalnum():
             raise HTTPException(status_code=400, detail="Invalid table name")

    try:
        if not surreal_system.db:
            await surreal_system.connect()
        
        # 鏋勫缓鍙傛暟鍖栨煡璇?
        where_clause = ""
        params = {"limit": limit}
        
        if character_id:
            where_clause = "WHERE character_id = $cid"
            params["cid"] = character_id
            
        # 鏌ヨ鏁版嵁锛堜笉杩斿洖 embedding 瀛楁锛屽お澶т簡锛?
        # Table name checks are sufficient to use f-string safely here
        query = f"SELECT * OMIT embedding FROM {table_name} {where_clause} ORDER BY created_at DESC LIMIT $limit;"
        
        logger.info(f"[DebugRouter] Querying table '{table_name}' with safe params: {params}")
        
        result = await surreal_system.execute_raw_query(query, params)
        if result and isinstance(result, list):
             logger.info(f"[SurrealDB] Table query returned {len(result)} rows from {table_name}")
        else:
             logger.info(f"[SurrealDB] Table query returned raw result type: {type(result)}")
        
        # 瑙f瀽缁撴灉 - SDK query() 宸茬粡杩斿洖瑙e寘鍚庣殑鏁版嵁 [{'id': ...}]
        data = []
        if result:
            # SDK 鐩存帴杩斿洖鏁版嵁鍒楄〃锛屼笉闇€瑕佸啀璁块棶 result[0]['result']
            data = result if isinstance(result, list) else []
        
        # 3. 閫掑綊娓呮礂鏁版嵁锛氬皢 RecordID 瀵硅薄杞崲涓哄瓧绗︿覆
        def sanitize_surreal_obj(obj):
            if isinstance(obj, list):
                return [sanitize_surreal_obj(item) for item in obj]
            elif isinstance(obj, dict):
                # Check if it's a RecordID dict (python client often returns it as dict or object)
                # print(f"DEBUG OBJ: {obj}")
                if "table_name" in obj and "record_id" in obj and len(obj) == 2:
                     # This looks like a serialized RecordID
                     return f"{obj['table_name']}:{obj['record_id']}"
                if "id" in obj:
                     val = obj["id"]
                     # Handle if 'id' value is itself a RecordID dict
                     if isinstance(val, dict) and "table_name" in val and "record_id" in val:
                         obj["id"] = f"{val['table_name']}:{val['record_id']}"
                         
                return {k: sanitize_surreal_obj(v) for k, v in obj.items()}
            else:
                # Check for RecordID object type if imported (or use string conversion)
                # The python client's RecordID.__str__ returns "table:id"
                if "RecordID" in str(type(obj)):
                     return str(obj)
                return obj

        clean_data = sanitize_surreal_obj(data)

        logger.info(f"[SurrealDB] Parsed {len(clean_data)} rows from {table_name}")
        return {"status": "success", "table": table_name, "count": len(clean_data), "data": clean_data}
    except Exception as e:
        logger.error(f"[SurrealDB] Get table data error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/surreal/stats", deprecated=True)
async def get_surreal_stats(character_id: str = None):
    """(Deprecated) Use /admin/stats instead"""
    surreal_system = _get_surreal()
    
    if not surreal_system:
        raise HTTPException(status_code=503, detail="SurrealDB not available")
    
    try:
        stats = await surreal_system.get_stats(character_id)
        return {"status": "success", "stats": stats}
    except Exception as e:
        logger.error(f"[SurrealDB] Stats error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/surreal/graph/{character_id}")
async def get_surreal_graph(character_id: str):
    """
    [DEPRECATED] Graph visualization endpoint
    """
    return {
        "status": "deprecated",
        "message": "Graph visualization is deprecated. Use /debug/surreal/table/episodic_memory instead.",
        "graph": {"nodes": [], "edges": []}
    }
