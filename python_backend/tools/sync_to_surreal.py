import asyncio
import sys
import os
import logging

# Add parent dir to path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from surreal_memory import SurrealMemory
from lite_memory import LiteMemory
# We need to load config to init LiteMemory correctly
import json

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("SyncTool")

async def main():
    print("🚀 Starting Data Sync: Qdrant -> SurrealDB")
    
    # 1. Initialize SurrealMemory
    surreal = SurrealMemory(url="ws://127.0.0.1:8000/rpc", user="root", password="root")
    try:
        await surreal.connect()
        # [Fix] Drop incompatible index from previous tests
        print("🧹 Cleaning up old schema (Dimension Mismatch)...")
        try:
             await surreal.db.query("REMOVE TABLE fact;")
             # await surreal.db.query("REMOVE INDEX fact_embedding ON TABLE fact;") 
        except Exception as e:
             logger.warning(f"Cleanup warning: {e}")
             
        # Re-initialize schema with correct 384 dim
        await surreal._initialize_schema()
        
    except Exception as e:
        logger.error(f"Failed to connect to SurrealDB: {e}")
        return

    # 2. Initialize LiteMemory (Read-Only context preferably, but we just need search/scroll)
    # Load config
    config_path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "memory_config.json")
    if not os.path.exists(config_path):
        logger.error("No memory_config.json found")
        return
        
    with open(config_path, 'r', encoding='utf-8') as f:
        config_data = json.load(f)
        
    character_id = config_data.get("character_id", "hiyori")
    print(f"Reading from source character: {character_id}")
    
    # Init existing memory system
    # Note: This might conflict if memory_server is running and holding locks on Qdrant.
    # We should use read-only if possible or handle locks.
    # Qdrant local file lock is strict. 
    # IF memory_server is running, we cannot open LiteMemory on same path easily.
    
    # Strategy: Use Qdrant Client HTTP if possible? No, we use local disk.
    # If using local disk, only one process can access.
    
    # ALTERNATIVE: Use the API of the running server to fetch memories? 
    # Or just warn user to stop server. 
    # Since we just started the server, this script WILL fail to lock Qdrant.
    
    # For now, let's implement the logic but assume server is stopped OR 
    # we export data via API.
    
    # Let's try to initialize. If it fails, we tell user to stop server.
    try:
        source_memory = LiteMemory(config_data, character_id=character_id)
    except Exception as e:
        logger.error(f"❌ Could not open Source Memory (Qdrant/SQLite): {e}")
        logger.warning("⚠️ If Memory Server is running, stop it before running this sync tool.")
        await surreal.close()
        return

    # 3. Iterate and Sync
    try:
        # Qdrant 'scroll' or iterate
        # LiteMemory doesn't expose scroll directly, but we can access `.client`
        client = source_memory.client
        collection_name = source_memory.character_collection_name
        
        print(f"Scrolling collection: {collection_name}...")
        
        offset = None
        count = 0
        
        # We need a loop to scroll all points
        # Qdrant client scroll API: client.scroll(collection_name, limit=100, with_payload=True, with_vectors=True, offset=offset)
        # Note: local qdrant client might simplify this.
        
        # Note: qdrant_client.scroll returns (points, next_page_offset)
        
        next_offset = None
        while True:
            records, next_offset = client.scroll(
                collection_name=collection_name,
                limit=50,
                with_payload=True,
                with_vectors=True,
                scroll_filter=None,
                offset=next_offset
            )
            
            for record in records:
                # payload: {text, metadata, ...}
                payload = record.payload or {}
                text = payload.get("text", "")
                embedding = record.vector
                
                if not text:
                    continue
                    
                # Sync to Surreal
                # Mapping:
                # agent_id -> character_id
                # importace -> from payload or default
                
                # Check if already exists? (Deduplication based on text hash? or just add)
                # SurrealDB add_memory generates new ID.
                # To prevent duplicates, we might want to check exact text match? 
                # For migration, we assume fresh start or overwrite.
                
                await surreal.add_memory(
                    content=text,
                    embedding=embedding,
                    agent_id=character_id, # Source character
                    importance=payload.get("importance", 1),
                    emotion=payload.get("emotion", None)
                )
                count += 1
                if count % 10 == 0:
                    print(f"Synced {count} memories...")

            if next_offset is None:
                break
                
        print(f"✅ Sync Complete. Total: {count}")

    except Exception as e:
        logger.error(f"Sync failed: {e}")
    finally:
        # source_memory.close() # if available
        await surreal.close()

if __name__ == "__main__":
    asyncio.run(main())
