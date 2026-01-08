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
# 全局引用（由 main.py 注入）
memory_clients: Dict = {}
surreal_system = None
hippocampus_service = None


def inject_dependencies(clients: Dict, surreal, hippo=None):
    """由 main.py 调用，注入全局依赖"""
    global memory_clients, surreal_system, hippocampus_service
    memory_clients = clients
    surreal_system = surreal
    hippocampus_service = hippo


@router.post("/force_digest")
async def force_digest_memories():
    """强制海马体消化所有未处理的记忆"""
    global hippocampus_service
    
    if not hippocampus_service:
        raise HTTPException(status_code=503, detail="Hippocampus service not available")
        
    try:
        # Import here to avoid circular dependency if possible, or use global
        # Assuming hippocampus_service has process_memories
        logger.info("[Debug] Forcing memory digestion...")
        await hippocampus_service.process_memories(batch_size=5, force=True)
        return {"status": "success", "message": "Digestion triggered"}
    except Exception as e:
        logger.error(f"[Debug] Digestion error: {e}")
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
        results = await surreal_system.get_all_conversations(agent_id=character_id)
        
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
    agent_id: str
    user_id: str = "user_default"
    importance: int = 1
    emotion: Optional[str] = None


class SurrealSearchRequest(BaseModel):
    query: str
    agent_id: str
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
            agent_id=request.agent_id,
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
        results = await surreal_system.search(embedding, request.agent_id, request.limit)
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
async def get_surreal_table_data(table_name: str, limit: int = 50):
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
        
        # 查询数据（不返回 embedding 字段，太大了）
        query = f"SELECT * OMIT embedding FROM {table_name} ORDER BY created_at DESC LIMIT {limit};"
        result = await surreal_system.db.query(query)
        logger.info(f"[SurrealDB] Table query raw result type: {type(result)}, value: {str(result)[:200]}")
        
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
async def get_surreal_stats(agent_id: str = None):
    """获取 SurrealDB 统计信息"""
    global surreal_system
    
    if not surreal_system:
        raise HTTPException(status_code=503, detail="SurrealDB not available")
    
    try:
        stats = await surreal_system.get_stats(agent_id)
        return {"status": "success", "stats": stats}
    except Exception as e:
        logger.error(f"[SurrealDB] Stats error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/surreal/graph/{agent_id}")
async def get_surreal_graph(agent_id: str):
    """获取指定角色的图关系数据（用于可视化）"""
    global surreal_system
    
    if not surreal_system:
        raise HTTPException(status_code=503, detail="SurrealDB not available")
    
    try:
        if not surreal_system.db:
            await surreal_system.connect()
        
        # 1. 获取所有 Entity 节点
        # 限制数量以防前端卡死
        entity_query = "SELECT * FROM entity ORDER BY created_at DESC LIMIT 50;"
        entity_result = await surreal_system.db.query(entity_query)
        
        logger.info(f"[Graph Debug] Entity Query Result: {str(entity_result)[:200]}")
        
        nodes = []
        edges = []
        entity_ids = set()
        
        # 健壮的结果解析函数 - SDK query() 已返回解包后的数据
        def parse_surreal_result(res):
            if not res: return []
            # SDK 直接返回 [{'id': ...}] 或者 {'tables': ...} (for INFO FOR DB)
            if isinstance(res, list):
                return res
            elif isinstance(res, dict):
                return res
            return []

        # 解析 Entity
        entities_data = parse_surreal_result(entity_result)
        logger.info(f"[Graph Debug] Parsed {len(entities_data)} entities")
        
        for item in entities_data:
            # Fix unhashable RecordID
            raw_id = item['id']
            # Convert RecordID to string "table:id"
            str_id = str(raw_id)
            
            # Pass ALL other attributes to the frontend
            node_data = {k: v for k, v in item.items() if k != 'id'}
            
            nodes.append({
                "id": str_id,
                "label": item.get('name', 'Unknown'),
                "type": "entity",
                "group": "knowledge",
                **node_data # Unpack all extra data (context, type, etc)
            })
            entity_ids.add(str_id)
            
        # 2. 动态发现边表
        info_query = "INFO FOR DB;"
        info_result = await surreal_system.db.query(info_query)
        logger.info(f"[Graph Debug] Info Result: {str(info_result)[:200]}")
        
        edge_tables = []
        known_node_tables = ["conversation", "entity", "character", "user", "user_entity", "memory_embeddings", "migrations"]
        
        info_data = parse_surreal_result(info_result)
        db_tables = {}
        if isinstance(info_data, dict) and "tables" in info_data:
            db_tables = info_data["tables"]
        elif isinstance(info_data, list) and len(info_data) > 0 and "tables" in info_data[0]:
             db_tables = info_data[0]["tables"]
             
        for tbl in db_tables.keys():
            if tbl not in known_node_tables:
                edge_tables.append(tbl)
        
        # [CRITICAL UPDATE] Force include known relationship tables if they exist but were missed or if we just want to be sure
        for required_edge in ["observes", "about", "attributed_to"]:
            if required_edge not in edge_tables:
                 edge_tables.append(required_edge)

        logger.info(f"[Graph] Found potential edge tables: {edge_tables}")
        
        # 3. 查询具体的边
        for edge_tbl in edge_tables:
            try:
                # 为每个边表构建查询 - SELECT * to get all fields
                edge_query = f"SELECT * FROM {edge_tbl} LIMIT 100;"
                logger.info(f"[Graph Debug] Querying edge table: {edge_tbl}")
                edge_res = await surreal_system.db.query(edge_query)
                # logger.info(f"Raw Edge Res: {edge_res}")
                
                e_data = parse_surreal_result(edge_res)
                logger.info(f"[Graph Debug] Parsed edges from {edge_tbl}: {len(e_data)}")
                if len(e_data) > 0:
                     logger.info(f"[Graph Debug] Sample edge: {e_data[0]}")

                for link in e_data:
                    # Surreal edge format: 'in' is source, 'out' is target
                    # Also check commonly aliased fields just in case
                    src = link.get('in') or link.get('source')
                    dst = link.get('out') or link.get('target')

                    if src and dst:
                        src = str(src)
                        dst = str(dst)
                        
                        # Include ALL edge data for detail view
                        edge_obj = {
                            "from": src,
                            "to": dst,
                            "label": edge_tbl.upper(),
                            "arrows": "to",
                            # Full edge data for detail modal
                            "strength": link.get('strength') or link.get('weight'),
                            "weight": link.get('weight'),
                            "emotion": link.get('emotion'),
                            "context": link.get('context'),
                            "potential_reason": link.get('potential_reason'),
                            "created_at": str(link.get('created_at', '')),
                            "last_mentioned": str(link.get('last_mentioned') or link.get('last_accessed', '')),
                            "id": str(link.get('id', '')),
                        }
                        edges.append(edge_obj)
                        
                        # 补充隐式节点 (Implicit Nodes)
                        # 如果边的端点不在我们目前的 nodes 列表里，添加它们，
                        # 这样我们至少能看到孤立的这种连接，而不是因为缺节点而不画线。
                        if src not in entity_ids:
                            nodes.append({
                                "id": src, 
                                "label": src.split(":")[-1], 
                                "type": "implicit", 
                                "group": "other"
                            })
                            entity_ids.add(src)
                        
                        if dst not in entity_ids:
                            nodes.append({
                                "id": dst, 
                                "label": dst.split(":")[-1], 
                                "type": "implicit", 
                                "group": "other"
                            })
                            entity_ids.add(dst)
                            
            except Exception as e:
                logger.warning(f"[Graph] Failed to query edge table {edge_tbl}: {e}")

        # 4. 加入角色自身节点
        char_node_id = f"character:{agent_id}"
        if char_node_id not in entity_ids:
             nodes.append({"id": char_node_id, "label": agent_id, "type": "character", "group": "agent"})


        edge_query = f"""
        SELECT id, in, out, weight, emotion 
        FROM observes 
        WHERE in = character:{agent_id}
        LIMIT 100;
        """
        edge_result = await surreal_system.db.query(edge_query)
        
        # SDK 直接返回 [{'id': ...}]
        if edge_result:
            for edge in edge_result:
                fact_id = str(edge.get('out', ''))
                edges.append({
                    "source": f"character:{agent_id}",
                    "target": fact_id,
                    "type": "observes",
                    "weight": edge.get('weight', 0)
                })
                
                # 添加事实节点
                nodes.append({"id": fact_id, "type": "fact", "label": "Fact"})
        
        # 获取 about 边（fact -> user）
        about_query = """
        SELECT id, in, out FROM about LIMIT 100;
        """
        about_result = await surreal_system.db.query(about_query)
        
        # SDK 直接返回 [{'id': ...}]
        if about_result:
            user_ids = set()
            for edge in about_result:
                fact_id = str(edge.get('in', ''))
                user_id = str(edge.get('out', ''))
                
                # 只添加与当前角色相关的边
                if any(n['id'] == fact_id for n in nodes):
                    edges.append({
                        "source": fact_id,
                        "target": user_id,
                        "type": "about"
                    })
                    user_ids.add(user_id)
            
            # 添加用户节点
            for uid in user_ids:
                nodes.append({"id": uid, "type": "user", "label": uid.split(":")[-1]})
        
        return {
            "status": "success",
            "graph": {
                "nodes": nodes,
                "edges": edges
            }
        }
    except Exception as e:
        logger.error(f"[SurrealDB] Graph error: {e}")
        raise HTTPException(status_code=500, detail=str(e))

