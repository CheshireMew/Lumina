
import os
import sys
# Add current directory to path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from lite_memory import LiteMemory
from dotenv import load_dotenv

# Load env to get API keys
load_dotenv()

def debug_search():
    config = {
        "qdrant_path": os.getenv("QDRANT_PATH", "e:\\Work\\Code\\Lumina\\brain\\mnemosyne"),
        "openai_base_url": os.getenv("OPENAI_BASE_URL"),
        "api_key": os.getenv("OPENAI_API_KEY"),
        "embedder_model": "sangmini/msmarco-cotmae-MiniLM-L12_en-ko-ja" 
    }
    
    print("Initializing LiteMemory...")
    try:
        memory = LiteMemory(config)
    except Exception as e:
        print(f"Failed to init LiteMemory: {e}")
        return

    query = "我的名字是什么?"
    print(f"\n--- Debugging Search for: '{query}' ---")
    
    try:
        # 1. Search User Memory
        print("\n[User Memory Raw Search Results]")
        user_vector = memory.encoder.encode(query).tolist()
        user_results = memory.client.query_points(
            collection_name="memory_user",
            query=user_vector,
            limit=10,
            with_payload=True
        ).points
        
        if not user_results:
            print("No results in user_memory.")
        
        for hit in user_results:
            print(f"Score: {hit.score:.4f} | Text: {hit.payload.get('text', 'N/A')} | Time: {hit.payload.get('timestamp')}")

        # 2. Search Character Memory (Hiyori)
        print("\n[Character Memory Raw Search Results]")
        char_results = memory.client.query_points(
            collection_name="memory_hiyori",
            query=user_vector,
            limit=10,
            with_payload=True
        ).points
        
        if not char_results:
            print("No results in character_memory.")

        for hit in char_results:
            print(f"Score: {hit.score:.4f} | Text: {hit.payload.get('text', 'N/A')} | Time: {hit.payload.get('timestamp')}")

        # 3. Test LiteMemory.search() logic (with decay)
        print("\n[LiteMemory.search() Final Output]")
        final_results = memory.search(query,limit=5)
        for res in final_results:
            print(f"Text: {res}")
            
    except Exception as e:
        print(f"Error during search: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    debug_search()
