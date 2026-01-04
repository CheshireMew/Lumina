
import os
import logging
from mem0 import Memory

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("DebugMem0")

def test_mem0():
    print("Testing Mem0 Configuration and Search...")
    
    # Mock Config (Same as server)
    m_config = {
        "vector_store": {
            "provider": "qdrant",
            "config": {
                "path": "./memory_db",
            }
        },
        "llm": {
            "provider": "openai",
            "config": {
                "model": "deepseek-chat",
                "api_key": "sk-dummy", # Won't be used for search if only embedding is needed? Or maybe it is.
                "openai_base_url": "https://api.deepseek.com/v1",
                "max_tokens": 1500
            }
        },
        "embedder": {
            "provider": "huggingface",
            "config": {
                "model": "all-MiniLM-L6-v2"
            }
        }
    }
    
    try:
        print("Initializing Memory...")
        m = Memory.from_config(m_config)
        print("Memory Initialized.")
        
        print("Attempting Search...")
        # Note: Search typically requires embedding. LLM might be used for reranking or answer generation depending on mem0 version?
        # mem0 search usually just semantic search.
        results = m.search("test query", user_id="default_user")
        print(f"Search Results: {results}")
        
    except Exception as e:
        print(f"❌ Error occurred: {type(e).__name__}: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    test_mem0()
