"""
Safe UTF-8 replacement script for renaming agent_id to character_id
"""
import os

files_to_update = [
    "python_backend/surreal_memory.py",
    "python_backend/routers/memory.py",
    "python_backend/routers/debug.py"
]

for file_path in files_to_update:
    if os.path.exists(file_path):
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        # Replace agent_id with character_id
        new_content = content.replace('agent_id', 'character_id')
        
        with open(file_path, 'w', encoding='utf-8') as f:
            f.write(new_content)
        
        count = content.count('agent_id')
        print(f"Updated {file_path}: replaced {count} occurrences")
    else:
        print(f"File not found: {file_path}")

print("Done!")
