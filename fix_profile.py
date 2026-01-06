import json

# 手动删除 current_obsession
with open('python_backend/core_profile.json', 'r', encoding='utf-8-sig') as f:
    profile = json.load(f)

if 'relationship' in profile and 'current_obsession' in profile['relationship']:
    del profile['relationship']['current_obsession']
    print("Removed 'current_obsession' from relationship")

# 手动设置正确的 description（如果需要测试）
# profile['identity']['description'] = "你是一个18岁的活泼可爱的女孩子，你正在你的恋人聊天。\n对话一定要使用英语，除非对方问某个东西是什么或者某个单词什么意思。"

with open('python_backend/core_profile.json', 'w', encoding='utf-8') as f:
    json.dump(profile, f, indent=2, ensure_ascii=False)

print("✅ Cleaned core_profile.json")
print("\n当前 identity:")
print(f"  name: {profile['identity']['name']}")
print(f"  description: {profile['identity']['description']}")
