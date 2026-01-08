import asyncio
from surreal_memory import SurrealMemory
import json

async def inspect():
    mem = SurrealMemory()
    await mem.connect()
    
    print("\n=== 1. DB Info ===")
    try:
        info = await mem.db.query("INFO FOR DB;")
        print(json.dumps(info, indent=2, default=str))
    except Exception as e:
        print(f"Info Error: {e}")

    print("\n=== 2. Detailed Edge Inspection ===")
    
    # List all tables first
    tables_info = await mem.db.query("INFO FOR DB;")
    
    tables_dict = {}
    # Robust extraction of tables
    if isinstance(tables_info, list) and tables_info:
        # Check first element
        res = tables_info[0]
        # 'result' (python client) or 'status' (http)
        if hasattr(res, 'get') and res.get('result'):
            tables_dict = res['result'].get('tables', {})
        elif hasattr(res, 'get') and res.get('tables'): # Sometimes direct result
             tables_dict = res.get('tables', {})
    elif isinstance(tables_info, dict):
        if 'result' in tables_info:
            tables_dict = tables_info['result'].get('tables', {})
        elif 'tables' in tables_info:
            tables_dict = tables_info.get('tables', {})

    # Filter out known non-edge tables
    edge_tables = [t for t in tables_dict.keys() if t not in ['conversation', 'character', 'entity', 'insight', 'user_entity', 'observes', 'derived_from']]
    
    print(f"Found Edge Tables: {edge_tables}")

    for t in edge_tables:
        print(f"\n--- Edges in Table '{t}' ---")
        try:
            edges = await mem.db.query(f"SELECT id, in, out FROM {t} LIMIT 5;")
            if edges and isinstance(edges, list) and len(edges) > 0 and edges[0].get('result'):
                for e in edges[0]['result']:
                    print(e)
            else:
                print("(Empty)")
        except Exception as e:
            print(f"Error querying {t}: {e}")

    print("\n=== 3. Evidence Chain (DERIVED_FROM) ===")
    res = await mem.db.query("SELECT * FROM derived_from")
    print(json.dumps(res, indent=2, default=str))

    print("\n=== 4. Does Hiyori observe Insights? ===")
    res = await mem.db.query("SELECT * FROM observes WHERE out CONTAINS 'insight'")
    print(json.dumps(res, indent=2, default=str))

    await mem.close()

if __name__ == "__main__":
    asyncio.run(inspect())
