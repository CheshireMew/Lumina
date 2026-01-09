"""
检查 SurrealDB 数据库内容
"""
import asyncio
from surrealdb import AsyncSurreal

SURREAL_URL = "ws://127.0.0.1:8000/rpc"

async def check():
    db = AsyncSurreal(SURREAL_URL)
    await db.connect()
    await db.signin({"username": "root", "password": "root"})
    await db.use("lumina", "memory")
    
    print("=== SurrealDB 数据检查 ===\n")
    
    # 列出所有表
    tables = await db.query("INFO FOR DB;")
    print("数据库信息:")
    print(tables)
    
    # 检查 conversation 表
    print("\n--- conversation 表 ---")
    conv = await db.query("SELECT count() FROM conversation GROUP ALL;")
    print(f"conversation: {conv}")
    
    # 检查 conversation_log 表
    print("\n--- conversation_log 表 ---")
    log = await db.query("SELECT count() FROM conversation_log GROUP ALL;")
    print(f"conversation_log: {log}")
    
    # 检查 episodic_memory 表
    print("\n--- episodic_memory 表 ---")
    mem = await db.query("SELECT count() FROM episodic_memory GROUP ALL;")
    print(f"episodic_memory: {mem}")
    
    await db.close()

if __name__ == "__main__":
    asyncio.run(check())
