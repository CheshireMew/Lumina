import sqlite3
import asyncio
import os
import sys

# Ensure local imports work
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from surreal_memory import SurrealMemory

# Path to legacy DB (relative to python_backend usually, or project root)
# If running from python_backend folder:
LEGACY_DB_REL = "../memory_db/lumina_memory.db"

async def migrate():
    base_dir = os.path.dirname(os.path.abspath(__file__))
    db_path = os.path.join(base_dir, LEGACY_DB_REL)
    
    if not os.path.exists(db_path):
        print(f"❌ Legacy DB not found at: {db_path}")
        # Try absolute path fallback if running from root
        db_path = os.path.join(base_dir, "memory_db", "lumina_memory.db")
        if not os.path.exists(db_path):
             print(f"❌ Legacy DB not found at fallback: {db_path}")
             return

    print(f"📦 Migrating from {db_path}...")
    
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    
    # [Debug] List Tables
    try:
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table';")
        tables = [r['name'] for r in cursor.fetchall()]
        print(f"🔎 Found tables: {tables}")
        
        target_table = "conversation_buffer" # Correct table name from TimeIndexedMemory
        if target_table not in tables:
            print(f"❌ Error: Table '{target_table}' not found in DB.")
            print(f"   Available tables: {tables}")
            return
    except Exception as e:
         print(f"❌ Failed to inspect tables: {e}")
         return
         
    try:
        cursor.execute(f"SELECT * FROM {target_table}")
        rows = cursor.fetchall()
        print(f"📄 Found {len(rows)} legacy conversations in '{target_table}'.")
    except Exception as e:
        print(f"❌ Failed to read source: {e}")
        return
    
    surreal = SurrealMemory(url="ws://127.0.0.1:8000/rpc", user="root", password="root")
    
    try:
        print("🔌 Connecting to SurrealDB...")
        await surreal.connect()

        # [Cleanup] Remove previous migration attempts to avoid duplicates
        print("🧹 Cleaning up previous migration data...")
        await surreal.db.query("DELETE conversation WHERE source = 'legacy_migration'")
        
        count = 0
        skipped = 0
        from datetime import datetime
        
        for row in rows:
            try:
                # Validation & Sanitization
                u_in = row["user_input"] if row["user_input"] else ""
                ai_res = row["ai_response"] if row["ai_response"] else ""
                
                if not u_in and not ai_res:
                    skipped += 1
                    continue
                    
                # Fix Timestamp (Data Type Issue)
                ts_raw = row["timestamp"]
                try:
                    if isinstance(ts_raw, (int, float)):
                        ts_clean = datetime.fromtimestamp(ts_raw).isoformat()
                    else:
                        ts_clean = ts_raw.replace(' ', 'T') if ' ' in ts_raw else ts_raw
                except:
                    ts_clean = datetime.now().isoformat()
                
                # Construct Narrative (For UI visibility)
                # Format: [Time] User: Input...
                user_name = row["user_name"] if "user_name" in row.keys() else "User"
                char_name = row["char_name"] if "char_name" in row.keys() else "AI"
                
                narrative = f"[{ts_clean[:16].replace('T', ' ')}] {user_name}: {u_in}\n[{ts_clean[:16].replace('T', ' ')}] {char_name}: {ai_res}"

                # Map fields
                data = {
                    "user_input": str(u_in),
                    "ai_response": str(ai_res),
                    "narrative": narrative, # ADDED: Required for Explorer UI
                    "created_at": ts_clean,
                    "agent_id": row["char_name"] if "char_name" in row.keys() and row["char_name"] else "default",
                    "user_name": str(user_name),
                    "is_processed": False, # TRIGGER RE-DREAMING
                    "source": "legacy_migration"
                }
                
                # Create
                await surreal.db.create("conversation", data)
                count += 1
                
                if count % 10 == 0:
                    print(f"   Saved {count}...", end='\r')

                    
            except Exception as row_err:
                print(f"⚠️ Error migrating row {row['id']}: {row_err}")
                
        print(f"\n✅ Migration Complete.")
        print(f"   Transferred: {count}")
        print(f"   Skipped: {skipped}")
        print(f"\n🚀 Next Step: Restart Backend. The Hippocampus will now 'Re-Dream' these memories into the Knowledge Graph over time.")
        
    except Exception as e:
        print(f"❌ Migration failed: {e}")
    finally:
        if surreal.db:
            await surreal.db.close()
        conn.close()

if __name__ == "__main__":
    asyncio.run(migrate())
