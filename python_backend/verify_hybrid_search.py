import requests
import json
import time
import logging

# Setup Logger
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger("HybridTest")

BASE_URL = "http://127.0.0.1:8010"
CHAR_ID = "hiyori"

def add_memory(content: str):
    """Add a memory via API"""
    url = f"{BASE_URL}/add"
    payload = {
        "character_id": CHAR_ID,
        "user_name": "Tester",
        "character_name": "Hiyori",
        "messages": [
            {"role": "user", "content": content},
            {"role": "assistant", "content": "Acknowledged."} # Needed to form a pair
        ]
    }
    try:
        resp = requests.post(url, json=payload)
        resp.raise_for_status()
        logger.info(f"✅ Added memory: '{content}'")
        return True
    except Exception as e:
        logger.error(f"❌ Failed to add memory: {e}")
        if 'resp' in locals():
            logger.error(f"Response Body: {resp.text}")
        return False

def search_hybrid(query: str):
    """Perform hybrid search"""
    url = f"{BASE_URL}/search/hybrid"
    payload = {
        "query": query,
        "character_id": CHAR_ID,
        "user_id": "user",
        "limit": 5
    }
    
    try:
        resp = requests.post(url, json=payload)
        resp.raise_for_status()
        results = resp.json()
        logger.info(f"🔍 Search for '{query}' returned {len(results)} results")
        return results
    except Exception as e:
        import traceback
        traceback.print_exc()
        logger.error(f"❌ Search failed: {e}")
        return []

def main():
    print(f"--- Starting Hybrid Search Verification for '{CHAR_ID}' ---")
    
    # 1. Insert Test Data (Designed to test Semantic vs Keyword)
    # Keyword hit: "Quantum", "Mechanics"
    # Semantic hit: "Physics of small particles" (no keyword overlap)
    
    t1 = "Dr. Hiyori is studying Quantum Mechanics in the lab."
    t2 = "The physics of very small particles is fascinating." 
    
    # We need 20+ items to trigger 'Dreaming' extractor
    # logger.info("📦 Seeding 20+ memories to trigger Dreaming threshold...")
    # add_memory(t1)
    # add_memory(t2)
    
    # for i in range(25):
    #     add_memory(f"Filler memory {i}: The weather is nice today.")
    #     time.sleep(0.1)
    
    # Wait for processing? 
    # The /memory/add endpoint writes to conversation_log immediately.
    # But Hybrid Search usually targets 'episodic_memory' or 'conversation_log'?
    # Let's check the API: /search/hybrid targets episodic_memory by default, 
    # but falls back to conversation_log if Free Tier.
    # Assuming standard setup: we might need to wait for consolidation if targeting episodic.
    # BUT, the generic search usually searches logs or immediate memories?
    # Let's check routers/memory.py:
    # It tries `target_table = "episodic_memory"`
    # But if Free Tier, `target_table = "conversation_log"`.
    # AND, `conversation_log` has embeddings generated synchronously in `log_conversation`.
    # So we should be able to search `conversation_log` if we force it or if the system uses it.
    
    # Force Digest to ensure episodic memory is populated
    try:
        requests.post(f"{BASE_URL}/debug/force_digest")
        logger.info("⏳ Triggered Force Digest...")
    except Exception as e:
        logger.warning(f"Digest failed: {e}")

    # Wait for async processing
    time.sleep(10) 
    
    # DEBUG: Check counts
    try:
        r1 = requests.get(f"{BASE_URL}/admin/table/conversation_log?limit=1&character_id={CHAR_ID}")
        c1 = r1.json().get('count', 0)
        logger.info(f"📊 Conversation Logs: {c1}")
        
        r2 = requests.get(f"{BASE_URL}/admin/table/episodic_memory?limit=1&character_id={CHAR_ID}")
        c2 = r2.json().get('count', 0)
        logger.info(f"📊 Episodic Memories: {c2}")
    except Exception as e:
        logger.warning(f"Failed to check counts: {e}")

    # 2. Search
    query = "玉子烧" # Exact match from screenshot 
    # Should hit t1 (Quantum keyword) and t2 (physics/particle keywords + semantic)
    
    # DEBUG: Check character_id format
    url_sql = f"{BASE_URL}/admin/query"
    try:
        # Check what the character_id actually looks like
        sql = f"SELECT character_id, type::string(character_id) as str_id FROM episodic_memory LIMIT 3;"
        resp = requests.post(url_sql, json={"query": sql})
        data = resp.json()
        logger.info(f"🆔 Character ID Check: {json.dumps(data, ensure_ascii=False, indent=2)}")
    except Exception as ex:
        logger.error(f"ID Check failed: {ex}")

    results = search_hybrid(query)
    
    print("\n--- Results ---")
    for i, res in enumerate(results):
        print(f"[{i+1}] Score: {res.get('score'):.4f} | Content: {res.get('content')[:100]}...")
        
    if len(results) > 0:
        print("\n✅ Hybrid Search Test Passed: Results returned.")
    else:
        print("\n⚠️ No results found. Ensure embedding model is loaded and data is persistent.")

if __name__ == "__main__":
    main()
