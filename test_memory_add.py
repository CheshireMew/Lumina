import requests
import json

BASE_URL = "http://127.0.0.1:8001"

print("=== 测试记忆功能 ===\n")

# 1. 配置（应该已经被前端配置过了）
print("1. 跳过配置（前端已配置）\n")

# 2. 添加记忆
print("2. 添加测试记忆...")
messages = [
    {"role": "user", "content": "我叫 Dylan，最喜欢 Python 编程"},
    {"role": "assistant", "content": "很高兴认识你 Dylan！Python 是个很棒的语言。"}
]

try:
    response = requests.post(f"{BASE_URL}/add", json={
        "messages": messages,
        "user_id": "default_user"
    })
    print(f"   状态码: {response.status_code}")
    print(f"   响应: {response.text}\n")
except Exception as e:
    print(f"   ❌ 失败: {e}\n")

# 3. 等待处理
import time
print("3. 等待 3 秒让 DeepSeek 处理...")
time.sleep(3)

# 4. 查询所有记忆
print("\n4. 查询所有记忆...")
try:
    response = requests.get(f"{BASE_URL}/all?user_id=default_user")
    print(f"   状态码: {response.status_code}")
    data = response.json()
    print(f"   记忆数量: {len(data.get('results', {}).get('results', []))}")
    print(f"   详细内容:")
    print(json.dumps(data, indent=2, ensure_ascii=False))
except Exception as e:
    print(f"   ❌ 失败: {e}")
