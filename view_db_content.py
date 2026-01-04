import sqlite3
import pickle

db_path = r"e:\Work\Code\Lumina\memory_db\collection\lumina_hf_1536d_local\storage.sqlite"

try:
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    # Get all records
    cursor.execute("SELECT * FROM points LIMIT 10")
    rows = cursor.fetchall()
    
    print(f"数据库中共有 {len(rows)} 条记录：\n")
    
    for i, row in enumerate(rows, 1):
        print(f"记录 {i}:")
        print(f"  ID: {row[0] if len(row) > 0 else 'N/A'}")
        
        # Try to get payload which contains the actual memory text
        if len(row) > 1:
            try:
                # Payload is usually in BLOB format
                payload_blob = row[1]
                if payload_blob:
                    # Try to decode as JSON first
                    import json
                    try:
                        payload = json.loads(payload_blob)
                        print(f"  内容: {payload}")
                    except:
                        print(f"  Raw payload (前100字符): {str(payload_blob)[:100]}")
            except Exception as e:
                print(f"  解析错误: {e}")
        print()
    
    # Also check schema
    cursor.execute("PRAGMA table_info(points)")
    schema = cursor.fetchall()
    print("\n数据库结构:")
    for col in schema:
        print(f"  {col[1]}: {col[2]}")
    
    conn.close()
    
except Exception as e:
    print(f"错误: {e}")
    import traceback
    traceback.print_exc()
