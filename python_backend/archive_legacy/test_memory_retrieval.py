"""
SurrealDB Memory Retrieval Diagnostic Script
诊断记忆检索问题：
1. 测试 conversation 表原始数据
2. 测试 text 别名计算
3. 测试 hybrid search
4. 测试 inspiration 获取
"""

import asyncio
from surrealdb import AsyncSurreal

# Config
SURREAL_URL = "ws://localhost:8000/rpc"
NAMESPACE = "lumina"
DATABASE = "memory"
CHARACTER_ID = "lillian"

async def main():
    print("=" * 60)
    print("SurrealDB Memory Retrieval Diagnostic")
    print("=" * 60)
    
    db = AsyncSurreal(SURREAL_URL)
    
    try:
        await db.connect()
        await db.signin({"username": "root", "password": "root"})
        await db.use(NAMESPACE, DATABASE)
        print("✅ Connected to SurrealDB\n")
        
        # ==================== Test 1: Raw Conversation Data ====================
        print("=" * 60)
        print("[Test 1] Raw Conversation Records")
        print("=" * 60)
        
        raw_query = f"""
        SELECT id, user_input, ai_response, narrative, agent_id, created_at
        FROM conversation
        WHERE agent_id = '{CHARACTER_ID}'
        ORDER BY created_at DESC
        LIMIT 3;
        """
        
        result = await db.query(raw_query)
        print(f"Raw Result Type: {type(result)}")
        print(f"Raw Result: {result}\n")
        
        # Parse result
        records = []
        if isinstance(result, list):
            if len(result) > 0 and isinstance(result[0], dict) and 'result' in result[0]:
                records = result[0]['result']
            else:
                records = result
        
        if records:
            print(f"Found {len(records)} records:")
            for i, rec in enumerate(records):
                print(f"\n  [{i+1}] ID: {rec.get('id')}")
                print(f"      agent_id: {rec.get('agent_id')}")
                print(f"      user_input: {str(rec.get('user_input'))[:50]}...")
                print(f"      ai_response: {str(rec.get('ai_response'))[:50]}...")
                print(f"      narrative: {rec.get('narrative')}")
        else:
            print("❌ No conversation records found!")
        
        # ==================== Test 2: Text Alias Calculation ====================
        print("\n" + "=" * 60)
        print("[Test 2] Text Alias Calculation (narrative OR concat)")
        print("=" * 60)
        
        alias_query = f"""
        SELECT 
            id,
            narrative,
            user_input,
            ai_response,
            (narrative OR (user_input + ' ' + ai_response)) as text
        FROM conversation
        WHERE agent_id = '{CHARACTER_ID}'
        LIMIT 3;
        """
        
        try:
            result2 = await db.query(alias_query)
            print(f"Result Type: {type(result2)}")
            
            records2 = []
            if isinstance(result2, list):
                if len(result2) > 0 and isinstance(result2[0], dict) and 'result' in result2[0]:
                    records2 = result2[0]['result']
                else:
                    records2 = result2
            
            if records2:
                print(f"Found {len(records2)} records with alias:")
                for i, rec in enumerate(records2):
                    text_value = rec.get('text')
                    print(f"\n  [{i+1}] text alias value: {str(text_value)[:100] if text_value else 'NULL/None'}...")
                    print(f"      narrative: {rec.get('narrative')}")
            else:
                print("❌ Query returned empty!")
        except Exception as e:
            print(f"❌ Alias query failed: {e}")
        
        # ==================== Test 3: Alternative Concat Syntax ====================
        print("\n" + "=" * 60)
        print("[Test 3] Alternative Concat Syntax (string::concat)")
        print("=" * 60)
        
        concat_query = f"""
        SELECT 
            id,
            string::concat(user_input, ' ', ai_response) as text_concat,
            narrative
        FROM conversation
        WHERE agent_id = '{CHARACTER_ID}'
        LIMIT 3;
        """
        
        try:
            result3 = await db.query(concat_query)
            
            records3 = []
            if isinstance(result3, list):
                if len(result3) > 0 and isinstance(result3[0], dict) and 'result' in result3[0]:
                    records3 = result3[0]['result']
                else:
                    records3 = result3
            
            if records3:
                print(f"Found {len(records3)} records:")
                for i, rec in enumerate(records3):
                    text_value = rec.get('text_concat')
                    print(f"\n  [{i+1}] text_concat: {str(text_value)[:100] if text_value else 'NULL/None'}...")
            else:
                print("❌ Query returned empty!")
        except Exception as e:
            print(f"❌ Concat query failed: {e}")
        
        # ==================== Test 4: COALESCE/IF-ELSE Logic ====================
        print("\n" + "=" * 60)
        print("[Test 4] COALESCE-like Logic (IF narrative ELSE concat)")
        print("=" * 60)
        
        coalesce_query = f"""
        SELECT 
            id,
            IF narrative != NONE AND narrative != '' THEN narrative 
            ELSE string::concat(COALESCE(user_input, ''), ' ', COALESCE(ai_response, ''))
            END as text_safe
        FROM conversation
        WHERE agent_id = '{CHARACTER_ID}'
        LIMIT 3;
        """
        
        try:
            result4 = await db.query(coalesce_query)
            
            records4 = []
            if isinstance(result4, list):
                if len(result4) > 0 and isinstance(result4[0], dict) and 'result' in result4[0]:
                    records4 = result4[0]['result']
                else:
                    records4 = result4
            
            if records4:
                print(f"Found {len(records4)} records:")
                for i, rec in enumerate(records4):
                    text_value = rec.get('text_safe')
                    print(f"\n  [{i+1}] text_safe: {str(text_value)[:100] if text_value else 'NULL/None'}...")
            else:
                print("❌ Query returned empty!")
        except Exception as e:
            print(f"❌ COALESCE query failed: {e}")
        
        # ==================== Test 5: Edge Tables for Inspiration ====================
        print("\n" + "=" * 60)
        print("[Test 5] Edge Tables (for Inspiration)")
        print("=" * 60)
        
        info_query = "INFO FOR DB;"
        try:
            info_result = await db.query(info_query)
            print(f"INFO result type: {type(info_result)}")
            
            # Parse to get tables
            if isinstance(info_result, list):
                if len(info_result) > 0:
                    info_data = info_result[0]
                    if isinstance(info_data, dict) and 'result' in info_data:
                        info_data = info_data['result']
                    
                    tables = info_data.get('tables', {}) if isinstance(info_data, dict) else {}
                    
                    edge_tables = [t for t in tables.keys() if t.islower() and not t.startswith('_')]
                    print(f"All tables: {list(tables.keys())}")
                    print(f"Potential edge tables: {edge_tables}")
                    
                    # Try to query a few edge tables
                    for edge in ['likes', 'knows', 'observes'][:3]:
                        if edge in tables:
                            edge_query = f"SELECT * FROM {edge} LIMIT 2;"
                            edge_result = await db.query(edge_query)
                            
                            edge_records = []
                            if isinstance(edge_result, list):
                                if len(edge_result) > 0 and isinstance(edge_result[0], dict) and 'result' in edge_result[0]:
                                    edge_records = edge_result[0]['result']
                                else:
                                    edge_records = edge_result
                            
                            print(f"\n  Edge '{edge}': {len(edge_records)} sample records")
                            if edge_records:
                                print(f"    Sample: {edge_records[0]}")
        except Exception as e:
            print(f"❌ Edge query failed: {e}")
        
        # ==================== Summary ====================
        print("\n" + "=" * 60)
        print("[Summary] Recommended Fix")
        print("=" * 60)
        print("""
Based on these tests, the issue is likely:
1. 'narrative' field is NULL on old records
2. SurrealDB 'OR' operator doesn't work as expected for null coalescing
3. String concat with NULL returns NULL

SOLUTION: Use IF/ELSE or string::concat with COALESCE
        """)
        
    except Exception as e:
        print(f"❌ Connection/Query Error: {e}")
        import traceback
        traceback.print_exc()
    finally:
        await db.close()
        print("\n✅ Connection closed")

if __name__ == "__main__":
    asyncio.run(main())
