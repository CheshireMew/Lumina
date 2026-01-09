import asyncio
import json
import os
from surrealdb import AsyncSurreal

SUB_NAMESPACE = "lumina"
SUB_DB = "memory"

async def main():
    print("--- 🔍 Entity Merge Diagnostic Tool ---")
    
    # 1. Connect
    print(f"Connecting to SurrealDB (ws://localhost:8000/rpc)...")
    db = AsyncSurreal("ws://localhost:8000/rpc")
    try:
        await db.connect()
        await db.signin({"username": "root", "password": "root"})
        await db.use(SUB_NAMESPACE, SUB_DB)
        print("✅ Connected!")
    except Exception as e:
        print(f"❌ Connection failed: {e}")
        return

    # 2. Load Aliases
    aliases_path = os.path.join(os.path.dirname(__file__), "config", "entity_aliases.json")
    if not os.path.exists(aliases_path):
        print(f"❌ Aliases file not found at: {aliases_path}")
        return
        
    with open(aliases_path, 'r', encoding='utf-8') as f:
        aliases = json.load(f)
        
    print(f"Loaded {len(aliases)} aliases from config.")
    
    # 3. Diagnose Each Alias
    def parse_res(res):
        print(f"    [DEBUG] Raw Response: {res}")
        if not res: return []
        if isinstance(res, list):
            if len(res) > 0 and isinstance(res[0], dict) and 'result' in res[0]:
                return res[0]['result']
            return res
        if isinstance(res, dict) and 'result' in res:
            return res['result']
        return []

    for alias, canonical in aliases.items():
        if alias not in ['柴郡', 'Hiyori', 'Cheshire']: continue
        print(f"\n[Alias: '{alias}' -> Canonical: '{canonical}']")
        
        found_alias_id = None
        
        # A. Name Lookup
        q1 = f"SELECT id, name FROM entity WHERE name = '{alias}'"
        print(f"  > Query Name: {q1}")
        try:
            res1 = await db.query(q1)
            rows = parse_res(res1)
            if rows:
                print(f"    ✅ FOUND BY NAME! ID: {rows[0]['id']}")
                found_alias_id = rows[0]['id']
            else:
                print(f"    ❌ Not found by name.")
        except Exception as e:
            print(f"    ❌ Query failed: {e}")

        # B. ID Lookup (Raw)
        if not found_alias_id:
             id_raw = f"entity:{alias}"
             q2 = f"SELECT id, name FROM {id_raw}"
             print(f"  > Query ID (Raw): {q2}")
             try:
                 res2 = await db.query(q2)
                 rows = parse_res(res2)
                 if rows:
                     print(f"    ✅ FOUND BY RAW ID! ID: {rows[0]['id']}")
                     found_alias_id = rows[0]['id']
                 else:
                     print(f"    ❌ Not found by Raw ID.")
             except Exception as e:
                 print(f"    ❌ Query failed: {e}")

        # C. ID Lookup (Bracketed)
        if not found_alias_id:
             id_brack = f"entity:⟨{alias}⟩"
             q3 = f"SELECT id, name FROM {id_brack}"
             print(f"  > Query ID (Bracketed): {q3}")
             try:
                 res3 = await db.query(q3)
                 rows = parse_res(res3)
                 if rows:
                     print(f"    ✅ FOUND BY BRACKET ID! ID: {rows[0]['id']}")
                     found_alias_id = rows[0]['id']
                 else:
                     print(f"    ❌ Not found by Bracketed ID.")
             except Exception as e:
                 print(f"    ❌ Query failed: {e}")


    await db.close()
    print("\nDone.")

if __name__ == "__main__":
    asyncio.run(main())
