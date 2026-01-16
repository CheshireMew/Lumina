"""
Memory Router
Includes: /add, /search, /consolidate_history, /all, /memory/inspiration

Refactored: Removed inject_dependencies pattern
Now uses container for core services, EventBus for plugin services
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


def _get_surreal():
    """Get SurrealDB from container"""
    from services.container import services
    return services.surreal_system


def _get_soul():
    """Get SoulClient from container"""
    from services.container import services
    return services.soul_client


def _get_service(name: str):
    """Get plugin service from EventBus"""
    from core.events.bus import get_event_bus
    bus = get_event_bus()
    return bus.get_service(name) if bus else None


@router.post("/add")
async def add_memory(request: AddMemoryRequest):
    """Add memory to SurrealDB (Primary Storage)"""
    surreal_system = _get_surreal()
    soul_client = _get_soul()
    hippocampus_service = _get_service("hippocampus_service")
    
    # [Refactor] Fallback for optional character_id
    character_id = request.character_id
    if not character_id:
        if surreal_system and hasattr(surreal_system, 'character_id'):
            character_id = surreal_system.character_id
        else:
            character_id = "default"

    print(f"[API] Character: {character_id}")
    
    # 妫€鏌?SurrealDB 鏄惁鍙敤
    if not surreal_system:
        raise HTTPException(
            status_code=503, 
            detail="SurrealDB not available. Please ensure SurrealDB is running."
        )
    
    # 鑾峰彇 encoder (Unified Model Management)
    encoder = surreal_system.encoder if hasattr(surreal_system, 'encoder') else None
    
    if not encoder:
        print("[API] Warning: Encoder not found in SurrealSystem.")
    
    try:
        user_input = ""
        ai_response = ""
        timestamp = "unknown"
        
        # Extract last user/ai pair
        for m in reversed(request.messages):
            if m.role == "assistant" and not ai_response:
                ai_response = m.content
            elif m.role == "user" and not user_input:
                user_input = m.content
            
            if m.timestamp is not None and timestamp == "unknown":
                timestamp = m.timestamp

        if not user_input and not ai_response:
            return {"status": "skipped", "reason": "Empty interaction"}

        # Normalize user input for proactive cases
        if not user_input:
             user_input = "(Silence)"

        # 鏋勯€犲璇濆唴瀹?
        content = f"{request.user_name}: {user_input}\n{request.character_name}: {ai_response}"

        # 璁板綍瀵硅瘽鏃ュ織 (SurrealDB)
        log_id = await surreal_system.log_conversation(
            character_id=character_id,
            narrative=content
        )
        
        # [Soul Update] 
        # Decoupled: Use Galgame Manager if available
        galgame_service = _get_service("galgame_manager")
        if galgame_service and hasattr(galgame_service, 'update_energy'):
             # Update Interaction Time & Energy via Plugin
             # GalgameManager doesn't expose update_last_interaction explicitly? 
             # It subscribes to ticker usually, but interactive update is good.
             # Actually GalgameManager handles logic internally.
             # But wait, checking galgame/manager.py... it doesn't seem to have 'update_last_interaction'.
             # Let's check.
             
             # Fallback: soul_client still holds the STATE (last_interaction).
             # We should keep update_last_interaction in SoulManager as it's Core State (Metadata).
             # BUT update_energy is definitely Game Logic.
             pass

        if soul_client:
             soul_client.update_last_interaction()
             
        if galgame_service:
             # Apply Energy Cost
             galgame_service.update_energy(-0.1)
        
        # [Hippocampus Trigger]
        if hippocampus_service:
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
    """Search memory (SurrealDB Primary)"""
    surreal_system = _get_surreal()
    
    # [Refactor] Fallback for optional character_id
    character_id = request.character_id
    if not character_id:
        if surreal_system and hasattr(surreal_system, 'character_id'):
            character_id = surreal_system.character_id
        else:
            character_id = "default"
    
    # 妫€鏌?SurrealDB
    if not surreal_system:
        raise HTTPException(status_code=503, detail="SurrealDB not available")
    
    import time
    start_time = time.time()

    # 鑾峰彇 encoder
    encoder = surreal_system.encoder
    if not encoder:
         raise HTTPException(status_code=500, detail="Embedding encoder not ready")

    try:
        # 鐢熸垚鏌ヨ鍚戦噺
        query_vec = encoder(request.query)
        if hasattr(query_vec, 'tolist'):
            query_vec = query_vec.tolist()
        
        # [Free Tier Opt] Dynamic Routing
        # [Free Tier Opt] Dynamic Routing
        # from llm.manager import llm_manager
        from services.container import services
        llm_manager = services.get_llm_manager()
        route = llm_manager.get_route("memory")
        
        target_table = "episodic_memory"
        final_limit = request.limit
        
        if route and route.provider_id == "free_tier":
            print("[API] Free Tier detected: Fallback to Searching Conversation Logs (Limit 3)")
            target_table = "conversation_log"
            final_limit = min(request.limit, 3)
            
        # 鎼滅储 SurrealDB
        results = await surreal_system.search(
            query_vec, character_id, 
            limit=final_limit,
            target_table=target_table
        )
        
        search_time = (time.time() - start_time) * 1000
        logger.info(f"🔎 SurrealDB Search: '{request.query}' -> {len(results)} hits ({search_time:.1f}ms)")
        
        # 杞崲涓哄墠绔湡鏈涚殑鏍煎紡
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
    """Hybrid Search (Vector + Fulltext) SurrealDB"""
    surreal_system = _get_surreal()
    
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
    
    # 妫€鏌?SurrealDB
    if not surreal_system:
        raise HTTPException(status_code=503, detail="SurrealDB not available")
    
    # 鑾峰彇 encoder
    encoder = surreal_system.encoder if hasattr(surreal_system, 'encoder') else None
    
    if not encoder:
        raise HTTPException(status_code=500, detail="Embedding encoder not available")
    
    try:
        # 鐢熸垚鏌ヨ鍚戦噺
        query_vec = encoder(request.query)
        if hasattr(query_vec, 'tolist'):
            query_vec = query_vec.tolist()
        
        # [Free Tier Opt] Dynamic Routing
        # [Free Tier Opt] Dynamic Routing
        # from llm.manager import llm_manager
        from services.container import services
        llm_manager = services.get_llm_manager()
        route = llm_manager.get_route("memory")
        
        target_table = "episodic_memory"
        final_limit = request.limit
        
        if route and route.provider_id == "free_tier":
            print("[API] Free Tier detected: Fallback to Hybrid Searching Logs (Limit 3)")
            target_table = "conversation_log"
            final_limit = min(request.limit, 3)

        # SurrealDB 娣峰悎鎼滅储
        results = await surreal_system.search_hybrid(
            query=request.query,
            query_vector=query_vec,
            character_id=character_id,
            limit=final_limit,
            target_table=target_table
        )
        
        print(f"[API] Hybrid Search (SurrealDB) found {len(results)} results")
        
        # 杞崲鏍煎紡
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
    """Archive history (Deprecated: SurrealDB handles persistence)"""
    try:
        print(f"[API] /consolidate_history called for '{request.character_id}'. Action: Skipped (Legacy).")
        return {"status": "success", "archived_count": 0, "message": "Legacy consolidation skipped."}

    except Exception as e:
        print(f"[API] Consolidation Error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/dream_on_idle")
async def dream_on_idle(request: DreamRequest):
    """Trigger idle dreaming / consolidation"""
    dreaming_service = _get_service("dreaming_service")
    try:
        print(f"[API] 🛌 Idle Dream Request for '{request.character_id}'")
        
        if not dreaming_service:
             raise HTTPException(status_code=500, detail="DreamingService not initialized.")

        dreaming_service.wake_up(mode="deep")
        
        return {"status": "success", "message": "Dreaming cycle started"}

    except Exception as e:
        print(f"[API] Dreaming Error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/context/clear")
async def clear_context(request: AddMemoryRequest):
    """Clear Short-Term Context (Session History)"""
    from services.session_manager import session_manager
    try:
        # Using AddMemoryRequest structure for convenience (user_id, character_id)
        # Or should we define a specific request schema? 
        # AddMemoryRequest has character_id.
        cid = request.character_id or "default"
        uid = request.user_id or "default_user"
        
        session_manager.clear_history(uid, cid)
        print(f"[API] Context cleared for {uid}:{cid}")
        return {"status": "success", "message": "Short-term context cleared"}
    except Exception as e:
        logger.error(f"Context Clear Error: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/all")
async def get_all_memories(character_id: str = "hiyori"):
    """Get all memories (SurrealDB)"""
    print(f"\n--- [API] /all Request Received ---")
    surreal_system = _get_surreal()
    
    if not surreal_system:
         raise HTTPException(status_code=503, detail="SurrealDB not available")
    
    try:
        results = await surreal_system.get_all_conversations(character_id=character_id)
        
        # 鏍煎紡鍖?
        memories = []
        for r in results:
            memories.append({
                "id": str(r.get("id", "")),
                "content": r.get("content", ""),
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
    """Get random memories for inspiration (SurrealDB)"""
    surreal_system = _get_surreal()
    if not surreal_system:
        return []
        
    try:
        results = await surreal_system.get_inspiration(character_id=character_id, limit=limit)
        
        # 鏍煎紡鍖?
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
