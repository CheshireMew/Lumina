"""
Debug 调试路由
包含: /debug/brain_dump, /debug/processing_status, /debug/surreal/*
"""
import os
import json
import logging
from typing import Dict, Optional
from pydantic import BaseModel
from fastapi import APIRouter, HTTPException

logger = logging.getLogger("DebugRouter")

router = APIRouter(prefix="/debug", tags=["Debug"])

# 全局引用（由 main.py 注入）
surreal_system = None
dreaming_service = None


def inject_dependencies(surreal, dreaming=None):
    """由 main.py 调用，注入全局依赖"""
    global surreal_system, dreaming_service
    surreal_system = surreal
    dreaming_service = dreaming


@router.post("/force_digest")
async def force_digest_memories():
    """强制 Dreaming 消化所有未处理的记忆"""
    global dreaming_service
    
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
    获取角色记忆的完整快照
    返回: { facts: [], graph: {nodes: [], edges: []}, history: [] }
    """
    global surreal_system
    
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
    """获取三层记忆处理管道的实时状态"""
    return {
        "status": "success",
        "conversations": {"unprocessed": 0, "total": 0},
        "facts": {"user": {"unconsolidated": 0, "total": 0}, "character": {"unconsolidated": 0, "total": 0}},
        "message": "Legacy processing status disabled."
    }

def _legacy_get_processing_status_graveyard(character_id):
    """Legacy code wrapped to prevent execution but avoid complex deletion match failures"""
    global memory_clients
    
    if character_id not in memory_clients:
        return {
            "status": "not_initialized",
            "message": f"Memory not initialized for '{character_id}'.",
            "conversations": {"unprocessed": 0, "total": 0},
            "facts": {"user": {"unconsolidated": 0, "total": 0}, "character": {"unconsolidated": 0, "total": 0}}
        }
    
    try:
        memory = memory_clients[character_id]
        
        # Conversation processing status
        unprocessed_convs = memory.sql_db.get_conversations_count(processed=False)
        total_convs = memory.sql_db.get_conversations_count(processed=True) + unprocessed_convs
        
        # Fact consolidation status (per channel)
        user_unconsolidated = memory.sql_db.get_facts_count(channel="user", consolidated=False)
        user_total = memory.sql_db.get_facts_count(channel="user", consolidated=True) + user_unconsolidated
        
        char_unconsolidated = memory.sql_db.get_facts_count(channel="character", consolidated=False)
        char_total = memory.sql_db.get_facts_count(channel="character", consolidated=True) + char_unconsolidated
        
        return {
            "status": "success",
            "conversations": {
                "unprocessed": unprocessed_convs,
                "total": total_convs,
                "threshold": 20,
                "progress_percent": min(100, (unprocessed_convs / 20) * 100) if unprocessed_convs < 20 else 100
            },
            "facts": {
                "user": {
                    "unconsolidated": user_unconsolidated,
                    "total": user_total,
                    "threshold": 10,
                    "progress_percent": min(100, (user_unconsolidated / 10) * 100) if user_unconsolidated < 10 else 100
                },
                "character": {
                    "unconsolidated": char_unconsolidated,
                    "total": char_total,
                    "threshold": 10,
                    "progress_percent": min(100, (char_unconsolidated / 10) * 100) if char_unconsolidated < 10 else 100
                }
            }
        }
    
    except Exception as e:
        logger.error(f"[API] Processing Status Error: {e}")
        return {
            "status": "error",
            "message": str(e),
            "conversations": {"unprocessed": 0, "total": 0},
            "facts": {"user": {"unconsolidated": 0, "total": 0}, "character": {"unconsolidated": 0, "total": 0}}
        }


@router.post("/memory/merge_entities")
async def trigger_entity_merge():
    """Trigger manual entity duplicate merging based on aliases."""
    global surreal_system
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


@router.post("/surreal/add")
async def add_surreal_memory(request: SurrealAddRequest):
    """向 SurrealDB 添加记忆（调试用）"""
    global memory_clients, surreal_system
    
    if not surreal_system:
        raise HTTPException(status_code=503, detail="SurrealDB not available")
    
    # 获取 encoder (Unified)
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


@router.post("/surreal/search")
async def search_surreal_memory(request: SurrealSearchRequest):
    """搜索 SurrealDB 记忆（调试用）"""
    global memory_clients, surreal_system
    
    if not surreal_system:
        raise HTTPException(status_code=503, detail="SurrealDB not available")
    
    active_client = next(iter(memory_clients.values())) if memory_clients else None
    if not active_client:
         raise HTTPException(status_code=500, detail="No active embedding model")

    try:
        embedding = active_client.encoder.encode(request.query).tolist()
        results = await surreal_system.search(embedding, request.character_id, request.limit)
        return {"results": results}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# ==================== SurrealDB 可视化 API ====================

class SurrealQueryRequest(BaseModel):
    query: str  # SurrealQL 查询语句


@router.get("/surreal/tables")
async def get_surreal_tables():
    """获取 SurrealDB 所有表列表"""
    global surreal_system
    
    if not surreal_system:
        raise HTTPException(status_code=503, detail="SurrealDB not available")
    
    try:
        if not surreal_system.db:
            await surreal_system.connect()
        
        result = await surreal_system.db.query("INFO FOR DB;")
        logger.info(f"[SurrealDB] INFO FOR DB raw result: {result}")
        
        # 解析表信息（支持多种格式）
        tables = []
        
        if result and isinstance(result, list) and len(result) > 0:
            first = result[0]
            
            # 尝试新格式
            if isinstance(first, dict):
                db_info = first.get('result', first)
                
                # 直接有 tables 字段
                if isinstance(db_info, dict) and 'tables' in db_info:
                    for table_name, table_info in db_info['tables'].items():
                        tables.append({
                            "name": table_name,
                            "info": str(table_info)[:100]
                        })
        
        # 如果仍然没有表，尝试直接查询已知表
        if not tables:
            known_tables = ["fact", "conversation", "character", "user_entity", "observes", "about"]
            for tbl in known_tables:
                try:
                    count_result = await surreal_system.db.query(f"SELECT count() FROM {tbl} GROUP ALL;")
                    if count_result:
                        tables.append({"name": tbl, "info": "exists"})
                except:
                    pass
        
        return {"status": "success", "tables": tables}
    except Exception as e:
        logger.error(f"[SurrealDB] Get tables error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/surreal/table/{table_name}")
async def get_surreal_table_data(table_name: str, limit: int = 50, character_id: Optional[str] = None):
    """获取指定表的数据"""
    global surreal_system
    
    if not surreal_system:
        raise HTTPException(status_code=503, detail="SurrealDB not available")
    
    # 安全检查：只允许字母数字下划线
    if not table_name.replace("_", "").isalnum():
        raise HTTPException(status_code=400, detail="Invalid table name")
    
    try:
        if not surreal_system.db:
            await surreal_system.connect()
        
        # 构建查询
        where_clause = ""
        if character_id:
            where_clause = f"WHERE character_id = '{character_id}'"
            
        # 查询数据（不返回 embedding 字段，太大了）
        query = f"SELECT * OMIT embedding FROM {table_name} {where_clause} ORDER BY created_at DESC LIMIT {limit};"
        
        logger.info(f"[DebugRouter] Querying table '{table_name}' with user '{character_id}'")
        logger.info(f"[DebugRouter] SQL: {query}")
        
        result = await surreal_system.db.query(query)
        if result and isinstance(result, list):
             logger.info(f"[SurrealDB] Table query returned {len(result)} rows from {table_name}")
        else:
             logger.info(f"[SurrealDB] Table query returned raw result type: {type(result)}")
        
        # 解析结果 - SDK query() 已经返回解包后的数据 [{'id': ...}]
        data = []
        if result:
            # SDK 直接返回数据列表，不需要再访问 result[0]['result']
            data = result if isinstance(result, list) else []
        
        # 3. 递归清洗数据：将 RecordID 对象转换为字符串
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


@router.delete("/surreal/record/{table_name}/{record_id}")
async def delete_surreal_record(table_name: str, record_id: str):
    """删除指定记录"""
    global surreal_system
    
    if not surreal_system:
        raise HTTPException(status_code=503, detail="SurrealDB not available")
        
    try:
        if not surreal_system.db:
            await surreal_system.connect()
            
        # 安全检查
        if not table_name.replace("_", "").isalnum():
             raise HTTPException(status_code=400, detail="Invalid table name")
             
        # ID 必须是 ID 格式 (不含 table 前缀，或者含)
        # SurrealDB delete 语法: DELETE type::thing('id') OR DELETE type:id
        # 我们假设传入的是纯 ID，或者是 table:id 格式
        
        target_id = record_id
        if ":" not in record_id:
            target_id = f"{table_name}:{record_id}"
            
        logger.info(f"[SurrealDB] DELETING {target_id}...")
        
        # 使用 SDK delete 方法
        await surreal_system.db.delete(target_id)
        
        return {"status": "success", "message": f"Deleted {target_id}"}
        
    except Exception as e:
        logger.error(f"[SurrealDB] Delete error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.put("/surreal/record/{table_name}/{record_id}")
async def update_surreal_record(table_name: str, record_id: str, data: Dict):
    """更新指定记录 (Merge Strategy)"""
    global surreal_system
    
    if not surreal_system:
        raise HTTPException(status_code=503, detail="SurrealDB not available")
        
    try:
        if not surreal_system.db:
            await surreal_system.connect()
            
        target_id = record_id
        if ":" not in record_id:
            target_id = f"{table_name}:{record_id}"
            
        logger.info(f"[SurrealDB] UPDATING {target_id} with {data}")
        
        # Merge updates (partial)
        # SurrealDB python client: merge(id, data)
        updated = await surreal_system.db.merge(target_id, data)
        return {"status": "success", "data": updated}
        
    except Exception as e:
        logger.error(f"[SurrealDB] Update error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/surreal/record/{table_name}")
async def create_surreal_record(table_name: str, data: Dict):
    """创建新记录"""
    global surreal_system
    
    if not surreal_system:
        raise HTTPException(status_code=503, detail="SurrealDB not available")
        
    try:
        if not surreal_system.db:
            await surreal_system.connect()
        
        logger.info(f"[SurrealDB] CREATING in {table_name} with {data}")
        
        # Create
        created = await surreal_system.db.create(table_name, data)
        
        # Unpack if list
        if isinstance(created, list) and len(created) > 0:
            created = created[0]
            
        return {"status": "success", "data": created}
        
    except Exception as e:
        logger.error(f"[SurrealDB] Create error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/surreal/query")
async def execute_surreal_query(request: SurrealQueryRequest):
    """执行自定义 SurrealQL 查询"""
    global surreal_system
    
    if not surreal_system:
        raise HTTPException(status_code=503, detail="SurrealDB not available")
    
    # 安全检查：禁止危险操作
    dangerous_keywords = ["DELETE", "REMOVE", "DROP", "KILL"]
    query_upper = request.query.upper()
    for keyword in dangerous_keywords:
        if keyword in query_upper:
            raise HTTPException(status_code=403, detail=f"Dangerous operation '{keyword}' not allowed")
    
    try:
        if not surreal_system.db:
            await surreal_system.connect()
        
        result = await surreal_system.db.query(request.query)
        logger.info(f"[SurrealDB] Custom query raw result: {str(result)[:300]}")
        
        # 解析结果（支持多种格式）
        if result and isinstance(result, list) and len(result) > 0:
            first = result[0]
            if isinstance(first, dict):
                if first.get('status') == 'ERR':
                    return {"status": "error", "error": first.get('result', 'Unknown error')}
                # 格式1: [{result: [...]}]
                if 'result' in first:
                    return {"status": "success", "result": first['result']}
                # 格式2: 直接是数据
                return {"status": "success", "result": result}
            return {"status": "success", "result": result}
        
        return {"status": "success", "result": result or []}
    except Exception as e:
        logger.error(f"[SurrealDB] Query error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/surreal/stats")
async def get_surreal_stats(character_id: str = None):
    """获取 SurrealDB 统计信息"""
    global surreal_system
    
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
    [DEPRECATED] 图谱可视化端点
    
    图谱功能已移除，所有记忆现在存储在 episodic_memory 表中。
    请使用 /surreal/table/episodic_memory 查看记忆数据。
    """
    return {
        "status": "deprecated",
        "message": "Graph visualization is deprecated. Use /debug/surreal/table/episodic_memory instead.",
        "graph": {"nodes": [], "edges": []}
    }

