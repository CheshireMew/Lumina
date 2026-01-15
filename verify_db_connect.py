import sys
import os
import asyncio
import traceback

# Add current dir to path
sys.path.append(os.path.join(os.getcwd(), 'python_backend'))

from app_config import config
from surrealdb import AsyncSurreal

async def test_connect():
    print(f"--- Configuration Check ---")
    print(f"Memory URL: {config.memory.url}")
    print(f"User: {config.memory.user}")
    print(f"Pass: {config.memory.password}")
    print(f"Namespace: {config.memory.namespace}")
    print(f"Database: {config.memory.database}")
    print("-" * 30)

    url = config.memory.url
    db = AsyncSurreal(url)
    
    print(f"Attempting connection to {url}...")
    try:
        await asyncio.wait_for(db.connect(), timeout=5.0)
        print("✅ Connection Established (Socket Open)")
        
        await db.signin({
            "username": config.memory.user,
            "password": config.memory.password
        })
        print("✅ Signin Successful")
        
        await db.use(config.memory.namespace, config.memory.database)
        print("✅ Namespace Selected")
        
        # Test Query
        res = await db.query("INFO FOR DB;")
        print(f"✅ Query Result: {res}")
        
        await db.close()
        print("✅ Connection Closed cleanly")
        
    except Exception as e:
        print(f"❌ CONNECTION FAILED: {e}")
        traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(test_connect())
