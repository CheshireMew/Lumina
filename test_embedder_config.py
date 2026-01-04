from mem0.embeddings.huggingface import HuggingFaceEmbedding
from mem0.configs.embeddings.base import EmbedderConfig
import inspect

# 查看 HuggingFaceEmbedding 需要什么类型的 config
print("=" * 50)
print("HuggingFaceEmbedding.__init__ 签名:")
print(inspect.signature(HuggingFaceEmbedding.__init__))
print("=" * 50)

# 尝试不同的实例化方法
print("\n尝试 1: 直接使用 dict")
try:
    embedder = HuggingFaceEmbedding(config={"model": "all-MiniLM-L6-v2"})
    print("✅ 成功")
except Exception as e:
    print(f"❌ 失败: {type(e).__name__}: {e}")

print("\n尝试 2: 使用 EmbedderConfig (如果存在)")
try:
    from mem0.configs.embeddings.huggingface import HuggingFaceEmbedderConfig
    config = HuggingFaceEmbedderConfig(model="all-MiniLM-L6-v2")
    embedder = HuggingFaceEmbedding(config=config)
    print("✅ 成功")
    print(f"Config 类型: {type(config)}")
    print(f"Config 内容: {config}")
except ImportError as ie:
    print(f"❌ 导入失败: {ie}")
except Exception as e:
    print(f"❌ 实例化失败: {type(e).__name__}: {e}")

print("\n尝试 3: 不传参数（使用默认值）")
try:
    embedder = HuggingFaceEmbedding()
    print("✅ 成功")
except Exception as e:
    print(f"❌ 失败: {type(e).__name__}: {e}")
