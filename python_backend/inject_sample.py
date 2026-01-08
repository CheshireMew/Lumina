import asyncio
from surreal_memory import SurrealMemory

async def inject():
    print("Injecting sample memory for demonstration...")
    mem = SurrealMemory()
    await mem.connect()
    # Inject conversation for Multi-Speaker Test
    narrative = "[2026-01-08 18:00] 柴郡: 只要是博多拉面我都喜欢，特别是浓汤的。 [2026-01-08 18:01] hiyori: 我更喜欢清淡一点的酱油拉面呢。"
    query = f"INSERT INTO conversation {{ narrative: '{narrative}', created_at: time::now(), is_processed: false, agent_id: 'hiyori' }};"
    await mem.db.query(query)
    print("Injected.")
    await mem.close()

if __name__ == "__main__":
    asyncio.run(inject())
