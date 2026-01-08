"""
SurrealDB Data Migration Script
数据迁移脚本: 规范化 agent_id 并补充 observes 关系

执行内容:
1. 规范化 conversation 表中的 agent_id 为小写
2. 规范化 character 节点 ID 为小写
3. 为现有边补充 observes 关系（如果缺失）

警告: 请在执行前备份数据库!
"""

import asyncio
from surrealdb import AsyncSurreal
from datetime import datetime

SURREAL_URL = "ws://localhost:8000/rpc"
NAMESPACE = "lumina"
DATABASE = "memory"

async def main():
    print("=" * 60)
    print("SurrealDB Data Migration - Normalize Agent IDs")
    print("=" * 60)
    
    db = AsyncSurreal(SURREAL_URL)
    
    try:
        await db.connect()
        await db.signin({"username": "root", "password": "root"})
        await db.use(NAMESPACE, DATABASE)
        print("✅ Connected to SurrealDB\n")
        
        # ==================== Step 1: Normalize agent_id in conversation table ====================
        print("[Step 1] Normalizing agent_id in conversation table...")
        
        # Get all distinct agent_ids
        r = await db.query("SELECT agent_id, count() FROM conversation GROUP BY agent_id")
        print(f"Current agent_ids: {r}")
        
        # Find non-lowercase agent_ids
        agent_ids_to_fix = []
        if isinstance(r, list):
            for item in r:
                aid = item.get('agent_id', '')
                if aid and aid != aid.lower():
                    agent_ids_to_fix.append(aid)
        
        if agent_ids_to_fix:
            print(f"⚡ Found {len(agent_ids_to_fix)} agent_ids to normalize: {agent_ids_to_fix}")
            
            for old_id in agent_ids_to_fix:
                new_id = old_id.lower()
                # Update all conversations with this agent_id
                update_query = f"""
                UPDATE conversation SET agent_id = $new_id 
                WHERE agent_id = $old_id
                """
                result = await db.query(update_query, {"old_id": old_id, "new_id": new_id})
                print(f"  ✅ Updated '{old_id}' → '{new_id}': {result}")
        else:
            print("  ✅ All agent_ids are already lowercase")
        
        # ==================== Step 2: Create/Normalize character nodes ====================
        print("\n[Step 2] Creating/Normalizing character nodes...")
        
        # Get all unique agent_ids after normalization (SurrealDB uses GROUP BY instead of DISTINCT)
        r2 = await db.query("SELECT agent_id FROM conversation GROUP BY agent_id")
        unique_agents = set()
        if isinstance(r2, list):
            for item in r2:
                if item.get('agent_id'):
                    unique_agents.add(item['agent_id'].lower())
        
        print(f"  Found {len(unique_agents)} unique agents: {unique_agents}")
        
        for agent in unique_agents:
            # Check if character node exists
            check_query = f"SELECT * FROM character:{agent}"
            existing = await db.query(check_query)
            
            if not existing or (isinstance(existing, list) and len(existing) == 0):
                # Create character node
                create_query = f"""
                CREATE character:{agent} SET 
                    name = '{agent}',
                    created_at = time::now()
                """
                await db.query(create_query)
                print(f"  ✅ Created character node: character:{agent}")
            else:
                print(f"  ✓ character:{agent} already exists")
        
        # ==================== Step 3: Backfill observes relations ====================
        print("\n[Step 3] Backfilling observes relations...")
        
        # Get all edge tables
        info = await db.query("INFO FOR DB;")
        tables_map = {}
        if isinstance(info, dict):
            tables_map = info.get('tables', {})
        
        known_non_edge = ["conversation", "entity", "character", "user", "user_entity", 
                         "memory_embeddings", "migrations", "fact", "insight", "observes"]
        edge_tables = [t for t in tables_map.keys() if t not in known_non_edge]
        
        print(f"  Found {len(edge_tables)} edge tables: {edge_tables[:10]}...")
        
        observes_created = 0
        
        # For each character, link them to edges that mention related entities
        for agent in unique_agents:
            char_id = f"character:{agent}"
            
            for tbl in edge_tables[:20]:  # Limit to first 20 edge tables
                try:
                    # Get edges from this table
                    edges_query = f"SELECT id FROM {tbl} LIMIT 50"
                    edges = await db.query(edges_query)
                    
                    if isinstance(edges, list):
                        for edge in edges:
                            edge_id = edge.get('id')
                            if edge_id:
                                # Check if observes relation already exists
                                check_obs = f"""
                                SELECT * FROM observes 
                                WHERE in = {char_id} AND out = {edge_id}
                                """
                                existing_obs = await db.query(check_obs)
                                
                                if not existing_obs or (isinstance(existing_obs, list) and len(existing_obs) == 0):
                                    # Create observes relation
                                    relate_query = f"""
                                    RELATE {char_id}->observes->{edge_id} SET 
                                        last_observed = time::now()
                                    """
                                    await db.query(relate_query)
                                    observes_created += 1
                                    
                except Exception as e:
                    print(f"  ⚠️ Error processing {tbl}: {e}")
                    continue
        
        print(f"  ✅ Created {observes_created} new observes relations")
        
        # ==================== Summary ====================
        print("\n" + "=" * 60)
        print("[Summary]")
        print("=" * 60)
        print(f"  ✅ Normalized {len(agent_ids_to_fix)} agent_ids to lowercase")
        print(f"  ✅ Ensured {len(unique_agents)} character nodes exist")
        print(f"  ✅ Created {observes_created} observes relations")
        print("\n🎉 Migration complete! Please restart the backend.")
        
    except Exception as e:
        print(f"❌ Migration Error: {e}")
        import traceback
        traceback.print_exc()
    finally:
        await db.close()
        print("\n✅ Connection closed")

if __name__ == "__main__":
    asyncio.run(main())
