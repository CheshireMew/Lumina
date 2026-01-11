import asyncio
import logging
from memory.connection import DBConnection
from app_config import config

logging.basicConfig(level=logging.INFO)

async def debug_db():
    print("--- Debugging SurrealDB ---")
    await DBConnection.connect()
    db = await DBConnection.get_db()
    
    # 1. List Tables
    try:
        print("\n[Query] INFO FOR DB:")
        info = await db.query("INFO FOR DB;")
        print(info)
    except Exception as e:
        print(f"Info query failed: {e}")

    # 2. Count Logs
    try:
        print("\n[Query] SELECT count() FROM conversation_log:")
        count = await db.query("SELECT count() FROM conversation_log GROUP ALL;")
        print(count)
    except Exception as e:
        print(f"Count query failed: {e}")
        
    # 3. Sample Log
    try:
        print("\n[Query] SELECT * FROM conversation_log LIMIT 1:")
        sample = await db.query("SELECT * FROM conversation_log LIMIT 1;")
        print(sample)
    except Exception as e:
        print(f"Sample query failed: {e}")

    await DBConnection.close()

if __name__ == "__main__":
    asyncio.run(debug_db())
