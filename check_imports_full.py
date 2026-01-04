
try:
    from mem0.llms.openai import OpenAILLM
    print("✅ LLM Import successful")
except ImportError as e:
    print(f"❌ LLM Import failed: {e}")

try:
    from mem0.embeddings.huggingface import HuggingFaceEmbedding
    print("✅ Embedder Import successful")
except ImportError as e:
    print(f"❌ Embedder Import failed: {e}")
