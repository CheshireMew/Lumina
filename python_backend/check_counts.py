"""Quick check of table counts in SurrealDB"""
import asyncio
from surrealdb import AsyncSurreal

async def check():
    db = AsyncSurreal("ws://127.0.0.1:8000/rpc")
    await db.connect()
    await db.signin({"username": "root", "password": "root"})
    await db.use("lumina", "memory")
    
    r1 = await db.query("SELECT count() FROM conversation_log GROUP ALL")
    r2 = await db.query("SELECT count() FROM episodic_memory GROUP ALL")
    
    print(f"conversation_log: {r1}")
    print(f"episodic_memory: {r2}")
    
    await db.close()

asyncio.run(check())
