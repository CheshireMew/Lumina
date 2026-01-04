
import os
import sys
import shutil
import time
from datetime import datetime, timedelta
import uuid

# Add directory to path
current_dir = os.path.dirname(os.path.abspath(__file__))
sys.path.append(current_dir)

from lite_memory import LiteMemory
from memory_consolidator import MemoryConsolidator
from qdrant_client.http import models

def test_weighted_retrieval():
    print("\n=== TEST 1: Weighted Retrieval ===")
    
    # 1. Setup Config
    config = {
        "qdrant_path": "./test_lite_memory_db", 
        "openai_base_url": "https://api.deepseek.com/v1",
        "api_key": "YOUR_API_KEY", # !!! Needs real key or mock
        "embedder_model": "sangmini/msmarco-cotmae-MiniLM-L12_en-ko-ja"
    }
    
    # Clean prev DB
    if os.path.exists("./test_lite_memory_db"):
        shutil.rmtree("./test_lite_memory_db")
        
    memory = LiteMemory(config, character_id="test_char")
    
    # 2. Inject Conflicting Facts with different Timestamps
    # "Autumn" was 2 days ago
    t1 = (datetime.now() - timedelta(hours=48)).isoformat()
    # "Summer" was 1 hour ago
    t2 = (datetime.now() - timedelta(hours=1)).isoformat()
    
    print(f"Injecting 'User like Autumn' at {t1}")
    print(f"Injecting 'User like Summer' at {t2}")

    # Manually upsert to control timestamp
    
    # Old Fact
    memory.client.upsert(
        collection_name=memory.user_collection_name,
        points=[
            models.PointStruct(
                id=str(uuid.uuid4()),
                vector=memory.encoder.encode("User's favorite season is Autumn").tolist(),
                payload={"text": "User's favorite season is Autumn", "timestamp": t1}
            )
        ]
    )
    
    # New Fact
    memory.client.upsert(
        collection_name=memory.user_collection_name,
        points=[
            models.PointStruct(
                id=str(uuid.uuid4()),
                vector=memory.encoder.encode("User's favorite season is Summer").tolist(),
                payload={"text": "User's favorite season is Summer", "timestamp": t2}
            )
        ]
    )
    
    # 3. Search
    print("Searching for 'User favorite season'...")
    results = memory.search("User favorite season", limit=2)
    
    for i, res in enumerate(results):
        print(f"Result {i+1}: {res['text']} (Score: {res['score']:.4f}, Orig: {res.get('original_score', 'N/A'):.4f})")
        
    # Validation
    top_text = results[0]['text']
    if "Summer" in top_text:
        print("✅ PASS: 'Summer' is ranked higher due to Time Decay.")
    else:
        print("❌ FAIL: 'Autumn' is still top ranked.")
        
    memory.close()

def test_consolidation_trigger():
    print("\n=== TEST 2: Memory Consolidation ===")
    
    config = {
        "qdrant_path": "./test_lite_memory_db_consol", 
        "openai_base_url": "https://api.deepseek.com/v1",
        "api_key": "sk-dummy", # Using dummy to test Trigger logic only (unless we have real key)
        "embedder_model": "sangmini/msmarco-cotmae-MiniLM-L12_en-ko-ja"
    }
    
    if os.path.exists("./test_lite_memory_db_consol"):
        shutil.rmtree("./test_lite_memory_db_consol")
        
    memory = LiteMemory(config, character_id="test_char")
    
    # Manually lower threshold for test
    memory.consolidator.consolidation_threshold = 5 
    print(f"Consolidation Threshold set to: {memory.consolidator.consolidation_threshold}")
    
    # Inject 4 dummy facts
    for i in range(4):
        memory.client.upsert(
            collection_name=memory.user_collection_name,
            points=[
                models.PointStruct(
                    id=str(uuid.uuid4()),
                    vector=memory.encoder.encode(f"Fact {i}").tolist(),
                    payload={"text": f"Fact {i}", "timestamp": datetime.now().isoformat()}
                )
            ]
        )
        
    count_before = memory.client.count(memory.user_collection_name).count
    print(f"Count before 5th insert: {count_before}")
    
    # Inject 5th fact -> Should Trigger
    print("Injecting 5th fact...")
    # We call _handle_consolidation explicitly to test the logic block
    # In real flow it's called after add_task
    
    memory.client.upsert(
            collection_name=memory.user_collection_name,
            points=[
                models.PointStruct(
                    id=str(uuid.uuid4()),
                    vector=memory.encoder.encode(f"Fact 5").tolist(),
                    payload={"text": f"Fact 5", "timestamp": datetime.now().isoformat()}
                )
            ]
        )
    
    # Mocking LLM response in Consolidator to avoid API cost/auth issues in test
    original_llm_consolidate = memory.consolidator._llm_consolidate
    memory.consolidator._llm_consolidate = lambda x: ["Consolidated Fact A", "Consolidated Fact B"]
    
    print("Triggering Consolidation Check...")
    memory._handle_consolidation(memory.user_collection_name, memory.user_backup_file)
    
    # Check Count (Should be 2 now: A and B)
    count_after = memory.client.count(memory.user_collection_name).count
    print(f"Count after consolidation: {count_after}")
    
    if count_after == 2:
        print("✅ PASS: Consolidation triggered and replaced 5 facts with 2.")
    else:
        print(f"❌ FAIL: Count is {count_after}, expected 2.")
        
    memory.close()

if __name__ == "__main__":
    test_weighted_retrieval()
    test_consolidation_trigger()
