"""
Cleanup Script: Remove legacy tables and graph data from SurrealDB
This script removes:
1. Old 'conversation' table (replaced by conversation_log)
2. Old 'fact' table
3. All graph edge tables (LIKES, OBSERVES, etc.)
4. Entity tables
"""
import asyncio
from surrealdb import AsyncSurreal

SURREAL_URL = "ws://127.0.0.1:8000/rpc"
SURREAL_USER = "root"
SURREAL_PASS = "root"
NAMESPACE = "lumina"
DATABASE = "memory"


async def main():
    print("🧹 Starting SurrealDB Cleanup...")
    
    db = AsyncSurreal(SURREAL_URL)
    await db.connect()
    await db.signin({"username": SURREAL_USER, "password": SURREAL_PASS})
    await db.use(NAMESPACE, DATABASE)
    
    # Get all tables
    result = await db.query("INFO FOR DB;")
    print(f"DEBUG: result type={type(result)}, value={result}")
    
    # Parse tables from result
    all_tables = []
    if isinstance(result, dict) and 'tables' in result:
        all_tables = list(result['tables'].keys())
    elif isinstance(result, list) and len(result) > 0:
        first = result[0]
        if isinstance(first, dict):
            if 'result' in first:
                tables_info = first['result']
            else:
                tables_info = first
            if isinstance(tables_info, dict) and 'tables' in tables_info:
                all_tables = list(tables_info['tables'].keys())
    
    print(f"📋 Found {len(all_tables)} tables in database")
    
    # Tables to KEEP (our new dual-table architecture)
    keep_tables = {
        'conversation_log',  # New raw log table
        'episodic_memory',   # New processed memory table
    }
    
    # Tables to DELETE
    tables_to_delete = [t for t in all_tables if t not in keep_tables]
    
    print(f"\n🗑️ Tables to DELETE ({len(tables_to_delete)}):")
    for t in sorted(tables_to_delete):
        print(f"   - {t}")
    
    print(f"\n✅ Tables to KEEP ({len(keep_tables)}):")
    for t in sorted(keep_tables):
        if t in all_tables:
            print(f"   - {t}")
    
    # Confirm deletion
    confirm = input("\n⚠️ Type 'DELETE' to confirm deletion: ")
    if confirm.strip() != "DELETE":
        print("❌ Aborted.")
        await db.close()
        return
    
    # Delete tables
    deleted_count = 0
    for table in tables_to_delete:
        try:
            await db.query(f"REMOVE TABLE {table};")
            print(f"   ✅ Deleted: {table}")
            deleted_count += 1
        except Exception as e:
            print(f"   ⚠️ Failed to delete {table}: {e}")
    
    print(f"\n🎉 Cleanup complete! Deleted {deleted_count} tables.")
    
    # Show remaining tables
    result = await db.query("INFO FOR DB;")
    remaining = result[0].get('result', {}).get('tables', {}) if result else {}
    print(f"\n📋 Remaining tables: {list(remaining.keys())}")
    
    await db.close()


if __name__ == "__main__":
    asyncio.run(main())
