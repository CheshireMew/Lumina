
import sqlite3
import os

db_path = "memory_db/lumina_memory.db"

if not os.path.exists(db_path):
    print(f"Database not found at {db_path}")
    exit()

conn = sqlite3.connect(db_path)
conn.row_factory = sqlite3.Row
cursor = conn.cursor()

print("=== Memory Events (Recent 10) ===")
try:
    cursor.execute("SELECT event_id, event_type, character_id, content FROM memory_events ORDER BY timestamp DESC LIMIT 10")
    rows = cursor.fetchall()
    for row in rows:
        print(f"ID: {row['event_id']}, Type: {row['event_type']}, CharID: '{row['character_id']}', Content: {row['content'][:30]}...")
except Exception as e:
    print(f"Error querying memory_events: {e}")


print(f"\n=== Simulating Brain Dump for character_id='lillian' ===")
try:
    # 模拟 get_recent_chat_history
    sql = """
        SELECT * FROM memory_events 
        WHERE event_type IN ('user_interaction', 'archived_chat', 'chat')
        AND (character_id = ?)
        ORDER BY timestamp DESC LIMIT 50
    """
    cursor.execute(sql, ('lillian',))
    rows = cursor.fetchall()
    print(f"Found {len(rows)} history events for lillian.")
    for row in rows[:3]:
        print(f" - [{row['timestamp']}] {row['event_type']}: {row['content'][:30]}...")
        
    if len(rows) == 0:
        print("⚠️ No history found! Checking if they have NULL character_id...")
        sql_null = "SELECT COUNT(*) FROM memory_events WHERE character_id IS NULL"
        cursor.execute(sql_null)
        print(f"Events with NULL character_id: {cursor.fetchone()[0]}")

except Exception as e:
    print(f"Error simulating brain dump: {e}")
