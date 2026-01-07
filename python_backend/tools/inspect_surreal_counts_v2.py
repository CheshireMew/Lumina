import asyncio
import sys
import os

# Add parent dir to path to import backend modules
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from surreal_memory import SurrealMemory

async def main():
    print("Initializing SurrealMemory...")
    # Use exact same defaults: lumina/memory
    mem = SurrealMemory()
    await mem.connect()
    
    print("✅ Connected. Querying 'fact' table...")
    
    try:
        # 1. Count Facts
        # Note: SELECT count() FROM fact GROUP ALL returns [{count: 90}]
        res_count = await mem.db.query("SELECT count() FROM fact GROUP ALL;")
        count = 0
        if isinstance(res_count, list) and len(res_count) > 0:
             # SDK 1.x returns the data rows directly in a list for query()
             # Wait, usuallySDK .query() returns [ {result: [], status: "OK"}, ... ]
             # BUT the previous debug showed: DEBUG RAW RESPONSE: [{'count': 90}]
             # This means the SDK is indeed unwrapping.
             count = res_count[0].get('count', 0)
        print(f"📊 Total Facts: {count}")
        
        # 2. Sample Data
        res_sample = await mem.db.query("SELECT * FROM fact LIMIT 3;")
        if isinstance(res_sample, list) and len(res_sample) > 0:
            print("\n📝 Sample Entries:")
            for s in res_sample:
                txt = s.get('text', 'N/A')
                print(f" - [{s['id']}] {txt[:50]}...")
        else:
            print("\n⚠️ No data found in 'fact' table via query.")

        # 3. Verify Graph Edges
        res_edges = await mem.db.query("SELECT count() FROM observes GROUP ALL;")
        edge_count = 0
        if isinstance(res_edges, list) and len(res_edges) > 0:
             edge_count = res_edges[0].get('count', 0)
        print(f"\n🔗 Graph Connections (Edges): {edge_count}")
        if edge_count > 0:
            print("   ✅ Graph structure is ACTIVE. Memories are linked to characters.")
        else:
            print("   ⚠️ Graph structure MISSING. Memories are isolated nodes.")

    except Exception as e:
        print(f"❌ Query Error: {e}")
    finally:
        await mem.close()

if __name__ == "__main__":
    if sys.platform == 'win32':
        asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())
    asyncio.run(main())
