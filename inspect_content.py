
import sys
import os
sys.path.append(os.path.join(os.getcwd(), "python_backend"))
from python_backend.time_indexed_memory import TimeIndexedMemory

db_path = "memory_db/lumina_memory.db"
tm = TimeIndexedMemory(db_path)

print("\n--- memories (type='dialogue') sample ---")
mems = tm.get_recent_memories(character_id="lillian", limit=5, memory_type="dialogue")
for m in mems:
    print(f"Content: '{m['content']}'")

print("\n--- Checking Separator ---")
if mems:
    c = mems[0]['content']
    if ": " in c:
        print("Standard ': ' found")
    elif "：" in c:
        print("Chinese '：' found")
    else:
        print("No separator found!")
