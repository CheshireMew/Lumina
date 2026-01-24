
import logging
from fastapi import APIRouter, HTTPException, Depends
from typing import Any, Optional
from routers.deps import get_memory_service
from schemas.requests import AddMemoryRequest, SearchRequest
from pydantic import BaseModel

logger = logging.getLogger("MemoryRoutes")
router = APIRouter() # Prefix handled by inclusion

class ClearContextRequest(BaseModel):
    user_id: Optional[str] = "default_user"
    character_id: Optional[str] = "default_char"

@router.post("/add")
async def add_memory(request: AddMemoryRequest, memory_manager: Any = Depends(get_memory_service)):
    """Add memory to SurrealDB (Primary Storage)"""
    if not memory_manager or memory_manager.status != "ready":
         raise HTTPException(status_code=503, detail="Memory Service not ready")

    # Encoder check
    # MemoryManager wraps SurrealSystem
    # But wait, MemoryManager is what we get here. 
    # memory_manager.surreal is the system.
    surreal = memory_manager.surreal
    if not surreal:
        raise HTTPException(status_code=503, detail="SurrealDB Backend not connected")

    # Character ID Fallback
    character_id = request.character_id
    if not character_id:
        if hasattr(surreal, 'character_id'):
            character_id = surreal.character_id
        else:
            character_id = "default"

    try:
        user_input = ""
        ai_response = ""
        timestamp = "unknown"
        
        for m in reversed(request.messages):
            if m.role == "assistant" and not ai_response:
                ai_response = m.content
            elif m.role == "user" and not user_input:
                user_input = m.content
            if m.timestamp is not None and timestamp == "unknown":
                timestamp = m.timestamp

        if not user_input and not ai_response:
            return {"status": "skipped", "reason": "Empty interaction"}

        if not user_input: user_input = "(Silence)"

        content = f"{request.user_name}: {user_input}\n{request.character_name}: {ai_response}"

        log_id = await surreal.log_conversation(
            character_id=character_id,
            narrative=content
        )
        
        # [Refactor Note] Side-effects (Soul updates) removed. Caller must handle.
        
        return {"status": "success", "id": str(log_id), "storage": "surreal"}
    except Exception as e:
        logger.error(f"Add Memory Error: {e}")
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/search")
async def search_memory(request: SearchRequest, memory_manager: Any = Depends(get_memory_service)):
    if not memory_manager or not memory_manager.surreal:
         raise HTTPException(status_code=503, detail="Memory Service not ready")
    
    surreal = memory_manager.surreal
    
    character_id = request.character_id or (surreal.character_id if hasattr(surreal, 'character_id') else "default")
    
    import time
    start_time = time.time()

    encoder = surreal.encoder
    if not encoder:
         raise HTTPException(status_code=500, detail="Embedding encoder not ready")

    try:
        query_vec = encoder(request.query)
        if hasattr(query_vec, 'tolist'):
            query_vec = query_vec.tolist()
        
        # Routing Logic removed/simplified? 
        # In Worker, we assume full capability unless configured otherwise.
        # "Free Tier" logic belonged to Gateway/LLM Manager. 
        # Here we just executing search. Caller decides target_table if needed or we default.
        # Let's keep strict search for episodic_memory unless requested?
        # The original code dynamically switched based on LLM Tier.
        # Worker shouldn't know about LLM Tier.
        # We will search "episodic_memory" by default.
        
        target_table = "episodic_memory"
        final_limit = request.limit
        
        results = await surreal.search(
            query_vec, character_id, 
            limit=final_limit,
            target_table=target_table
        )
        
        search_time = (time.time() - start_time) * 1000
        logger.info(f"🔎 Memory Search: '{request.query}' -> {len(results)} hits ({search_time:.1f}ms)")
        
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
        logger.error(f"Search Error: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/search/hybrid")
async def search_memory_hybrid(request: SearchRequest, memory_manager: Any = Depends(get_memory_service)):
    if not memory_manager or not memory_manager.surreal:
         raise HTTPException(status_code=503, detail="Memory Service not ready")
    surreal = memory_manager.surreal
    character_id = request.character_id or (surreal.character_id if hasattr(surreal, 'character_id') else "default")

    encoder = surreal.encoder
    if not encoder: raise HTTPException(status_code=500, detail="Encoder not ready")
    
    try:
        query_vec = encoder(request.query)
        if hasattr(query_vec, 'tolist'): query_vec = query_vec.tolist()
        
        results = await surreal.search_hybrid(
            query=request.query,
            query_vector=query_vec,
            character_id=character_id,
            limit=request.limit,
            target_table="episodic_memory"
        )
        
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
        logger.error(f"Hybrid Search Error: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/all")
async def get_all_memories(character_id: str = "hiyori", memory_manager: Any = Depends(get_memory_service)):
    if not memory_manager or not memory_manager.surreal:
         raise HTTPException(status_code=503, detail="Memory Service not ready")
    surreal = memory_manager.surreal
    
    try:
        if hasattr(surreal, 'get_all_conversations'):
             results = await surreal.get_all_conversations(character_id=character_id)
        else:
             sql = "SELECT * FROM conversation_log WHERE character_id = $cid ORDER BY created_at DESC LIMIT 50"
             results = await surreal.query(sql, {"cid": character_id})
             if isinstance(results, dict) and 'result' in results: results = results['result']
        
        memories = []
        for r in results:
            memories.append({
                "id": str(r.get("id", "")),
                "content": r.get("content", ""),
                "role": r.get("role", "user"),
                "created_at": r.get("created_at", "")
            })
        return memories
    except Exception as e:
        logger.error(f"Get All Error: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/inspiration")
async def get_inspiration(character_id: str = "hiyori", limit: int = 3, memory_manager: Any = Depends(get_memory_service)):
    if not memory_manager or not memory_manager.surreal:
         raise HTTPException(status_code=503, detail="Memory Service not ready")
    
    try:
        results = await memory_manager.surreal.get_inspiration(character_id=character_id, limit=limit)
        formatted = []
        for r in results:
            formatted.append({
                "id": str(r.get("id", "")),
                "content": r.get("content", ""),
                "created_at": r.get("created_at", "")
            })
        return formatted
    except Exception as e:
        logger.error(f"Inspiration Error: {e}")
        raise HTTPException(status_code=500, detail=str(e))
