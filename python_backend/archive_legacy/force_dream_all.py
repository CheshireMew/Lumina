import asyncio
import logging
from surreal_memory import SurrealMemory
from hippocampus import Hippocampus

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger("ForceDream")

async def main():
    print("🧠 Initializing Batch Dreamer...")
    
    # Init components
    mem = SurrealMemory()
    await mem.connect()
    
    hippo = Hippocampus(memory_client=mem)
    
    # 1. Check count
    count_query = "SELECT count() FROM conversation WHERE is_processed = false;"
    res = await mem.db.query(count_query)
    
    # Debug response structure if needed
    # print(f"DEBUG Response: {res}")

    total = 0
    try:
        if isinstance(res, list) and len(res) > 0:
            item = res[0]
            if 'result' in item:
                # Standard Wrapper: [{'result': [{'count': 50}], ...}]
                inner = item['result']
                if inner and isinstance(inner, list):
                    total = inner[0].get('count', 0)
            elif 'count' in item:
                # Direct unwrapped: [{'count': 50}]
                total = item['count']
    except Exception as e:
        print(f"⚠️ Error parsing count: {e}. Raw: {res}")

    print(f"📊 Found {total} unprocessed memories.")
    
    if total == 0:
        print("✅ Nothing to do.")
        return

    batch_size = 5
    print(f"🚀 Starting processing (Batch Size: {batch_size})...")
    
    processed = 0
    while processed < total:
        print(f"\n⚡ Processing batch {processed + 1} - {processed + batch_size} ...")
        
        # force=True skips the "accumulating" check
        # We assume process_memories processes 'batch_size' items
        # But process_memories fetches 'limit=batch_size'. 
        
        try:
            await hippo.process_memories(batch_size=batch_size, force=True)
            processed += batch_size
            # Small delay to let DB breathe
            await asyncio.sleep(1)
        except Exception as e:
            print(f"❌ Error in batch: {e}")
            break
            
    print("\n✅ Batch processing complete.")

if __name__ == "__main__":
    asyncio.run(main())
