import asyncio
from surrealdb import Surreal, AsyncSurreal

async def main():
    conn_str = "ws://127.0.0.1:8000/rpc"
    async with AsyncSurreal(conn_str) as db:
        await db.signin({"username": "root", "password": "root"})
        
        # Debug: List Info
        # note: surrealdb python sdk might not have direct 'info' wrapper, use query
        try:
             info_ns = await db.query("INFO FOR SU;")
             print(f"馃實 Root Info: {info_ns}")
        except Exception as e:
             print(f"Could not get root info: {e}")

        await db.use("lumina", "memory")
        
        info_db = await db.query("INFO FOR DB;")
        print(f"馃搧 DB Info: {info_db}")
        
        tables = ["character", "user", "fact", "observes", "about"]
        
        print("\n馃搳 SurrealDB Database Inventory:")
        print("-" * 40)
        
        for table in tables:
            # SurrealQL: SELECT count() FROM table GROUP ALL
            # Or just select * and count in python for small db
            try:
                # Try raw select first
                result = await db.query(f"SELECT * FROM {table} LIMIT 1;")
                
                item_count = "Unknown"
                if result and isinstance(result, list):
                     first = result[0]
                     if 'result' in first:
                         res_list = first['result']
                         if res_list:
                             item_count = "> 0 (Data Exists)"
                         else:
                             item_count = "0 (Empty)"
                
                print(f"馃摝 {table.ljust(15)}: {item_count}")
            except Exception as e:
                print(f"鉂?{table.ljust(15)}: Error ({e})")

        print("-" * 40)

if __name__ == "__main__":
    import sys
    if sys.platform == 'win32':
        asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())
    asyncio.run(main())
