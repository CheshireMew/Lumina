
import os
import uvicorn
from fastapi import FastAPI, HTTPException, BackgroundTasks

# ... existing code ...


from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import Dict, Any, List, Optional
import sys
import json
import time
from collections import defaultdict
from contextlib import asynccontextmanager
import logging

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(name)s: %(message)s',
    datefmt='%H:%M:%S'
)
logger = logging.getLogger("MemoryServer")

# Add python_backend to path to find local modules if needed
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from lite_memory import LiteMemory
from dreaming import DreamingService
from heartbeat_service import HeartbeatService  # 导入 HeartbeatService
# [SOUL] Soul Manager imported later, but we need it for Heartbeat init.
# Let's import it here to be clean.
from soul_manager import SoulManager

# Global Services
dreaming_service: Optional[DreamingService] = None
heartbeat_service_instance: Optional[HeartbeatService] = None # Heartbeat Instance
soul_client = SoulManager() # Global Soul Manager

# 请求防抖：防止短时间内重复配置同一个character
config_timestamps: Dict[str, float] = defaultdict(float)
CONFIG_COOLDOWN = 30  # 30秒冷却时间

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Lifespan event handler for startup/shutdown."""
    global memory_clients, dreaming_service, heartbeat_service_instance, soul_client
    
    # [Startup] Load Config
    config_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "memory_config.json")
    if os.path.exists(config_path):
        try:
            print(f"[API] Loading saved config from {config_path}...")
            with open(config_path, 'r', encoding='utf-8') as f:
                config_data = json.load(f)
            
            # Re-initialize hiyori
            character_id = config_data.get("character_id", "hiyori")
            # Ensure LiteMemory is initialized
            memory_clients[character_id] = LiteMemory(config_data, character_id=character_id)
            
            # Init Dreaming
            dreaming_service = DreamingService(
                base_url=config_data["base_url"],
                api_key=config_data["api_key"],
                memory_client=memory_clients[character_id]
            )
            print(f"[API] Auto-initialized memory for '{character_id}'")
        except Exception as e:
            print(f"[API] Failed to auto-load config: {e}")
    
    # [Startup] Start Heartbeat
    try:
        print("[API] Starting Heartbeat Service...")
        heartbeat_service_instance = HeartbeatService(soul_client)
        heartbeat_service_instance.start()
    except Exception as e:
        print(f"[API] Failed to start Heartbeat: {e}")

    yield
    
    # [Shutdown] Cleanup
    print("[API] Shutting down...")
    
    # Stop Heartbeat
    if heartbeat_service_instance:
        heartbeat_service_instance.stop()

app = FastAPI(lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Global LiteMemory instances (character_id -> LiteMemory)
memory_clients: Dict[str, LiteMemory] = {}

class ConfigRequest(BaseModel):
    base_url: str
    api_key: str
    model: Optional[str] = "deepseek-chat"
    embedder: Optional[str] = "paraphrase-multilingual-MiniLM-L12-v2"
    character_id: str = "hiyori"  # Character identifier
    
    @classmethod
    def validate_base_url(cls, v):
        """验证 base_url 格式"""
        if not v:
            raise ValueError('base_url cannot be empty')
        if not v.startswith(('http://', 'https://')):
            raise ValueError('base_url must start with http:// or https://')
        # 移除尾部斜杠以保持一致性
        return v.rstrip('/')
    
    @classmethod
    def validate_api_key(cls, v):
        """验证 api_key 非空且长度合理"""
        if not v or len(v.strip()) < 8:
            raise ValueError('api_key must be at least 8 characters')
        return v.strip()

class AddMemoryRequest(BaseModel):
    user_id: str = "user"
    character_id: str = "hiyori"
    user_name: str = "User"     # Default if missing
    char_name: str = "AI"       # Default if missing
    messages: List[Dict[str, Any]]

class SearchRequest(BaseModel):
    user_id: str
    character_id: str = "hiyori"  # Character identifier
    query: str
    limit: Optional[int] = 10
    empower_factor: Optional[float] = 0.5 # For RRF Hybrid Search

class ConsolidateRequest(BaseModel):
    user_id: str = "user"
    character_id: str = "hiyori"
    user_name: str = "User"
    char_name: str = "AI"
    messages: List[Dict[str, Any]]

class DreamRequest(BaseModel):
    user_id: str = "user"
    character_id: str = "hiyori"
    user_name: str = "User"
    char_name: str = "AI"

class UpdateIdentityRequest(BaseModel):
    name: str
    description: str

class UpdateUserNameRequest(BaseModel):
    user_name: str

@app.post("/configure")
async def configure_memory(config: ConfigRequest):
    global memory_clients, dreaming_service, config_timestamps
    character_id = config.character_id
    
    logger.info(f"=== /configure Request Received ===")
    logger.info(f"Character: {character_id}, BaseURL: {config.base_url}, Model: {config.model}")
    
    # 防抖检查
    current_time = time.time()
    last_config_time = config_timestamps[character_id]
    if current_time - last_config_time < CONFIG_COOLDOWN:
        elapsed = int(current_time - last_config_time)
        logger.warning(f"⚠️ Duplicate /configure blocked (last configured {elapsed}s ago)")
        return {
            "status": "skipped", 
            "message": f"Configuration recently updated {elapsed}s ago. Wait {CONFIG_COOLDOWN}s between configurations."
        }
    
    try:
        # 更新时间戳
        config_timestamps[character_id] = current_time
        
        # Close existing instance for this character if exists
        if character_id in memory_clients:
            logger.info(f"Closing existing memory client for '{character_id}'...")
            try:
                memory_clients[character_id].close()
            except Exception as e:
                logger.warning(f"Warning closing client: {e}")
        
        # Initialize new LiteMemory (Primary Owner of DB Lock)
        logger.info(f"Initializing LiteMemory for {character_id}...")
        
        # Create per-character instance
        memory_clients[character_id] = LiteMemory(config.model_dump(), character_id=character_id)
        
        # Initialize Dreaming Service using the SHARED memory client
        # Always re-init dreaming service on configure to ensure it uses the latest memory client
        logger.info(f"Initializing Dreaming Service with shared memory...")
        dreaming_service = DreamingService(
            base_url=config.base_url, 
            api_key=config.api_key,
            memory_client=memory_clients[character_id]
        )
        
        # Save config for auto-load on restart
        try:
            config_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "memory_config.json")
            with open(config_path, 'w', encoding='utf-8') as f:
                json.dump(config.model_dump(), f, indent=4)
            logger.info(f"Saved config to {config_path}")
        except Exception as e:
            logger.warning(f"Failed to save config file: {e}")

        logger.info(f"✅ LiteMemory initialized successfully for '{character_id}'")
        return {"status": "ok", "message": f"Memory configured for {character_id}"}
    except Exception as e:
        logger.error(f"INIT ERROR: {e}")
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/add")
async def add_memory(request: AddMemoryRequest):
    global memory_clients
    character_id = request.character_id
    # print(f"\n--- [API] /add Request Received ---")
    print(f"[API] Character: {character_id}")
    
    client = memory_clients.get(character_id)
    if not client:
        print(f"[API] Error: Memory not configured for character '{character_id}'")
        raise HTTPException(status_code=400, detail=f"Memory not configured for character '{character_id}'. Please call /configure first.")
    
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
            
            # Try to find timestamp
            if "timestamp" in m and timestamp == "unknown":
                timestamp = m["timestamp"]

        # print(f"[API] User Input: {user_input[:50]}...")
        # print(f"[API] AI Response: {ai_response[:50]}...")

        if not user_input and not ai_response:
            # print("[API] Warning: No interaction content found.")
            return {"status": "skipped", "reason": "Empty interaction"}

        # Normalize user input for proactive cases
        if not user_input:
             user_input = "(Silence)"

        # Add to background queue
        task = {
            "user_input": user_input,
            "ai_response": ai_response,
            "timestamp": timestamp,
            "user_name": request.user_name,
            "char_name": request.char_name
        }
        client.add_memory_async(task)
        
        # [Soul Update] 
        # 1. Update timestamp to reset Heartbeat idle timer
        soul_client.update_last_interaction()
        
        # 2. Decrease energy slightly for every interaction
        if ai_response:
             # logger.info(f"[Soul] Interaction detected. Decaying energy (-0.1).")
             soul_client.update_energy(-0.1)
        
        # [Visual Update] Log explicit 'chat' event for Debug UI immediately
        try:
            # Format content similar to what the inspector expects (User/AI pair or single)
            # Now including 'name' for UI display
            
            # 1. Log User Message
            user_json = json.dumps({
                "role": "user", 
                "content": user_input,
                "name": request.user_name
            })
            client.add_event_log(content=user_json, event_type="chat")
            
            # 2. Log AI Message (if exists)
            if ai_response:
                ai_json = json.dumps({
                    "role": "assistant", 
                    "content": ai_response,
                    "name": request.char_name
                })
                client.add_event_log(content=ai_json, event_type="chat")
                
        except Exception as log_e:
            print(f"[API] Warning: Failed to log chat event: {log_e}")
            
        print(f"[API] Memory add task queued for '{character_id}'")
        return {"status": "queued"}
    except Exception as e:
        print(f"[API] ADD ERROR: {e}")
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/consolidate_history")
async def consolidate_history(request: ConsolidateRequest):
    global memory_clients
    try:
        cid = request.character_id
        if cid not in memory_clients:
            raise HTTPException(status_code=400, detail=f"Memory not initialized for character '{cid}'. Call /configure first.")
            
        memory = memory_clients[cid]
        
        print(f"[API] /consolidate_history for '{cid}': Processing {len(request.messages)} messages...")
        
        # Consolidate (Archive) messages to Event Log
        memory.archive_chat_history(request.messages, request.user_name, request.char_name)
        
        return {"status": "success", "archived_count": len(request.messages)}

    except Exception as e:
        print(f"[API] Consolidation Error: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/dream_on_idle")
async def dream_on_idle(request: DreamRequest):
    global dreaming_service
    try:
        print(f"[API] 🌙 Idle Dream Request for '{request.character_id}'")
        
        if not dreaming_service:
             # Try to lazy init if memory client exists?
             # For now, assume initialized by /configure.
             raise HTTPException(status_code=500, detail="DreamingService not initialized. Call /configure first.")

        # Trigger Background Dreaming (Deep Mode)
        # Note: In production, this should be a background task (asyncio.create_task)
        # but for now we run it synchronously to see logs immediately in this demo.
        dreaming_service.wake_up(mode="deep")
        
        return {"status": "success", "message": "Dreaming cycle started"}

    except Exception as e:
        print(f"[API] Dreaming Error: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/all")
async def get_all_memories(character_id: str = "hiyori"):
    """Get all memories from JSONL backup (Legacy/Debug)"""
    print(f"\n--- [API] /all Request Received ---")
    global memory_clients
    client = memory_clients.get(character_id)
    if not client:
        raise HTTPException(status_code=400, detail=f"Memory not configured for character '{character_id}'.")
    
    try:
        memories = []
        # Support reading both user and character backup files for debugging
        files_to_read = [client.character_backup_file, client.user_backup_file]
        
        for fpath in files_to_read:
            if os.path.exists(fpath):
                with open(fpath, "r", encoding="utf-8") as f:
                    for line in f:
                        try:
                            memories.append(json.loads(line))
                        except:
                            pass
        print(f"[API] Found {len(memories)} memories in backup")
        return memories
    except Exception as e:
        print(f"[API] ALL ERROR: {e}")
        return {"error": str(e)}
        return {"error": str(e)}

@app.get("/memory/inspiration")
def get_inspiration(character_id: str = "hiyori", limit: int = 3):
    """
    Returns random facts/memories to inspire proactive conversation.
    """
    if character_id not in memory_clients:
        # Fallback if no client found
        return []
    
    try:
        results = memory_clients[character_id].get_random_inspiration(limit=limit)
        return results
    except Exception as e:
        print(f"[API] Inspiration Error: {e}")
        return []

@app.get("/debug/brain_dump")
def brain_dump(character_id: str = "hiyori"):
    """
    Returns a comprehensive snapshot of the character's memory.
    Returns: { facts: [], graph: {nodes: [], edges: []}, history: [] }
    """
    if character_id not in memory_clients:
        return {
            "status": "not_initialized",
            "message": f"Memory not initialized for '{character_id}'. Please interact with the AI or check configuration.",
            "facts": [],
            "graph": {"nodes": [], "edges": []},
            "history": []
        }
             
    try:
        memory = memory_clients[character_id]
        
        # 1. Fetch Facts (从 facts_staging 表获取已巩固的 Facts)
        facts = memory.sql_db.get_consolidated_facts(limit=50)
        
        # 2. Fetch Graph
        graph = memory.sql_db.view_knowledge_graph(limit=100)

        # 3. Fetch History (Raw Dialog)
        history = memory.sql_db.get_recent_chat_history(limit=50)
        
        return {
            "status": "success",
            "facts": facts,
            "graph": graph,
            "history": history
        }
    except Exception as e:
        print(f"[API] Brain Dump Error: {e}")
        # Return partial success or clear error
        return {
            "status": "error",
            "message": str(e),
            "facts": [],
            "graph": {"nodes": [], "edges": []},
            "history": []
        }

@app.get("/debug/processing_status")
def get_processing_status(character_id: str = "hiyori"):
    """
    Returns real-time status of the three-layer memory processing pipeline.
    Useful for displaying progress bars and monitoring system health.
    """
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
        print(f"[API] Processing Status Error: {e}")
        return {
            "status": "error",
            "message": str(e),
            "conversations": {"unprocessed": 0, "total": 0},
            "facts": {"user": {"unconsolidated": 0, "total": 0}, "character": {"unconsolidated": 0, "total": 0}}
        }

@app.post("/search")
async def search_memory(request: SearchRequest):
    global memory_clients
    character_id = request.character_id
    print(f"\n--- [API] /search Request Received ---")
    print(f"[API] Character: {character_id}")
    print(f"[API] Query: '{request.query}' Limit: {request.limit} UserID: {request.user_id}")
    
    client = memory_clients.get(character_id)
    if not client:
        print(f"[API] Error: Memory not configured for character '{character_id}'")
        raise HTTPException(status_code=400, detail=f"Memory not configured for character '{character_id}'.")
    
    try:
        results = client.search(request.query, limit=request.limit)
        print(f"[API] Search found {len(results)} results for '{character_id}'")
        return results
    except Exception as e:
        print(f"[API] SEARCH ERROR: {e}")
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/search/hybrid")
async def search_memory_hybrid(request: SearchRequest):
    global memory_clients
    character_id = request.character_id
    print(f"\n--- [API] /search/hybrid Request Received ---")
    print(f"[API] Character: {character_id}")
    print(f"[API] Query: '{request.query}' Limit: {request.limit}")
    
    client = memory_clients.get(character_id)
    if not client:
        raise HTTPException(status_code=400, detail=f"Memory not configured for character '{character_id}'.")
    
    try:
        # Call the new hybrid search method
        results = client.search_hybrid(
            request.query, 
            limit=request.limit, 
            empower_factor=request.empower_factor
        )
        print(f"[API] Hybrid Search found {len(results)} results")
        return results
    except Exception as e:
        print(f"[API] HYBRID SEARCH ERROR: {e}")
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=str(e))

# Global Soul Manager definition moved to top

@app.get("/soul")
async def get_soul_state():
    """Returns the current 'Soul File' (Profile) for the frontend."""
    # Force reload from disk to get latest changes (e.g. from Dreaming)
    soul_client.profile = soul_client._load_profile()
    
    # Ensure runtime consistency for frontend
    p = soul_client.profile
    if "relationship" in p:
        # Inject dynamic label
        stage_info = soul_client.get_relationship_stage()
        p["relationship"]["current_stage_label"] = stage_info["label"]
        p["relationship"]["level"] = p["relationship"].get("level", 2)
        p["relationship"]["progress"] = p["relationship"].get("progress", 50)
    
    # Inject dynamic system prompt for frontend LLM (DeepSeek)
    try:
        p["system_prompt"] = soul_client.render_system_prompt()
    except Exception as e:
        print(f"[API] Failed to render system prompt: {e}")
        
    return p

@app.post("/soul/mutate")
async def mutate_soul(pleasure: float = 0, arousal: float = 0, dominance: float = 0, intimacy: float = 0, energy: float = 0):
    """Debug endpoint to manually adjust soul state."""
    if pleasure or arousal or dominance:
        soul_client.mutate_mood(d_p=pleasure, d_a=arousal, d_d=dominance)
    if intimacy:
        soul_client.update_intimacy(intimacy)
    if energy:
        soul_client.update_energy(energy)
    return soul_client.profile

@app.post("/dream/wake_up")
async def trigger_dreaming(background_tasks: BackgroundTasks):
    """Triggers a dreaming cycle to consolidate memory and evolve soul."""
    client = memory_clients.get("hiyori")
    if not client:
        raise HTTPException(status_code=400, detail="Character not found")
        
    def run_dreaming():
         # Re-use existing client to avoid locking
         logger.info("[Task] Starting Dreaming Cycle...")
         try:
             dreamer = DreamingService(memory_client=client)
             dreamer.wake_up()
         except Exception as e:
             logger.error(f"[Task] Dreaming Failed: {e}")
         
    background_tasks.add_task(run_dreaming)
    return {"status": "dreaming_initiated"}

@app.post("/soul/update_identity")
async def update_identity(request: UpdateIdentityRequest):
    """Update identity (name and description) in core_profile.json"""
    try:
        soul_client.profile["identity"]["name"] = request.name
        soul_client.profile["identity"]["description"] = request.description
        soul_client.save_profile()
        logger.info(f"[API] Updated identity: name={request.name}")
        return {"status": "updated", "identity": soul_client.profile["identity"]}
    except Exception as e:
        logger.error(f"[API] Failed to update identity: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/soul/update_user_name")
async def update_user_name(request: UpdateUserNameRequest):
    """Update user_name in core_profile.json"""
    try:
        soul_client.profile["relationship"]["user_name"] = request.user_name
        soul_client.save_profile()
        logger.info(f"[API] Updated user_name: {request.user_name}")
        return {"status": "updated", "user_name": request.user_name}
    except Exception as e:
        logger.error(f"[API] Failed to update user_name: {e}")
        raise HTTPException(status_code=500, detail=str(e))

if __name__ == "__main__":
    uvicorn.run(app, host="127.0.0.1", port=8001)
