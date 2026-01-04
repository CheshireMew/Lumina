import requests
import json

# Test memory server directly
base_url = "http://127.0.0.1:8001"

# 1. Configure memory
print("1. 配置 Memory...")
config_data = {
    "api_key": "sk-test",
    "base_url": "https://api.deepseek.com/v1",
    "model": "deepseek-chat"
}
try:
    response = requests.post(f"{base_url}/configure", json=config_data)
    print(f"   状态: {response.status_code}")
    print(f"   响应: {response.json()}\n")
except Exception as e:
    print(f"   错误: {e}\n")

# 2. Add a memory
print("2. 添加记忆...")
add_data = {
    "messages": [
        {"role": "user", "content": "我喜欢吃苹果"},
        {"role": "assistant", "content": "苹果很好吃呢！"}
    ],
    "user_id": "default_user"
}
try:
    response = requests.post(f"{base_url}/add", json=add_data)
    print(f"   状态: {response.status_code}")
    print(f"   响应: {response.json()}\n")
except Exception as e:
    print(f"   错误: {e}\n")

# 3. Get all memories
print("3. 获取所有记忆...")
try:
    response = requests.get(f"{base_url}/all?user_id=default_user")
    print(f"   状态: {response.status_code}")
    result = response.json()
    print(f"   记忆数量: {len(result.get('results', []))}")
    for i, mem in enumerate(result.get('results', []), 1):
        print(f"   {i}. {mem.get('memory', 'N/A')}")
except Exception as e:
    print(f"   错误: {e}\n")
