
try:
    from mem0.embeddings.huggingface import HuggingFaceEmbedding
    print("✅ Import successful")
except ImportError as e:
    print(f"❌ Import failed: {e}")
    # Try alternative
    try:
        from mem0.embeddings.huggingface import HuggingFaceEmbeddings
        print("✅ Import successful (Alternative)")
    except ImportError as e2:
        print(f"❌ Import failed (Alternative): {e2}")
