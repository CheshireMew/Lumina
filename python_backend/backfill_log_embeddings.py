import asyncio
import logging
from memory.core import SurrealMemory
from memory.connection import DBConnection
from app_config import config
from sentence_transformers import SentenceTransformer

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("Backfill")

async def backfill_embeddings():
    print("[INFO] Starting Backfill Process...")
    
    # 1. Connect DB
    await DBConnection.connect()
    
    # 2. Init Encoder
    print(f"[INFO] Loading Encoder: {config.models.embedding_model_name}")
    try:
        model_path = config.paths.models_dir / config.models.embedding_model_name
        encoder_model = SentenceTransformer(str(model_path))
        
        def encoder(text):
            if not text: return []
            return encoder_model.encode(text).tolist()
            
        print("✅ Encoder Loaded")
    except Exception as e:
        print(f"❌ Failed to load encoder: {e}")
        return
        
    db = await DBConnection.get_db()
    
    # 3. Fetch Logs
    print("Fetching conversation logs...")
    
    # Check count
    try:
        count_res = await db.query("SELECT count() FROM conversation_log")
        # SurrealDB response parsing
        if count_res and isinstance(count_res, list) and count_res[0].get('result'):
            total = count_res[0]['result'][0].get('count', 0)
            print(f"Total Logs found: {total}")
        else:
            print("Could not query count, proceeding blindly.")
    except Exception as e:
        print(f"Count query failed: {e}")
    
    # Process in batches
    BATCH_SIZE = 50
    OFFSET = 0
    
    processed_count = 0
    
    while True:
        # Fetch batch
        query = f"SELECT id, narrative FROM conversation_log START {OFFSET} LIMIT {BATCH_SIZE}"
        results = await db.query(query)
        
        # Robust Parsing (Match VectorStore logic)
        items = []
        if results:
            if isinstance(results, list):
                if isinstance(results[0], dict) and 'result' in results[0]:
                    items = results[0]['result']
                else:
                    items = results
            elif isinstance(results, dict) and 'result' in results:
                items = results['result']
                
        if not items:
            # Debug: Print why it's empty if it's the first batch
            if OFFSET == 0:
                print(f"[DEBUG] Raw Response for first batch: {results}")
            break
            
        processed_in_batch = 0
        
        for item in items:
            log_id = item['id']
            narrative = item.get('narrative', '')
            
            if not narrative or len(narrative.strip()) < 2:
                continue
                
            try:
                # Generate Embedding
                vec = encoder(narrative)
                
                # Update DB
                await db.query(f"UPDATE {log_id} SET embedding = $vec", {"vec": vec})
                processed_in_batch += 1
            except Exception as ex:
                print(f"[ERROR] processing {log_id}: {ex}")
        
        processed_count += processed_in_batch
        print(f"Processed batch {OFFSET}-{OFFSET+BATCH_SIZE}: Updated {processed_in_batch} records")
        
        OFFSET += BATCH_SIZE
        
        if len(items) < BATCH_SIZE:
             break

    print(f"✅ Backfill Complete! Updated {processed_count} logs.")
    await DBConnection.close()

if __name__ == "__main__":
    asyncio.run(backfill_embeddings())
