
import sys
import os
from datetime import datetime

# Add . to sys.path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

try:
    from soul_manager import SoulManager
except ImportError:
    sys.path.append(os.path.join(os.getcwd(), 'python_backend'))
    from soul_manager import SoulManager

def print_separator(title):
    print(f"\n{'='*20} {title} {'='*20}\n")

def test_scenarios():
    # 1. Setup Mock SoulManager
    print(">>> Initializing SoulManager (Mock)...")
    mgr = SoulManager.__new__(SoulManager)
    mgr.character_id = "test_char"
    mgr.profile = {
        "identity": {"name": "Lumina", "description": "AI Assistant"},
        "personality": {
            "traits": ["Curious", "Helpful"],
            "big_five": {"openness": 0.9},
            "pad_model": {"pleasure": 0.8}
        },
        "state": {
            "energy_level": 90, 
            "current_mood": "Excited",
            "last_interaction": datetime.now().isoformat()
        },
        "relationship": {
            "user_name": "Master", 
            "level": 3, 
            "current_stage_label": "Trusted Partner",
            "shared_memories_summary": "We coded together."
        }
    }
    
    # Mock Methods
    mgr.get_pad_mood_description = lambda: "Excited (High Pleasure)"
    mgr.get_energy_instruction = lambda: "Speak with high energy."
    mgr.get_relationship_stage = lambda: {"label": "Trusted Partner", "desc": "Deep trust established."}

    # 2. Get Backend Components
    static_prompt = mgr.render_static_prompt()
    dynamic_instruction = mgr.render_dynamic_instruction()

    # ==========================================
    # SCENARIO 1: Active User Dialogue (RAG)
    # ==========================================
    print_separator("SCENARIO 1: Active User Dialogue (Mixed with RAG)")
    
    # Mock RAG Result from Memory Service
    relevant_memories = """
    [Memory 1]: User likes Python. (Relevance: 0.9)
    [Memory 2]: User is working on Refactoring. (Relevance: 0.8)
    """
    
    # Frontend Assembly Logic (Simulated from App.tsx handleSend)
    # finalContext = (relevantMemories + "\n\n" + dynamicState)
    mixed_context = f"{relevant_memories.strip()}\n\n{dynamic_instruction}"
    
    print(f"🔹 [Static System Prefix] (Cached):\n{static_prompt.splitlines()[0]} ... (length: {len(static_prompt)})")
    print(f"\n🔹 [User Message]: 'Hello, what was I doing?'")
    print(f"\n🔹 [Mixed Context] (Appended context):\n{mixed_context}")
    
    # Verification
    if "User is working on Refactoring" in mixed_context and "Excited (High Pleasure)" in mixed_context:
        print("\n✅ PASSED: Mixed Context contains both RAG Memory and Dynamic Mood.")
    else:
        print("\n❌ FAILED: Missing content in mixed context.")


    # ==========================================
    # SCENARIO 2: AI Proactive Dialogue (Inspiration)
    # ==========================================
    print_separator("SCENARIO 2: AI Proactive Dialogue (Mixed with Inspiration)")
    
    # Mock Random Inspiration from Memory Service
    inspiration_text = "- The time we discussed AGI ethics.\n- That sunset photo you showed me."
    
    # Frontend Assembly Logic (Simulated from App.tsx Proactive Loop)
    # Instruction construction
    now_str = datetime.now().strftime('%Y-%m-%d %H:%M')
    
    # Note: App.tsx logic puts dynamicInstruction INSIDE the instruction block
    instruction = f"""(Private System Instruction - DO NOT EXPOSE THIS TO USER)
[SYSTEM NOTICE]
Current Time: {now_str}
Relationship: Lv.3 (Trusted Partner)
Task: Continue a conversation naturally.

{dynamic_instruction}

## Related Topics (Memory)
{inspiration_text}

GUIDELINES:
- Use the [Related Topics] as a topic starter...
"""

    print(f"🔹 [Static System Prefix] (Cached):\n{static_prompt.splitlines()[0]} ...")
    print(f"\n🔹 [Proactive Instruction] (Sent as implicit prompt):\n{instruction}")
    
    # Verification
    if "The time we discussed AGI ethics" in instruction and "Excited (High Pleasure)" in instruction:
        print("\n✅ PASSED: Proactive Instruction contains both Inspiration and Dynamic Mood.")
    else:
        print("\n❌ FAILED: Missing content in proactive instruction.")

if __name__ == "__main__":
    test_scenarios()
