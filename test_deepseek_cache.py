import os
import time
from openai import OpenAI
import dotenv

# Load environment variables
dotenv.load_dotenv()

# Configuration
API_KEY = os.getenv("DEEPSEEK_API_KEY") or "sk-8bd1a0937c8e4347a502206718536098" # Fallback if env not set
BASE_URL = "https://api.deepseek.com"

client = OpenAI(api_key=API_KEY, base_url=BASE_URL)

def run_test():
    print("🧪 Testing DeepSeek Context Caching...")
    
    # 1. Define a long System Prompt (Prefix)
    # The prefix must be identical to trigger cache.
    system_prompt = "You are a helpful assistant. " * 100 # Repeat to make it long enough to be noticeable
    
    messages = [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": "Hello! My name is Dylan."}
    ]
    
    print("\n[Request 1] Sending initial request (should be Cache MISS)...")
    start_time = time.time()
    response1 = client.chat.completions.create(
        model="deepseek-chat",
        messages=messages,
        stream=False
    )
    duration1 = time.time() - start_time
    
    usage1 = response1.usage
    print(f"⏱️ Duration: {duration1:.2f}s")
    print(f"📊 Usage: {usage1}")
    if hasattr(usage1, 'prompt_cache_hit_tokens'):
        print(f"🎯 Cache Hit Tokens: {usage1.prompt_cache_hit_tokens}")
    if hasattr(usage1, 'prompt_cache_miss_tokens'):
        print(f"💨 Cache Miss Tokens: {usage1.prompt_cache_miss_tokens}")

    # 2. Send the SAME prefix + New Message
    messages.append(response1.choices[0].message)
    messages.append({"role": "user", "content": "What is my name?"})
    
    print("\n[Request 2] Sending follow-up request with SAME prefix (should be Cache HIT)...")
    start_time = time.time()
    response2 = client.chat.completions.create(
        model="deepseek-chat",
        messages=messages,
        stream=False
    )
    duration2 = time.time() - start_time
    
    usage2 = response2.usage
    print(f"⏱️ Duration: {duration2:.2f}s")
    print(f"📊 Usage: {usage2}")
    if hasattr(usage2, 'prompt_cache_hit_tokens'):
        print(f"🎯 Cache Hit Tokens: {usage2.prompt_cache_hit_tokens}")
        if usage2.prompt_cache_hit_tokens > 0:
            print("\n✅ SUCCESS: Context Caching is WORKING!")
        else:
            print("\n❌ WARNING: Cache Hit is 0. Caching might not be active or prefix mismatch.")
    
if __name__ == "__main__":
    run_test()
