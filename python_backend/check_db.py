import sqlite3

# Check memory_db database (the real one)
db_path = "E:/Work/Code/Lumina/memory_db/lumina_memory.db"
conn = sqlite3.connect(db_path)

# Check all tables with 'fact' in name
cursor = conn.execute("SELECT name FROM sqlite_master WHERE type='table' AND name LIKE '%fact%'")
tables = cursor.fetchall()
print("Tables with 'fact' in name:")
for row in tables:
    print(f"  - {row[0]}")
    # Show schema
    cursor2 = conn.execute(f"PRAGMA table_info({row[0]})")
    print("    Columns:", ", ".join([c[1] for c in cursor2.fetchall()]))
    # Show count
    cursor3 = conn.execute(f"SELECT COUNT(*) FROM {row[0]}")
    count = cursor3.fetchone()[0]
    print(f"    Row count: {count}")
    
    # If has consolidated column, show consolidated count  
    try:
        cursor4 = conn.execute(f"SELECT COUNT(*) FROM {row[0]} WHERE consolidated=1")
        consolidated = cursor4.fetchone()[0]
        print(f"    Consolidated: {consolidated}")
        
        # Show samples
        if consolidated > 0:
            cursor5 = conn.execute(f"SELECT * FROM {row[0]} WHERE consolidated=1 ORDER BY RANDOM() LIMIT 2")
            samples = cursor5.fetchall()
            print(f"    Sample data:")
            for s in samples:
                print(f"      {s[:3]}...")
    except:
        pass
    print()

conn.close()
