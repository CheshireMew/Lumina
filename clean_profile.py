import json

# Load core_profile.json (handle BOM)
with open('python_backend/core_profile.json', 'r', encoding='utf-8-sig') as f:
    profile = json.load(f)

# Remove dynamic fields
if 'system_prompt' in profile:
    del profile['system_prompt']
    print("Removed 'system_prompt'")

if 'system_prompt_template' in profile:
    del profile['system_prompt_template']
    print("Removed 'system_prompt_template'")

# Save back
with open('python_backend/core_profile.json', 'w', encoding='utf-8') as f:
    json.dump(profile, f, indent=2, ensure_ascii=False)

print("✅ Cleaned core_profile.json")
