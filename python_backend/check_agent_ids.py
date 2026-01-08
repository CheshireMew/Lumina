import asyncio
from surrealdb import AsyncSurreal

async def check_agent_ids():
    db = AsyncSurreal("ws://localhost:8000/rpc")
    await db.connect()
    await db.signin({"username": "root", "password": "root"})
    await db.use("lumina", "memory")
    
    # Check agent_ids in conversation table
    print("=" * 50)
    print("1. Agent IDs in conversation table:")
    r = await db.query("SELECT agent_id, count() FROM conversation GROUP BY agent_id")
    for item in r if isinstance(r, list) else [r]:
        print(f"   {item}")
    
    # Check character nodes
    print("\n" + "=" * 50)
    print("2. Character nodes:")
    r2 = await db.query("SELECT id FROM character LIMIT 10")
    for item in r2 if isinstance(r2, list) else [r2]:
        print(f"   {item}")
    
    # Check observes edges with in details
    print("\n" + "=" * 50)
    print("3. observes edges (sample - checking 'in' format):")
    r3 = await db.query("SELECT id, in, out FROM observes LIMIT 10")
    for item in r3 if isinstance(r3, list) else [r3]:
        print(f"   {item}")
    
    # Count observes by character
    print("\n" + "=" * 50)
    print("4. observes grouped by 'in' (observer):")
    r4 = await db.query("SELECT in, count() FROM observes GROUP BY in")
    for item in r4 if isinstance(r4, list) else [r4]:
        print(f"   {item}")
    
    await db.close()

asyncio.run(check_agent_ids())

