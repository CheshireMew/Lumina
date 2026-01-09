"""
Memory 相关路由
包含: /add, /search, /consolidate_history, /all, /memory/inspiration
"""
import os
import json
import time
import logging
from typing import Dict, Optional
from fastapi import APIRouter, HTTPException

from schemas.requests import AddMemoryRequest, SearchRequest, ConsolidateRequest, DreamRequest

logger = logging.getLogger("MemoryRouter")

router = APIRouter(tags=["Memory"])

# 全局引用（由 main.py 注入）
# 全局引用（由 main.py 注入）
memory_clients: Dict = {}
dreaming_service = None
soul_client = None
surreal_system = None
hippocampus_service = None


def inject_dependencies(soul, surreal, dreamer=None, hippocampus=None):
    """由 main.py 调用，注入全局依赖"""
    global dreaming_service, soul_client, surreal_system, hippocampus_service
    dreaming_service = dreamer
    soul_client = soul
    surreal_system = surreal
    hippocampus_service = hippocampus


@router.post("/add")
async def add_memory(request: AddMemoryRequest):
    """添加记忆到 SurrealDB（主存储）"""
    global memory_clients, soul_client, surreal_system
    
    # [Refactor] Fallback for optional character_id
    character_id = request.character_id
    if not character_id:
        # Try SurrealSystem default
        if surreal_system and hasattr(surreal_system, 'character_id'):
            character_id = surreal_system.character_id
        else:
            character_id = "default"  # Ultimate safety net

    print(f"[API] Character: {character_id}")
    
    # 检查 SurrealDB 是否可用
    if not surreal_system:
        raise HTTPException(
            status_code=503, 
            detail="SurrealDB not available. Please ensure SurrealDB is running."
        )
    
    # 获取 encoder (Unified Model Management)
    encoder = surreal_system.encoder if surreal_system and hasattr(surreal_system, 'encoder') else None
    
    if not encoder:
        # Fallback if no specific char encoder (should share global one)
        print("[API] Warning: Encoder not found in SurrealSystem.")
        encoder = None
    
    try:
        user_input = ""
        ai_response = ""
        timestamp = "unknown"
        
        # Extract last user/ai pair
        for m in reversed(request.messages):
            if m["role"] == "assistant" and not ai_response:
                ai_response = m["content"]
            elif m["role"] == "user" and not user_input:
                user_input = m["content"]
            
            if "timestamp" in m and timestamp == "unknown":
                timestamp = m["timestamp"]

        if not user_input and not ai_response:
            return {"status": "skipped", "reason": "Empty interaction"}

        # Normalize user input for proactive cases
        if not user_input:
             user_input = "(Silence)"

        # 构造对话内容 [Refactor] Use character_name
        content = f"{request.user_name}: {user_input}\n{request.character_name}: {ai_response}"

        # 记录对话日志 (SurrealDB)
        # 注意：不再直接调用 add_memory，而是记录日志后由后台 Dreaming 进程异步提取记忆
        log_id = await surreal_system.log_conversation(
            character_id=character_id,
            narrative=content
        )
        
        # [Soul Update] 
        if soul_client:
            soul_client.update_last_interaction()
            if ai_response:
                 soul_client.update_energy(-0.1)
        
        # [Hippocampus Trigger]
        if hippocampus_service:
            # Check if we should digest memories (Accumulate 20)
            # We fire this asynchronously so we don't block the UI too long, 
            # OR we await it if we want to ensure consistency. 
            # The user logic allows accumulation, so it usually returns fast.
            await hippocampus_service.process_memories(batch_size=20)

        print(f"[API] ✅ Conversation logged: {log_id}")
        return {"status": "success", "id": str(log_id), "storage": "surreal"}
    except Exception as e:
        print(f"[API] ADD ERROR: {e}")
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/search")
async def search_memory(request: SearchRequest):
    """搜索记忆（SurrealDB 主存储）"""
    global memory_clients, surreal_system
    
    # [Refactor] Fallback for optional character_id
    character_id = request.character_id
    if not character_id:
        if surreal_system and hasattr(surreal_system, 'character_id'):
            character_id = surreal_system.character_id
        else:
            character_id = "default"
    
    # 检查 SurrealDB
    if not surreal_system:
        raise HTTPException(status_code=503, detail="SurrealDB not available")
    
    import time
    start_time = time.time()

    # 获取 encoder
    encoder = surreal_system.encoder
    if not encoder:
         raise HTTPException(status_code=500, detail="Embedding encoder not ready")

    try:
        # 生成查询向量
        # Encoder injected text -> list
        query_vec = encoder(request.query)
        
        # 搜索 SurrealDB
        results = await surreal_system.search(query_vec, character_id, limit=request.limit)
        
        search_time = (time.time() - start_time) * 1000
        logger.info(f"🟣 SurrealDB Search: '{request.query}' → {len(results)} hits ({search_time:.1f}ms)")
        
        # 转换为前端期望的格式
        formatted_results = []
        for r in results:
            formatted_results.append({
                "id": str(r.get("id", "")),
                "content": r.get("content", ""),
                "score": r.get("score", 0),
                "created_at": r.get("created_at", ""),
                "importance": r.get("importance", 1)
            })

        return formatted_results
    except Exception as e:
        print(f"[API] SEARCH ERROR: {e}")
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/search/hybrid")
async def search_memory_hybrid(request: SearchRequest):
    """混合搜索（向量 + 全文）- SurrealDB"""
    global memory_clients, surreal_system
    
    # [Refactor] Fallback for optional character_id
    character_id = request.character_id
    if not character_id:
        if surreal_system and hasattr(surreal_system, 'character_id'):
            character_id = surreal_system.character_id
        else:
            character_id = "default"
            
    print(f"\n--- [API] /search/hybrid Request Received ---")
    print(f"[API] Character: {character_id}")
    print(f"[API] Query: '{request.query}' Limit: {request.limit}")
    
    # 检查 SurrealDB
    if not surreal_system:
        raise HTTPException(status_code=503, detail="SurrealDB not available")
    
    # 获取 encoder
    # 获取 encoder (Unified)
    encoder = surreal_system.encoder if surreal_system and hasattr(surreal_system, 'encoder') else None
    
    if not encoder:
        raise HTTPException(status_code=500, detail="Embedding encoder not available")
    
    try:
        # 生成查询向量
        query_vec = encoder(request.query)
        
        # SurrealDB 混合搜索
        results = await surreal_system.search_hybrid(
            query=request.query,
            query_vector=query_vec,
            character_id=character_id,
            limit=request.limit
        )
        
        print(f"[API] Hybrid Search (SurrealDB) found {len(results)} results")
        
        # 转换格式
        formatted_results = []
        for r in results:
            formatted_results.append({
                "id": str(r.get("id", "")),
                "content": r.get("content", ""),
                "score": r.get("hybrid_score", 0),
                "created_at": r.get("created_at", ""),
                "importance": r.get("importance", 1)
            })
        
        return formatted_results
    except Exception as e:
        print(f"[API] HYBRID SEARCH ERROR: {e}")
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/consolidate_history")
async def consolidate_history(request: ConsolidateRequest):
    """归档历史消息"""
    """归档历史消息 (Deprecated: SurrealDB handles persistence)"""
    try:
        print(f"[API] /consolidate_history called for '{request.character_id}'. Action: Skipped (Legacy).")
        return {"status": "success", "archived_count": 0, "message": "Legacy consolidation skipped."}

    except Exception as e:
        print(f"[API] Consolidation Error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/dream_on_idle")
async def dream_on_idle(request: DreamRequest):
    """空闲时触发做梦/整合"""
    global dreaming_service
    try:
        print(f"[API] 🌙 Idle Dream Request for '{request.character_id}'")
        
        if not dreaming_service:
             raise HTTPException(status_code=500, detail="DreamingService not initialized. Call /configure first.")

        dreaming_service.wake_up(mode="deep")
        
        return {"status": "success", "message": "Dreaming cycle started"}

    except Exception as e:
        print(f"[API] Dreaming Error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/all")
async def get_all_memories(character_id: str = "hiyori"):
    """获取所有记忆（SurrealDB）"""
    print(f"\n--- [API] /all Request Received ---")
    global surreal_system
    
    if not surreal_system:
         raise HTTPException(status_code=503, detail="SurrealDB not available")
    
    try:
        results = await surreal_system.get_all_conversations(character_id=character_id)
        
        # 格式化
        memories = []
        for r in results:
            memories.append({
                "id": str(r.get("id", "")),
                "content": r.get("content", ""), # Map DB content -> Response content
                "role": r.get("role", "user"),
                "created_at": r.get("created_at", "")
            })
            
        print(f"[API] Found {len(memories)} memories in SurrealDB")
        return memories
    except Exception as e:
        print(f"[API] ALL ERROR: {e}")
        return {"error": str(e)}


@router.get("/memory/inspiration")
async def get_inspiration(character_id: str = "hiyori", limit: int = 3):
    """获取随机记忆用于灵感 (SurrealDB)"""
    global surreal_system
    if not surreal_system:
        # Fallback to empty if not ready (though it should be)
        return []
        
    try:
        results = await surreal_system.get_inspiration(character_id=character_id, limit=limit)
        
        # 格式化 (App.tsx expects 'content')
        formatted = []
        for r in results:
            formatted.append({
                "id": str(r.get("id", "")),
                "content": r.get("content", ""),
                "created_at": r.get("created_at", "")
            })
        return formatted
    except Exception as e:
        print(f"[API] Inspiration Error: {e}")
        return []
