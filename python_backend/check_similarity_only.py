
from sentence_transformers import SentenceTransformer
import numpy as np
from numpy.linalg import norm

print(f"\n--- Similarity Check Only ---")
model_path = "sangmini/msmarco-cotmae-MiniLM-L12_en-ko-ja" 

try:
    print(f"Loading model: {model_path}")
    encoder = SentenceTransformer(model_path)
    
    s1 = "用户最喜欢的季节是秋天"
    s2 = "用户只喜欢夏天"
    
    emb1 = encoder.encode(s1)
    emb2 = encoder.encode(s2)
    
    cosine = np.dot(emb1, emb2) / (norm(emb1) * norm(emb2))
    print(f"\nSentence 1: {s1}")
    print(f"Sentence 2: {s2}")
    print(f"Similarity Score: {cosine:.4f}")
    
    if cosine < 0.6:
        print("!! Similarity is below threshold (0.6). Conflict check would be SKIPPED. !!")
    else:
        print("Similarity is above threshold. Conflict check should have triggered.")

except Exception as e:
    print(f"Error: {e}")
