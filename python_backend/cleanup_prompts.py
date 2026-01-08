import asyncio
from surreal_memory import SurrealMemory
import logging

# Configure basic logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("Cleanup")

async def main():
    print("🔌 Connecting to SurrealDB for cleanup...")
    surreal = SurrealMemory()
    await surreal.connect()
    
    search_term = "Private System Instruction - DO NOT EXPOSE THIS TO USER"
    
    # 1. Check count
    count_query = f"""
    SELECT count() FROM conversation 
    WHERE 
        ai_response CONTAINS '{search_term}' OR 
        narrative CONTAINS '{search_term}' OR
        user_input CONTAINS '{search_term}';
    """
    
    print("\n🔎 Scanning for leaked prompts...")
    res = await surreal.db.query(count_query)
    print(f"   Scan result: {res}")
    
    # 2. Delete
    delete_query = f"""
    DELETE conversation 
    WHERE 
        ai_response CONTAINS '{search_term}' OR 
        narrative CONTAINS '{search_term}' OR
        user_input CONTAINS '{search_term}';
    """
    
    print(f"\n🗑️ Deleting records containing: '{search_term}' ...")
    await surreal.db.query(delete_query)
    print("✅ Cleanup complete.")

if __name__ == "__main__":
    asyncio.run(main())
