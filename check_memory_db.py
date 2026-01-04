import sqlite3

db_path = r"e:\Work\Code\Lumina\memory_db\collection\lumina_hf_1536d_local\storage.sqlite"
try:
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    # Count points
    cursor.execute("SELECT COUNT(*) FROM points")
    count = cursor.fetchone()[0]
    print(f"Total memories in database: {count}")
    
    if count > 0:
        cursor.execute("SELECT * FROM points LIMIT 10")
        rows = cursor.fetchall()
        print(f"\nFirst {min(count, 10)} memories:")
        for i, row in enumerate(rows, 1):
            print(f"{i}. {row}")
    
    conn.close()
except Exception as e:
    print(f"Error: {e}")
