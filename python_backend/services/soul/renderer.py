
from typing import Dict, Any, Optional
from prompt_manager import prompt_manager

class SoulRenderer:
    """
    璐熻矗灏?Soul 鐨勭姸鎬佽浆鎹负鏈€缁堢殑 System Prompt銆?
    鍘熷垯锛氱函鍑芥暟锛屾棤鐘舵€侊紝鍙礋璐f覆鏌撳瓧绗︿覆銆?
    """
    
    def render(self, 
               config_prompt: str,
               identity: Dict[str, Any],
               personality: Dict[str, Any],
               state: Dict[str, Any],
               user_context: Dict[str, Any] = {}) -> str:
        """
        Main entry point for prompt rendering.
        """
        # 1. Prepare base context
        context = {
            "char_name": identity.get("name", ""),
            "description": identity.get("description", ""),
            "custom_prompt": config_prompt,
            **personality, # traits, big_five, etc.
            **state,       # galgame state, mood, etc.
        }
        
        # 2. Inject extra user context
        context.update(user_context)
        
        # 3. Handle Mood Description (if not already handled by helper)
        if "current_mood" in state and "description" in context:
             context["description"] += f"\nCurrent Mood: {state['current_mood']}"

        try:
            # 4. Load & Render Template via PromptManager
            # Uses 'chat/system.yaml'
            data = prompt_manager.load_structured("chat/system.yaml", context)
            
            if isinstance(data, dict):
                parts = []
                # Order matters: Role -> Style -> Constraints
                if "瑙掕壊" in data: parts.append(data["瑙掕壊"])
                if "role" in data: parts.append(data["role"])
                
                if "琛ㄨ揪瑙勮寖" in data: parts.append(data["琛ㄨ揪瑙勮寖"])
                if "style" in data: parts.append(data["style"])
                
                if "琛屼负鍑嗗垯" in data: parts.append(data["琛屼负鍑嗗垯"])
                if "constraints" in data: parts.append(data["constraints"])
                
                full_prompt = "\n\n".join(parts)
                # Fallback if empty
                if not full_prompt.strip():
                     return config_prompt
                return full_prompt
            
            return str(data)
            
        except Exception as e:
            print(f"[SoulRenderer] Render failed: {e}")
            return config_prompt or "You are a helpful AI."

    def render_dynamic_context(self, 
                               state: Dict[str, Any], 
                               personality: Dict[str, Any], 
                               time_str: str) -> str:
        """
        Renders dynamic runtime context (Time, Mood, Energy, Relationship).
        Refactored from `render_dynamic_instruction`
        """
        # Note: Logic for generating 'descriptions' from numbers (PAD/Energy) 
        # should technically belong to a logic layer, but we can accept pre-processed values here.
        
        context = {
            "time": time_str,
            "mood": state.get("mood_desc", "Neutral"),
            "user_name": state.get("user_name", "User"),
            "traits": personality.get("traits", [])
        }
        
        return prompt_manager.render("chat/context.yaml", context)
