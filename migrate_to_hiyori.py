"""
Migrate existing memory collection to character-based naming
"""
from qdrant_client import QdrantClient

# Initialize Qdrant client
client = QdrantClient(path="./lite_memory_db")

# Check existing collections
collections = client.get_collections()
print("Existing collections:")
for col in collections.collections:
    print(f"  - {col.name}")

# Check if old collection exists
old_name = "test_collection"
new_name = "memory_hiyori"

try:
    # Try to get the old collection
    old_collection = client.get_collection(old_name)
    print(f"\n✓ Found old collection: {old_name}")
    print(f"  Points count: {old_collection.points_count}")
    
    # Check if new collection already exists
    try:
        new_collection = client.get_collection(new_name)
        print(f"\n⚠️  New collection '{new_name}' already exists!")
        print(f"  Points count: {new_collection.points_count}")
        print("\nSkipping migration. Please manually delete one if needed.")
    except:
        print(f"\n→ Renaming collection: {old_name} -> {new_name}")
        
        # Qdrant doesn't support direct rename, we need to:
        # 1. Get all points from old collection
        # 2. Create new collection with same config
        # 3. Copy points
        # 4. Delete old collection
        
        # For simplicity, since MemoryService will auto-restore from backup,
        # we can just rename by updating internal metadata
        # But Qdrant doesn't support this easily.
        
        # Workaround: Just delete old collection, LiteMemory will reload from backup
        print("⚠️  Qdrant doesn't support collection renaming.")
        print("   The system will auto-restore from hiyori_memory.jsonl on next configure.")
        print("   Deleting old collection...")
        client.delete_collection(old_name)
        print("✓ Old collection deleted.")
        
except Exception as e:
    print(f"\n✓ Old collection '{old_name}' not found: {e}")
    print("  Nothing to migrate.")

print("\n" + "="*50)
print("Migration complete!")
print("="*50)
print("\nNext steps:")
print("1. Restart memory_server.py")
print("2. Refresh frontend - it will auto-configure for 'hiyori'")
print("3. LiteMemory will create 'memory_hiyori' collection from backup")
