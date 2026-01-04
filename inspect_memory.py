import os
import sys

# Check if database directory exists and what collections are there
memory_db_path = r"e:\Work\Code\Lumina\memory_db"

if os.path.exists(memory_db_path):
    print(f"✓ memory_db exists at: {memory_db_path}")
    
    collections_path = os.path.join(memory_db_path, "collection")
    if os.path.exists(collections_path):
        collections = os.listdir(collections_path)
        print(f"\n✓ Collections found: {collections}")
        
        for coll in collections:
            coll_path = os.path.join(collections_path, coll)
            if os.path.isdir(coll_path):
                print(f"\n  Collection: {coll}")
                
                # Check for config file
                config_file = os.path.join(coll_path, "collection_config.json")
                if os.path.exists(config_file):
                    print(f"    ✓ Has config file")
                    with open(config_file, 'r') as f:
                        import json
                        config = json.load(f)
                        print(f"    Vector size: {config.get('params', {}).get('vectors', {}).get('size', 'unknown')}")
                        
                # Check storage.sqlite size
                sqlite_file = os.path.join(coll_path, "storage.sqlite")
                if os.path.exists(sqlite_file):
                    size = os.path.getsize(sqlite_file)
                    print(f"    ✓ storage.sqlite: {size} bytes")
                    
                    # Try to count records
                    try:
                        import sqlite3
                        conn = sqlite3.connect(sqlite_file)
                        cursor = conn.cursor()
                        cursor.execute("SELECT COUNT(*) FROM points")
                        count = cursor.fetchone()[0]
                        print(f"    Records in database: {count}")
                        conn.close()
                    except Exception as e:
                        print(f"    Error reading database: {e}")
else:
    print(f"✗ memory_db does NOT exist at: {memory_db_path}")
