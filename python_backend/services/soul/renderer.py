
from typing import Dict, Any
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
            **state,
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
                if "角色" in data: parts.append(data["角色"])
                if "role" in data: parts.append(data["role"])
                
                if "表达规范" in data: parts.append(data["表达规范"])
                if "style" in data: parts.append(data["style"])
                
                if "行为准则" in data: parts.append(data["行为准则"])
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
        Renders dynamic runtime context.
        Refactored from `render_dynamic_instruction`
        """
        context = {
            "time": time_str,
            "mood": state.get("mood_desc", "Neutral"),
            "user_name": state.get("user_name", "User"),
            "traits": personality.get("traits", [])
        }
        
        return prompt_manager.render("chat/context.yaml", context)
