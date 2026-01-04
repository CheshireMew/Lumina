
import os
import sys
from qdrant_client import QdrantClient
from sentence_transformers import SentenceTransformer

# 1. Inspect DB Content
db_path = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "lite_memory_db"))
print(f"Connecting to DB at: {db_path}")

client = QdrantClient(path=db_path)

def list_collection(name):
    print(f"\n--- Collection: {name} ---")
    try:
        # Check if collection exists
        client.get_collection(name)
        
        # Scroll all points
        points, _ = client.scroll(
            collection_name=name,
            limit=100,
            with_payload=True,
            with_vectors=False
        )
        
        print(f"Found {len(points)} points:")
        for p in points:
            text = p.payload.get("text", "N/A")
            print(f"ID: {p.id} | Text: {text}")
            
    except Exception as e:
        print(f"Error accessing collection {name}: {e}")

list_collection("memory_user")
list_collection("memory_hiyori")

# 2. Check Similarity
print(f"\n--- Similarity Check ---")
model_path = "sangmini/msmarco-cotmae-MiniLM-L12_en-ko-ja" 
# Use the same model as in lite_memory.py (default) or check config
# Assuming default based on lite_memory.py reading

try:
    print(f"Loading model: {model_path}")
    encoder = SentenceTransformer(model_path)
    
    s1 = "用户最喜欢的季节是秋天"
    s2 = "用户只喜欢夏天"
    
    emb1 = encoder.encode(s1)
    emb2 = encoder.encode(s2)
    
    # Calculate Cosine Similarity
    import numpy as np
    from numpy.linalg import norm
    
    cosine = np.dot(emb1, emb2) / (norm(emb1) * norm(emb2))
    print(f"\nSentence 1: {s1}")
    print(f"Sentence 2: {s2}")
    print(f"Similarity Score: {cosine:.4f}")
    
    if cosine < 0.6:
        print("!! Similarity is below threshold (0.6). Conflict check would be SKIPPED. !!")
    else:
        print("Similarity is above threshold. Conflict check should have triggered.")

except Exception as e:
    print(f"Error loading model or calculating similarity: {e}")
