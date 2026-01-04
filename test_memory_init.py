from mem0 import Memory
from mem0.embeddings.huggingface import HuggingFaceEmbedding
from mem0.llms.openai import OpenAILLM

print("测试 1: HuggingFaceEmbedding 默认初始化")
try:
    embedder = HuggingFaceEmbedding()
    print(f"✅ 成功! 类型: {type(embedder)}")
    print(f"   模型: {getattr(embedder, 'model_name', 'N/A')}")
except Exception as e:
    print(f"❌ 失败: {e}")

print("\n测试 2: 使用 Memory.from_config 完整配置")
try:
    config = {
        "vector_store": {
            "provider": "qdrant",
            "config": {
                "collection_name": "test_collection",
                "path": "./test_memory_db",
            }
        },
        "llm": {
            "provider": "openai",
            "config": {
                "model": "gpt-4",
                "api_key": "sk-test",
                "base_url": "https://api.deepseek.com/v1"
            }
        },
        "embedder": {
            "provider": "huggingface",
            "config": {
                "model": "all-MiniLM-L6-v2"
            }
        }
    }
    memory = Memory.from_config(config)
    print(f"✅ 成功! 类型: {type(memory)}")
except Exception as e:
    print(f"❌ 失败: {e}")

print("\n测试 3: Memory() 直接传递对象（无 config 参数给 HF）")
try:
    embedder = HuggingFaceEmbedding()  # 默认
    llm = OpenAILLM(config={
        "model": "gpt-4",
        "api_key": "sk-test",
        "base_url": "https://api.deepseek.com/v1"
    })
    
    memory = Memory(
        embedding_model=embedder,
        llm=llm,
        vector_store_config={
            "provider": "qdrant",
            "config": {
                "collection_name": "test",
                "path": "./test_db"
            }
        }
    )
    print(f"✅ 成功! 类型: {type(memory)}")
except Exception as e:
    print(f"❌ 失败: {e}")
