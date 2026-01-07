
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
            
            # ⚡ Fix: Re-init soul_client to match the saved character_id
            soul_client = SoulManager(character_id=character_id)
            print(f"[API] SoulManager initialized for '{character_id}'")
            
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
    # Heartbeat Settings
    # Heartbeat Settings
    heartbeat_enabled: Optional[bool] = None
    proactive_threshold_minutes: Optional[float] = None
    
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
    global memory_clients, dreaming_service, config_timestamps, soul_client, heartbeat_service_instance
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
        
        # ⚡ CRITICAL FIX: Enforce Single Active Instance
        # Qdrant local storage locks the folder. We cannot have multiple LiteMemory instances 
        # open on the same folder even for different characters.
        # We must verify if ANY client is open and close it.
        if memory_clients:
            logger.info(f"Closing ALL existing memory clients to release Qdrant lock ({len(memory_clients)} active)...")
            # Create a list of keys to avoid runtime error during modification
            active_ids = list(memory_clients.keys())
            for active_id in active_ids:
                try:
                    logger.info(f"Closing client for '{active_id}'...")
                    memory_clients[active_id].close()
                except Exception as e:
                    logger.warning(f"Error closing client '{active_id}': {e}")
            memory_clients.clear()
            
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
        
        # ⚡ Soul & Heartbeat Reload
        # Since SoulManager is character-specific, we MUST reload it.
        logger.info(f"Switching SoulManager to '{character_id}'...")
        soul_client = SoulManager(character_id=character_id)
        
        # ⚡ Update Soul Config with Heartbeat Settings
        # ⚡ Update Soul Config with Heartbeat Settings (Only if provided)
        if config.heartbeat_enabled is not None:
            soul_client.config["heartbeat_enabled"] = config.heartbeat_enabled
        if config.proactive_threshold_minutes is not None:
            soul_client.config["proactive_threshold_minutes"] = config.proactive_threshold_minutes
        soul_client.save_config() # Persist to characters/{id}/config.json
        
        # Restart Heartbeat Service with new Soul
        if heartbeat_service_instance:
            logger.info("Restarting Heartbeat Service for new character...")
            try:
                heartbeat_service_instance.stop()
            except: pass
        
        heartbeat_service_instance = HeartbeatService(soul_client)
        heartbeat_service_instance.start()
        
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
        
        # 1. Fetch Consolidated Core Facts (from facts_staging and vector store meta)
        # These are facts explicitly extracted and consolidated.
        facts = memory.sql_db.get_consolidated_facts(limit=100, source_name=character_id)
        
        # ⚡ Fetch User Facts (source_name='User')
        user_facts = memory.sql_db.get_consolidated_facts(limit=100, source_name="User")

        # 2. Fetch Knowledge Graph (Short-term context edges)
        # Filter edges by character_id
        # graph = memory.sql_db.view_knowledge_graph(limit=100, character_id=character_id)
        graph = {"edges": [], "nodes": []} # Disabled Graph

        # 3. Fetch History (Clean Dialogue from Memory Store)
        # Use 'memories' table instead of raw 'memory_events' log to avoid duplicate/merged logs
        raw_history = memory.sql_db.get_recent_memories(character_id=character_id, limit=100, memory_type="dialogue")
        
        # Post-process for Frontend (MemoryInspector.tsx)
        # Frontend expects: { timestamp, role, content (or content as JSON with name/role) }
        history = []
        for h in raw_history:
            item = {
                "timestamp": h["created_at"], # Map created_at -> timestamp
                "content": h["content"],
                "role": "assistant" if h.get("type") == "dialogue" else "system" 
            }
            
            # Parsing "Name: Message" format stored in LiteMemory
            # Format usually: "User: Hello" or "Character: Hi"
            if ": " in h["content"]:
                parts = h["content"].split(": ", 1)
                name = parts[0]
                text = parts[1]
                
                item["role"] = name # Use name as role for display
                item["name"] = name
                item["content"] = text
                
            history.append(item)
        
        
        return {
            "status": "success",
            "facts": facts,
            "user_facts": user_facts, # Add User Facts
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

# ==================== Character Management API ====================

@app.get("/characters")
async def list_characters():
    """列出所有可用角色"""
    try:
        from pathlib import Path
        chars_dir = Path("python_backend/characters")
        characters = []
        
        if chars_dir.exists():
            for char_dir in chars_dir.iterdir():
                if char_dir.is_dir():
                    config_path = char_dir / "config.json"
                    if config_path.exists():
                        try:
                            with open(config_path, 'r', encoding='utf-8') as f:
                                config = json.load(f)
                                characters.append(config)
                        except Exception as e:
                            logger.error(f"[API] Error loading character config for {char_dir.name}: {e}")
                            # Skip corrupted character but continue listing others
                            continue
        
        return {"characters": characters}
    except Exception as e:
        logger.error(f"[API] Error listing characters: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/characters/{character_id}/config")
async def get_character_config(character_id: str):
    """获取角色配置（Settings界面使用）"""
    try:
        from soul_manager import SoulManager
        soul = SoulManager(character_id)
        return soul.config
    except Exception as e:
        print(f"[API] Error getting character config: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/characters/{character_id}/config")
async def update_character_config(character_id: str, config: dict):
    """更新角色配置（Settings界面保存）"""
    try:
        logger.info(f"[API] update_character_config for: {character_id}")
        # logger.info(f"[API] Payload: {json.dumps(config, ensure_ascii=False)}")
        
        from soul_manager import SoulManager
        soul = SoulManager(character_id)
        
        # Ensure directory exists (in case it's a new character being saved purely by config update)
        if not soul.base_dir.exists():
            logger.info(f"[API] {character_id} directory missing, creating...")
            soul.base_dir.mkdir(parents=True, exist_ok=True)
            
        soul.config.update(config)
        soul.save_config()
        
        # ⚡ Fix: Sync with global soul_client if it's the active character
        # This ensures HeartbeatService sees the new settings immediately without restart
        global soul_client
        if soul_client and soul_client.character_id == character_id:
             soul_client.config.update(config)
             logger.info(f"[API] Synced config to active soul_client (Heartbeat Updated)")

        logger.info(f"[API] Config saved for {character_id}")
        return {"status": "ok", "character_id": character_id}
    except Exception as e:
        logger.error(f"[API] Error updating character config: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.delete("/characters/{character_id}")
async def delete_character(character_id: str):
    """删除角色"""
    try:
        from pathlib import Path
        import shutil
        
        # Prevent deleting default character
        if character_id == "hiyori":
             raise HTTPException(status_code=400, detail="Cannot delete default character 'hiyori'")
             
        char_dir = Path(f"python_backend/characters/{character_id}")
        
        if char_dir.exists() and char_dir.is_dir():
            shutil.rmtree(char_dir)
            logger.info(f"[API] Deleted character directory: {char_dir}")
            
            # Remove from memory clients if active
            if character_id in memory_clients:
                del memory_clients[character_id]
                
            return {"status": "ok", "message": f"Character {character_id} deleted"}
        else:
            return {"status": "skipped", "message": "Character not found"}
            
    except Exception as e:
        print(f"[API] Error deleting character: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/soul/{character_id}")
async def get_soul_data(character_id: str):
    """获取AI演化的性格数据（只读）"""
    try:
        from soul_manager import SoulManager
        soul = SoulManager(character_id)
        return soul.soul
    except Exception as e:
        print(f"[API] Error getting soul data: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/galgame/{character_id}/state")
async def get_galgame_state(character_id: str):
    """获取GalGame状态"""
    try:
        from soul_manager import SoulManager
        soul = SoulManager(character_id)
        return soul.state.get("galgame", {})
    except Exception as e:
        print(f"[API] Error getting galgame state: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/galgame/{character_id}/state")
async def update_galgame_state(character_id: str, state_update: dict):
    """更新GalGame状态"""
    try:
        from soul_manager import SoulManager
        soul = SoulManager(character_id)
        soul.state.setdefault("galgame", {}).update(state_update)
        soul.save_state()
        return {"status": "ok", "character_id": character_id}
    except Exception as e:
        print(f"[API] Error updating galgame state: {e}")
        raise HTTPException(status_code=500, detail=str(e))

# ==================== Legacy Soul API (Backward Compatible) ====================

@app.get("/soul")
async def get_soul():
    """获取Soul状态（使用全局 soul_client）"""
    try:
        global soul_client
        
        # ✅ 使用全局 soul_client，而不是创建新的 hiyori 实例
        # 重新加载以获取最新数据（如Dreaming更新）
        soul_client.soul = soul_client._load_soul()
        soul_client.state = soul_client._load_state()
        soul_client.profile = soul_client._merge_profile()
        
        # 注入关系标签
        if "relationship" in soul_client.profile:
            stage_info = soul_client.get_relationship_stage()
            soul_client.profile["relationship"]["current_stage_label"] = stage_info["label"]
        
        # 注入动态 system prompt
        try:
            soul_client.profile["system_prompt"] = soul_client.render_system_prompt()
        except Exception as e:
            print(f"[API] Failed to render system prompt: {e}")
        
        return soul_client.profile
    except Exception as e:
        print(f"[API] Error in /soul endpoint: {e}")
        raise HTTPException(status_code=500, detail=str(e))
        
@app.post("/soul/mutate")
async def mutate_soul(pleasure: float = 0, arousal: float = 0, dominance: float = 0, intimacy: float = 0, energy: float = 0, clear_pending: bool = False):
    """Debug endpoint to manually adjust soul state."""
    if pleasure or arousal or dominance:
        soul_client.mutate_mood(d_p=pleasure, d_a=arousal, d_d=dominance)
    if intimacy:
        soul_client.update_intimacy(intimacy)
    if energy:
        soul_client.update_energy(energy)
    if clear_pending:
        soul_client.set_pending_interaction(False)
    return soul_client.profile

class SwitchCharacterRequest(BaseModel):
    character_id: str

@app.post("/soul/switch_character")
async def switch_character(request: SwitchCharacterRequest):
    """切换到指定角色"""
    global soul_client, memory_clients, dreaming_service, config_timestamps, heartbeat_service_instance
    
    try:
        character_id = request.character_id
        logger.info(f"[API] Switching to character: {character_id}")
        
        # ⚡ 重置防抖时间戳，允许后续的 /configure 调用
        config_timestamps[character_id] = 0.0
        
        # 1. 重新初始化 SoulManager
        soul_client = SoulManager(character_id=character_id)
        
        # 重新加载数据
        soul_client.soul = soul_client._load_soul()
        soul_client.state = soul_client._load_state()
        soul_client.profile = soul_client._merge_profile()
        
        character_name = soul_client.profile.get("identity", {}).get("name", character_id)
        
        logger.info(f"[API] ✅ Switched to character: {character_name}")
        
        # 2. ⚡ 重要：同时初始化 Memory Client
        # 从配置文件读取 API 配置
        config_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "memory_config.json")
        if os.path.exists(config_path):
            try:
                with open(config_path, 'r', encoding='utf-8') as f:
                    saved_config = json.load(f)
                
                # 关闭旧的 memory clients（释放 Qdrant 锁）
                if memory_clients:
                    logger.info(f"Closing {len(memory_clients)} existing memory clients...")
                    for old_id in list(memory_clients.keys()):
                        try:
                            memory_clients[old_id].close()
                        except Exception as e:
                            logger.warning(f"Error closing '{old_id}': {e}")
                    memory_clients.clear()
                
                # 更新 character_id 并初始化新的 LiteMemory
                saved_config["character_id"] = character_id
                memory_clients[character_id] = LiteMemory(saved_config, character_id=character_id)
                
                # 重新初始化 Dreaming Service
                dreaming_service = DreamingService(
                    base_url=saved_config["base_url"],
                    api_key=saved_config["api_key"],
                    memory_client=memory_clients[character_id]
                )
                
                # 3. ⚡ 更新 Heartbeat Service 的 Soul 引用
                if heartbeat_service_instance:
                    heartbeat_service_instance.soul = soul_client
                    logger.info(f"[API] Heartbeat service updated to track character: {character_id}")

                logger.info(f"[API] Memory, Dreaming, and Heartbeat initialized for '{character_id}'")
            except Exception as e:
                logger.error(f"[API] Failed to init memory for '{character_id}': {e}")
                import traceback
                traceback.print_exc()
        else:
            logger.warning(f"[API] No saved config found. Memory not initialized.")
        
        return {
            "status": "success",
            "character_id": character_id,
            "character_name": character_name,
            "system_prompt": soul_client.render_system_prompt()
        }
    except Exception as e:
        logger.error(f"[API] Failed to switch character: {e}")
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=str(e))



@app.post("/dream/wake_up")
async def trigger_dreaming(background_tasks: BackgroundTasks):
    """Triggers a dreaming cycle to consolidate memory and evolve soul."""
    global memory_clients, dreaming_service
    
    # 动态获取当前活跃的 client
    active_client = None
    character_id = None
    
    if memory_clients:
        # 获取第一个（应该是唯一的）client
        character_id, active_client = next(iter(memory_clients.items()))
        logger.info(f"[API] Triggering dream for active character: {character_id}")
    
    if not active_client:
        logger.warning("[API] No active memory client found for dreaming.")
        raise HTTPException(status_code=400, detail="No active character memory found")
        
    def run_dreaming():
         # Re-use existing client to avoid locking
         logger.info(f"[Task] Starting Dreaming Cycle for {character_id}...")
         try:
             # 使用全局的 dreaming_service 或重新创建
             if dreaming_service and dreaming_service.memory == active_client:
                 dreamer = dreaming_service
             else:
                 dreamer = DreamingService(memory_client=active_client)
                 
             dreamer.wake_up()
         except Exception as e:
             logger.error(f"[Task] Dreaming Failed: {e}")
             import traceback
             traceback.print_exc()
         
    background_tasks.add_task(run_dreaming)
    return {"status": "dreaming_initiated", "character_id": character_id}

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
