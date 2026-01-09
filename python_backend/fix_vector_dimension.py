"""
修复 episodic_memory 向量索引维度
从 1024 改为 384（匹配 paraphrase-multilingual-MiniLM-L12-v2 模型）
"""
import asyncio
from surrealdb import AsyncSurreal

async def fix_vector_dimension():
    db = AsyncSurreal("ws://127.0.0.1:8000/rpc")
    
    try:
        await db.signin({"username": "root", "password": "root"})
        await db.use("lumina", "memory")
        
        print("Connected to SurrealDB")
        
        # 1. 删除旧的向量索引
        print("Removing old index...")
        await db.query("REMOVE INDEX mem_embedding ON episodic_memory;")
        
        # 2. 创建新的 384 维向量索引
        print("Creating new 384-dim index...")
        await db.query("""
            DEFINE INDEX mem_embedding ON episodic_memory FIELDS embedding 
            MTREE DIMENSION 384 DIST COSINE TYPE F32;
        """)
        
        print("✅ Vector index updated to 384 dimensions!")
        
        # 清空现有的 episodic_memory（因为维度不匹配）
        result = await db.query("SELECT count() as c FROM episodic_memory GROUP ALL;")
        print(f"Current episodic_memory count: {result}")
        
        # 询问是否清空
        print("\n⚠️ 如果现有 episodic_memory 有 1024 维向量数据，需要清空表")
        print("运行: DELETE episodic_memory;")
        
    except Exception as e:
        print(f"Error: {e}")
    finally:
        await db.close()

if __name__ == "__main__":
    asyncio.run(fix_vector_dimension())
