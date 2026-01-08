
import os
import json
import uuid
from typing import List, Dict
from qdrant_client import QdrantClient
from qdrant_client.http import models
from sentence_transformers import SentenceTransformer
import logging

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s [%(levelname)s] %(message)s')
logger = logging.getLogger("RebuildDB")

# Configuration
DB_PATH = "./lite_memory_db"
BACKUP_DIR = "./memory_backups"
EMBEDDER_MODEL = "paraphrase-multilingual-MiniLM-L12-v2"
COLLECTIONS = ["memory_user", "memory_hiyori"] # Add other character IDs if needed

def load_backup(filepath: str) -> List[Dict]:
    """Load memories from a JSONL backup file."""
    memories = []
    if not os.path.exists(filepath):
        logger.warning(f"Backup file not found: {filepath}")
        return memories
    
    with open(filepath, 'r', encoding='utf-8') as f:
        for line in f:
            line = line.strip()
            if line:
                try:
                    data = json.loads(line)
                    memories.append(data)
                except json.JSONDecodeError:
                    logger.error(f"Invalid JSON in {filepath}: {line}")
    return memories

def rebuild_database():
    logger.info(f"--- Starting Database Rebuild ---")
    logger.info(f"Target Embedder: {EMBEDDER_MODEL} (Expect 384 dim)")
    
    # 1. Initialize Embedder
    logger.info("Loading embedding model...")
    encoder = SentenceTransformer(EMBEDDER_MODEL)
    embedding_size = encoder.get_sentence_embedding_dimension()
    logger.info(f"Model loaded. Dimension: {embedding_size}")
    
    if embedding_size != 384:
        logger.warning(f"Expected 384 dimensions, got {embedding_size}. Proceeding anyway.")

    # 1.5 FORCE CLEANUP: Remove the entire DB folder to ensure no residual 1536-dim schema remains
    if os.path.exists(DB_PATH):
        logger.warning(f"Removing existing DB at {DB_PATH} for fresh rebuild...")
        import shutil
        try:
            shutil.rmtree(DB_PATH)
            logger.info("Existing DB folder removed.")
        except Exception as e:
            logger.error(f"Failed to remove DB folder: {e}. Please manually delete {DB_PATH}.")
            return

    # 2. Initialize Qdrant
    logger.info(f"Connecting to Qdrant at {DB_PATH}...")
    client = QdrantClient(path=DB_PATH)
    
    for collection_name in COLLECTIONS:
        logger.info(f"\nProcessing Collection: {collection_name}")
        
        # Determine backup file from collection name
        if collection_name == "memory_user":
            backup_file = "user_memory.jsonl"
        else:
            # Assumes format memory_{char_id}
            char_id = collection_name.replace("memory_", "")
            backup_file = f"{char_id}_memory.jsonl"
            
        backup_path = os.path.join(BACKUP_DIR, backup_file)
        
        # 3. Load Data
        memories = load_backup(backup_path)
        logger.info(f"Loaded {len(memories)} items from {backup_file}")
        
        if not memories:
            logger.info("No data to migrate for this collection.")
            # Still recreate collection to fix dimensions if it exists and is wrong
        
        # 4. Re-create Collection
        if client.collection_exists(collection_name):
            logger.info(f"Deleting existing collection '{collection_name}'...")
            client.delete_collection(collection_name)
            
        logger.info(f"Creating collection '{collection_name}' with size {embedding_size}...")
        client.create_collection(
            collection_name=collection_name,
            vectors_config=models.VectorParams(
                size=embedding_size,
                distance=models.Distance.COSINE
            )
        )
        
        if not memories:
            continue

        # 5. Re-embed and Upsert
        logger.info("Re-embedding and upserting data...")
        points = []
        texts = [m["text"] for m in memories]
        
        # Batch embed
        vectors = encoder.encode(texts, show_progress_bar=True)
        
        for i, memory in enumerate(memories):
            # Ensure ID is valid UUID or generate one
            try:
                point_id = memory.get("id") or str(uuid.uuid4())
                # Validate UUID format loosely? Qdrant accepts strings.
            except:
                point_id = str(uuid.uuid4())
            
            # Construct Payload
            # We use the data from backup as payload, cleaning up 'vector' field if present
            payload = memory.copy()
            if "vector" in payload:
                del payload["vector"]
            if "score" in payload: 
                del payload["score"]
                
            points.append(models.PointStruct(
                id=point_id,
                vector=vectors[i].tolist(),
                payload=payload
            ))
            
        # Batch Upsert
        # Qdrant local might prefer smaller batches, but for <1000 items, one go is fine.
        client.upsert(
            collection_name=collection_name,
            points=points
        )
        logger.info(f"Successfully migrated {len(points)} items to {collection_name}")

    logger.info("\n--- Rebuild Complete! ---")
    logger.info("You can now restart the memory server.")

if __name__ == "__main__":
    rebuild_database()
