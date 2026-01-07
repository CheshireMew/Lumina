import asyncio
import logging
from surreal_memory import SurrealMemory

# Configure logging
logging.basicConfig(level=logging.INFO)

async def main():
    print("🧪 Testing SurrealMemory Class...")
    
    # Initialize Service
    memory = SurrealMemory(url="ws://127.0.0.1:8000/rpc", user="root", password="root")
    
    try:
        # 1. Connect & Init
        await memory.connect()
        
        # 2. Add Memories
        print("\n📝 Adding Memories...")
        # Character: Lillian
        await memory.add_memory(
            content="User loves cyberpunk aesthetics.",
            embedding=[0.1, 0.2, 0.3, 0.4], # Mock 4D vector
            agent_id="lillian",
            importance=8,
            emotion="excited"
        )
        
        # Character: Hiyori (Different perspective)
        await memory.add_memory(
            content="User seems interested in retro tech.",
            embedding=[0.1, 0.2, 0.35, 0.4], # Similar vector
            agent_id="hiyori",
            importance=5,
            emotion="curious"
        )

        # 3. Search (Lillian)
        print("\n🔍 Searching as Lillian...")
        query_vec = [0.1, 0.2, 0.3, 0.4]
        results_lillian = await memory.search(query_vec, agent_id="lillian", limit=5)
        print(f"Result Count: {len(results_lillian)}")
        for r in results_lillian:
            print(f" - {r['text']} (Score: {r['score']:.4f})")
            
        # 4. Search (Hiyori)
        print("\n🔍 Searching as Hiyori...")
        results_hiyori = await memory.search(query_vec, agent_id="hiyori", limit=5)
        print(f"Result Count: {len(results_hiyori)}")
        for r in results_hiyori:
            print(f" - {r['text']} (Score: {r['score']:.4f})")
            
        # Verify isolation: Lillian should see hers (and maybe public), Hiyori sees hers.
        # In current logic, they see their own observations.
        
        print("\n✅ Service Test Complete")

    except Exception as e:
        print(f"\n❌ Test Failed: {e}")
    finally:
        await memory.close()

if __name__ == "__main__":
    asyncio.run(main())
