
import os
import uvicorn
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import Dict, Any, List, Optional
import sys
import json

# Add python_backend to path to find local modules if needed
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from lite_memory import LiteMemory

app = FastAPI()

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
    limit: Optional[int] = 5

@app.post("/configure")
async def configure_memory(config: ConfigRequest):
    global memory_clients
    character_id = config.character_id
    print(f"\\n--- [API] /configure Request Received ---")
    print(f"[API] Character: {character_id}")
    print(f"[API] Config Params: BaseURL={config.base_url}, Model={config.model}")
    try:
        # Close existing instance for this character if exists
        if character_id in memory_clients:
            print(f"[API] Closing existing memory client for '{character_id}'...")
            try:
                memory_clients[character_id].close()
            except Exception as e:
                print(f"[API] Warning during close: {e}")
        
        current_dir = os.path.dirname(os.path.abspath(__file__))
        root_dir = os.path.dirname(current_dir)
        db_path = os.path.join(root_dir, "lite_memory_db")

        print(f"[API] DB Path: {db_path}")

        mem_config = {
            "qdrant_path": db_path,
            "openai_base_url": config.base_url,
            "api_key": config.api_key,
            "embedder_model": config.embedder
        }
        
        # Create per-character instance
        memory_clients[character_id] = LiteMemory(mem_config, character_id=character_id)
        print(f"[API] LiteMemory initialized successfully for '{character_id}'")
        return {
            "status": "success", 
            "message": f"LiteMemory initialized for {character_id}",
            "character_id": character_id
        }
    except Exception as e:
        print(f"[API] CRITICAL CONFIG ERROR: {e}")
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/add")
async def add_memory(request: AddMemoryRequest):
    global memory_clients
    character_id = request.character_id
    print(f"\n--- [API] /add Request Received ---")
    print(f"[API] Character: {character_id}")
    
    client = memory_clients.get(character_id)
    if not client:
        print(f"[API] Error: Memory not configured for character '{character_id}'")
        raise HTTPException(status_code=400, detail=f"Memory not configured for character '{character_id}'.")
    
    try:
        user_input = ""
        ai_response = ""
        
        for msg in reversed(request.messages):
            role = msg.get("role")
            content = msg.get("content", "")
            if not ai_response and role == "assistant":
                ai_response = content
            elif not user_input and role == "user":
                user_input = content
            
            if user_input and ai_response:
                break
        
        print(f"[API] User Input: {user_input[:50]}...")
        print(f"[API] AI Response: {ai_response[:50]}...")

        if not user_input:
             print("[API] Warning: No user input found.")
             return {"status": "skipped", "message": "No user input"}

        client.add_memory_async(user_input, ai_response, request.user_name, request.char_name)
        print(f"[API] Memory add task queued for '{character_id}'")
        return {"status": "success", "message": "Memory queued", "character_id": character_id}
    except Exception as e:
        print(f"[API] ADD ERROR: {e}")
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/all")
async def get_all_memories(user_id: str = "user"):
    print(f"\\n--- [API] /all Request Received ---")
    global memory_client
    if not memory_client:
        return {"error": "Memory not configured"}
    
    try:
        memories = []
        backup_path = memory_client.config.get("backup_file")
        if os.path.exists(backup_path):
            with open(backup_path, "r", encoding="utf-8") as f:
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

@app.post("/search")
async def search_memory(request: SearchRequest):
    global memory_clients
    character_id = request.character_id
    print(f"\\n--- [API] /search Request Received ---")
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

if __name__ == "__main__":
    uvicorn.run(app, host="127.0.0.1", port=8001)
