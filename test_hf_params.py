from mem0.embeddings.huggingface import HuggingFaceEmbedding
import inspect

# 查看构造函数签名
sig = inspect.signature(HuggingFaceEmbedding.__init__)
print("HuggingFaceEmbedding 构造函数参数:")
print(sig)

# 尝试不同的参数名
try:
    # 尝试 1: model_name
    embedder = HuggingFaceEmbedding(model_name="all-MiniLM-L6-v2")
    print("✅ model_name 成功")
except TypeError as e:
    print(f"❌ model_name 失败: {e}")
    
try:
    # 尝试 2: model
    embedder = HuggingFaceEmbedding(model="all-MiniLM-L6-v2")
    print("✅ model 成功")
except TypeError as e:
    print(f"❌ model 失败: {e}")

try:
    # 尝试 3: config dict
    embedder = HuggingFaceEmbedding(config={"model": "all-MiniLM-L6-v2"})
    print("✅ config dict 成功")
except TypeError as e:
    print(f"❌ config dict 失败: {e}")
