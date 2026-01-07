
import sys
import os
sys.path.append(os.path.join(os.getcwd(), "python_backend"))

try:
    from python_backend.time_indexed_memory import TimeIndexedMemory
    print("✅ Successfully imported TimeIndexedMemory")
except Exception as e:
    print(f"❌ Syntax Error or Import Error: {e}")
    exit()

db_path = "memory_db/lumina_memory.db"
if not os.path.exists(db_path):
    print("DB not found")
    exit()

tm = TimeIndexedMemory(db_path)

print("\n--- Testing get_recent_chat_history('lillian') ---")
try:
    history = tm.get_recent_chat_history(limit=5, character_id="lillian")
    print(f"Found {len(history)} records.")
    for h in history:
        print(f"Type: {h['event_type']}, Content: {h['content'][:30]}...")
except Exception as e:
    print(f"❌ Method call failed: {e}")

print("\n--- Testing get_consolidated_facts('lillian') ---")
try:
    facts = tm.get_consolidated_facts(limit=5, source_name="lillian")
    print(f"Found {len(facts)} facts.")
except Exception as e:
    print(f"❌ get_consolidated_facts failed: {e}")
