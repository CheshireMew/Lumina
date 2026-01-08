"""
Verify SurrealMemory Fix
直接调用 SurrealMemory 类方法来验证 Inspiration 获取逻辑（包括 fallback）
"""
import asyncio
import logging
from surreal_memory import SurrealMemory

# 设置日志以便看到 fallback 的 info
logging.basicConfig(level=logging.INFO)

async def main():
    print("=" * 60)
    print("Verifying SurrealMemory.get_random_inspiration Fix")
    print("=" * 60)
    
    # Initialize SurrealMemory
    mem = SurrealMemory(url="ws://localhost:8000/rpc", db_namespace="lumina", db_name="memory")
    await mem.connect()
    
    try:
        # Test getting inspiration for 'lillian' (who likely has no observes relations)
        print("\nTesting get_random_inspiration('lillian')...")
        results = await mem.get_random_inspiration(character_id="lillian", limit=5)
        
        print("\n" + "-" * 30)
        print(f"Results Found: {len(results)}")
        print("-" * 30)
        
        for i, res in enumerate(results):
            print(f"[{i+1}] {res['relation']}: {res['subject']} -> {res['object']}")
            print(f"    Context: {res['context'][:50]}...")
            
        if len(results) > 0:
            print("\n✅ SUCCESS: Inspiration retrieved (likely via fallback)!")
        else:
            print("\n❌ RETURNED 0 RESULTS. Fallback might have failed.")
            
    except Exception as e:
        print(f"❌ ERROR: {e}")
        import traceback
        traceback.print_exc()
    finally:
        # Close (well, no explicit close method, usually done via connection object)
        pass

if __name__ == "__main__":
    asyncio.run(main())
