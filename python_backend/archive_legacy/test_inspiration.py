"""
SurrealDB Inspiration Retrieval Diagnostic Script
诊断从知识图谱获取随机 Inspiration 的问题
"""

import asyncio
from surrealdb import AsyncSurreal

SURREAL_URL = "ws://localhost:8000/rpc"
NAMESPACE = "lumina"
DATABASE = "memory"
CHARACTER_ID = "lillian"

async def main():
    print("=" * 60)
    print("SurrealDB Inspiration Diagnostic")
    print("=" * 60)
    
    db = AsyncSurreal(SURREAL_URL)
    
    try:
        await db.connect()
        await db.signin({"username": "root", "password": "root"})
        await db.use(NAMESPACE, DATABASE)
        print("✅ Connected to SurrealDB\n")
        
        # ==================== Test 1: List All Tables ====================
        print("=" * 60)
        print("[Test 1] List All Tables")
        print("=" * 60)
        
        info = await db.query("INFO FOR DB;")
        print(f"INFO result type: {type(info)}")
        
        tables_map = {}
        if isinstance(info, dict):
            tables_map = info.get('tables', {})
        elif isinstance(info, list) and len(info) > 0:
            item = info[0]
            if isinstance(item, dict):
                if 'result' in item:
                    tables_map = item['result'].get('tables', {})
                else:
                    tables_map = item.get('tables', {})
        
        print(f"Found {len(tables_map)} tables: {list(tables_map.keys())}")
        
        # Identify edge tables (lowercase, not in known non-edge list)
        known_non_edge = ["conversation", "entity", "character", "user", "user_entity", "memory_embeddings", "migrations"]
        edge_tables = [t for t in tables_map.keys() if t not in known_non_edge]
        print(f"Potential edge tables: {edge_tables}")
        
        # ==================== Test 2: Check observes table ====================
        print("\n" + "=" * 60)
        print("[Test 2] Check 'observes' Table")
        print("=" * 60)
        
        try:
            obs_query = f"""
            SELECT * FROM observes 
            WHERE in = character:{CHARACTER_ID}
            LIMIT 5;
            """
            obs_result = await db.query(obs_query)
            print(f"observes result type: {type(obs_result)}")
            
            # Parse
            obs_records = []
            if isinstance(obs_result, list):
                if len(obs_result) > 0 and isinstance(obs_result[0], dict) and 'result' in obs_result[0]:
                    obs_records = obs_result[0]['result']
                else:
                    obs_records = obs_result
            
            print(f"Found {len(obs_records)} observes edges for {CHARACTER_ID}:")
            for i, rec in enumerate(obs_records[:3]):
                print(f"  [{i+1}] in: {rec.get('in')}, out: {rec.get('out')}")
        except Exception as e:
            print(f"❌ observes query failed: {e}")
        
        # ==================== Test 3: Query Edge Tables Directly ====================
        print("\n" + "=" * 60)
        print("[Test 3] Query Edge Tables Directly (Sample)")
        print("=" * 60)
        
        for tbl in edge_tables[:3]:  # Limit to 3
            if tbl == 'observes':
                continue
            try:
                q = f"SELECT * FROM {tbl} LIMIT 3;"
                r = await db.query(q)
                
                records = []
                if isinstance(r, list):
                    if len(r) > 0 and isinstance(r[0], dict) and 'result' in r[0]:
                        records = r[0]['result']
                    else:
                        records = r
                
                print(f"\n  Table '{tbl}': {len(records)} sample records")
                if records:
                    sample = records[0]
                    print(f"    Sample fields: {list(sample.keys())[:8]}...")
                    print(f"    in: {sample.get('in')}, out: {sample.get('out')}")
                    print(f"    context: {str(sample.get('context'))[:60]}...")
            except Exception as e:
                print(f"  ❌ {tbl} query failed: {e}")
        
        # ==================== Test 4: The Actual Inspiration Query ====================
        print("\n" + "=" * 60)
        print("[Test 4] Inspiration Query (Matching get_random_inspiration)")
        print("=" * 60)
        
        for tbl in edge_tables[:3]:
            if tbl == 'observes':
                continue
            try:
                # This is the actual query from get_random_inspiration
                q = f"""
                    SELECT * FROM {tbl} 
                    WHERE id IN (SELECT VALUE out FROM observes WHERE in = character:{CHARACTER_ID})
                    ORDER BY rand() 
                    LIMIT 3;
                """
                r = await db.query(q)
                
                records = []
                if isinstance(r, list):
                    if len(r) > 0 and isinstance(r[0], dict) and 'result' in r[0]:
                        records = r[0]['result']
                    else:
                        records = r
                
                print(f"\n  {tbl} (via observes): {len(records)} results")
                for rec in records:
                    subj = str(rec.get('in', '')).replace('entity:', '')
                    obj = str(rec.get('out', '')).replace('entity:', '')
                    ctx = rec.get('context', '')
                    print(f"    - {subj} --[{tbl}]--> {obj}: {str(ctx)[:50]}...")
                    
            except Exception as e:
                print(f"  ❌ {tbl} inspiration query failed: {e}")
        
        # ==================== Summary ====================
        print("\n" + "=" * 60)
        print("[Summary]")
        print("=" * 60)
        if not edge_tables:
            print("⚠️ No edge tables found! The knowledge graph may be empty.")
        elif 'observes' not in tables_map:
            print("⚠️ 'observes' table missing! Character->Fact observation links are needed.")
        else:
            print("✅ Edge tables and observes table exist. Check the query results above.")
        
    except Exception as e:
        print(f"❌ Connection/Query Error: {e}")
        import traceback
        traceback.print_exc()
    finally:
        await db.close()
        print("\n✅ Connection closed")

if __name__ == "__main__":
    asyncio.run(main())
