"""
Clean up old test_collection
"""
from qdrant_client import QdrantClient

client = QdrantClient(path="./lite_memory_db")

try:
    # Delete old collection
    client.delete_collection("test_collection")
    print("✓ Deleted old 'test_collection'")
except Exception as e:
    print(f"Collection already gone or error: {e}")

# Verify
collections = client.get_collections()
print("\nRemaining collections:")
for col in collections.collections:
    info = client.get_collection(col.name)
    print(f"  ✓ {col.name} ({info.points_count} memories)")

print("\n✅ Cleanup complete! Only character-specific collections remain.")
