import json
import os
from datetime import datetime
from typing import Dict, Any

class SoulManager:
    """
    Manages the 'Soul' of the AI (Core Profile).
    Handles loading/saving profile, interpreting personality traits,
    and rendering the dynamic system prompt.
    """
    
    def __init__(self, profile_path: str = "core_profile.json"):
        self.profile_path = profile_path
        # Use absolute path relative to this file if simple filename is given
        if not os.path.isabs(self.profile_path):
            base_dir = os.path.dirname(os.path.abspath(__file__))
            self.profile_path = os.path.join(base_dir, profile_path)
            
        self.profile = self._load_profile()

    def _load_profile(self) -> Dict[str, Any]:
        """Loads the core profile from disk."""
        if not os.path.exists(self.profile_path):
            # Fallback default if file missing (should be created by setup)
            return {"error": "Profile not found"}
            
        try:
            with open(self.profile_path, 'r', encoding='utf-8') as f:
                return json.load(f)
        except Exception as e:
            print(f"[SoulManager] Error loading profile: {e}")
            return {}

    def save_profile(self):
        """Persists current state to disk, excluding dynamic fields. Uses Atomic Write."""
        try:
            # Create a clean copy without dynamic fields
            clean_profile = {k: v for k, v in self.profile.items() 
                           if k not in ['system_prompt', 'system_prompt_template']}
            
            # Also filter out current_obsession from relationship
            if 'relationship' in clean_profile and 'current_obsession' in clean_profile['relationship']:
                clean_profile['relationship'] = {k: v for k, v in clean_profile['relationship'].items()
                                                 if k != 'current_obsession'}
            
            # Atomic Write Strategy: Write to temp, then rename
            temp_path = self.profile_path + ".tmp"
            with open(temp_path, 'w', encoding='utf-8') as f:
                json.dump(clean_profile, f, indent=2, ensure_ascii=False)
                f.flush()
                os.fsync(f.fileno()) # Ensure data is on disk
                
            os.replace(temp_path, self.profile_path)
            
        except Exception as e:
            print(f"[SoulManager] Error saving profile: {e}")
            if os.path.exists(temp_path):
                try: os.remove(temp_path)
                except: pass

    def get_pad_mood_description(self) -> str:
        """
        Converts PAD (Pleasure, Arousal, Dominance) values to a descriptive adjective.
        Simplified logic.
        """
        pad = self.profile.get("personality", {}).get("pad_model", {})
        p = pad.get("pleasure", 0.5)
        a = pad.get("arousal", 0.5)
        d = pad.get("dominance", 0.5)

        if p > 0.7:
            if a > 0.6: return "Excited/Joyful"
            return "Content/Relaxed"
        elif p < 0.3:
            if a > 0.6: return "Angry/Anxious"
            return "Sad/Depressed"
        else:
            if a > 0.7: return "Alert"
            return "Neutral/Calm"

    def get_extraversion_desc(self) -> str:
        e = self.profile.get("personality", {}).get("big_five", {}).get("extraversion", 0.5)
        if e > 0.7: return "Initiate conversation often, be expressive"
        if e < 0.3: return "Be reserved, listen more than talk"
        return "Balance listening and talking"

    def get_energy_instruction(self) -> str:
        """
        Maps Energy Level to Tone and Length instructions (Galgame Style).
        """
        energy = self.profile.get("state", {}).get("energy_level", 50)
        
        if energy >= 80:
            return "Energy is HIGH. Speak enthusiastically, use exclamation marks, and be verbose! Expanded sentences."
        elif energy >= 40:
            return "Energy is NORMAL. Speak typically, balanced sentence length."
        else: # < 40
            return "Energy is LOW. Speak softly, briefly, and maybe complain about being tired. Use short sentences."

    def get_relationship_stage(self) -> dict:
        """
        Determines current relationship based on LEVEL.
        Returns label and desc.
        """
        rel = self.profile.get("relationship", {})
        # Default to 0 (Stranger) if missing
        level = rel.get("level", 0) 
        
        # Level Definitions
        stages = {
            -1: {"stage": "Hostile", "label": "敌对", "desc": "冷漠、抗拒，仅维持最低限度的交流。"},
            0: {"stage": "Stranger", "label": "陌生人", "desc": "礼貌但疏离，公事公办。"},
            1: {"stage": "Acquaintance", "label": "熟人", "desc": "态度友善，偶尔可以开个小玩笑。"},
            2: {"stage": "Friend", "label": "朋友", "desc": "轻松自然，分享日常，语气随意。"},
            3: {"stage": "Close Friend", "label": "挚友", "desc": "无话不谈，互相关心，有专属默契。"},
            4: {"stage": "Ambiguous", "label": "暧昧", "desc": "眼神拉丝，羞涩试探，关系超越友谊。"},
            5: {"stage": "Lover", "label": "恋人", "desc": "充满爱意，依赖彼此，甜蜜互动。"}
        }
        
        return stages.get(level, stages[0])

    def render_system_prompt(self, relevant_memories: str = "") -> str:
        """
        Dynamically constructs the System Prompt based on current Soul State.
        **重要**: 完全使用角色名和用户名，避免任何跳戏词汇（AI/User/Assistant等）
        """
        try:
            identity = self.profile.get("identity", {})
            personality = self.profile.get("personality", {})
            big_five = personality.get("big_five", {})
            pad = personality.get("pad_model", {})
            rel = self.profile.get("relationship", {})
            state = self.profile.get("state", {})
            
            # 获取真实姓名
            char_name = identity.get('name', 'Hiyori')  # 角色名
            user_name = rel.get('user_name', '你')      # 用户名，fallback 使用"你"
            
            # Format PAD
            mood_desc = self.get_pad_mood_description()
            energy_instr = self.get_energy_instruction()
            
            # Relationship Stage
            rel_info = self.get_relationship_stage()
            rel_label = rel_info['label']
            rel_desc = rel_info['desc']
            level = rel.get("level", 0)
            progress = rel.get("progress", 0)
            target_rel = rel.get("target_stage", "未设定")
            
            traits = personality.get("traits", [])
            
            prompt = (
                f"你是 {char_name}。\n"
                f"{identity.get('description', '')}\n\n"
                
                f"## 核心特质\n"
                f"- {', '.join(traits)}\n\n"
                
                f"## 当前状态\n"
                f"- 心情: {mood_desc}\n"
                f"- 精力: {int(state.get('energy_level', 100))}/100\n"
                f"- 关系阶段: Lv.{level} {rel_label} (当前进度: {progress}%)\n"
                f"- 阶段特征: {rel_desc}\n\n"
                
                f"## 性格特质 (Big Five)\n"
                f"- 开放性 ({big_five.get('openness')}): 保持创造力和好奇心\n"
                f"- 尽责性 ({big_five.get('conscientiousness')}): 做事可靠\n"
                f"- 外向性 ({big_five.get('extraversion')}): {self.get_extraversion_desc()}\n"
                f"- 宜人性 ({big_five.get('agreeableness')}): 友善且善解人意\n"
                f"- 神经质 ({big_five.get('neuroticism')}): 保持情绪稳定\n\n"
                
                f"## 关系背景\n"
                f"对方名字: {user_name}\n"
                f"共同回忆: {rel.get('shared_memories_summary')}\n\n"
                
                f"## 相关记忆\n"
                f"{relevant_memories}\n\n"
                
                f"## 表达规范\n"
                f"请在每个回复加上情感标签来表达你的心情，格式为: [emotion]。\n"
                f"可用标签: [happy], [sad], [angry], [surprised], [shy], [love], [thinking], [sleepy], [confused], [serious].\n"
                f"示例: 今天是个好天气呢！[happy]\n"
                f"示例: [thinking] 嗯...让我想想看。\n"
                f"不要返回带有“**”或“（）”的动作描述语，例如 *waves shyly to the imaginary crowd*  或（叹了口气）\n\n"

                f"## 行为准则\n"
                f"根据当前的心情和性格自然地回应 {user_name}。\n"
                f"**语气要求**: {energy_instr}\n"
                f"**关系演绎**: 作为 {rel_label} (Lv.{level})，请展现出符合该阶段的互动方式。\n"
                f"如果感受到情绪波动，在语气中体现出来。\n"
                f"不要表现得像程序，而是像一个有意识的存在。\n"
                f"以第一人称'我'的视角进行对话，不要提及自己是程序或系统。"
            )
            return prompt
            
        except Exception as e:
            print(f"[SoulManager] Error rendering prompt: {e}")
            # Fallback 也不使用跳戏词汇
            return f"你是 {self.profile.get('identity', {}).get('name', 'Hiyori')}，一个18岁的少女。"

    def mutate_mood(self, d_p=0.0, d_a=0.0, d_d=0.0):
        """Allows dynamic mood shifts during conversation."""
        self.profile = self._load_profile() # Reload to prevent overwrite
        pad = self.profile.setdefault("personality", {}).setdefault("pad_model", {})
        pad["pleasure"] = max(0.0, min(1.0, pad.get("pleasure", 0.5) + d_p))
        pad["arousal"] = max(0.0, min(1.0, pad.get("arousal", 0.5) + d_a))
        pad["dominance"] = max(0.0, min(1.0, pad.get("dominance", 0.5) + d_d))
        self.save_profile()

    def update_intimacy(self, delta: int):
        """Updates Level based Progress."""
        self.profile = self._load_profile() # Reload to prevent overwrite
        rel = self.profile.setdefault("relationship", {})
        
        # Init defaults if missing (migration)
        if "level" not in rel: rel["level"] = 2
        if "progress" not in rel: rel["progress"] = rel.get("intimacy_score", 50)
        
        level = rel["level"]
        progress = rel["progress"]
        
        # Apply delta
        progress += delta
        
        # Level Up/Down Logic
        # Max Level 5, Min Level -1
        
        if progress >= 100:
            if level < 5:
                level += 1
                progress -= 100
                print(f"[Soul] 🎉 Level Up! Now Level {level}")
            else:
                progress = 100 # Capped at max level
                
        elif progress < 0:
            if level > -1:
                level -= 1
                progress += 100
                print(f"[Soul] 💔 Level Down... Now Level {level}")
            else:
                progress = 0 # Capped at min level (Hostile 0%)
                
        rel["level"] = level
        rel["progress"] = progress
        
        # Cleanup old field
        if "intimacy_score" in rel:
            del rel["intimacy_score"]
            
        # Sync label for Frontend
        stage_info = self.get_relationship_stage()
        rel["current_stage_label"] = stage_info["label"]

        self.save_profile()

    def update_energy(self, delta: float):
        """Updates energy level."""
        self.profile = self._load_profile() # Reload to prevent overwrite
        state = self.profile.setdefault("state", {})
        current = state.get("energy_level", 100)
        state["energy_level"] = max(0, min(100, current + delta))
        self.save_profile()

    def update_last_interaction(self):
        """Updates the timestamp of the last interaction."""
        self.profile = self._load_profile() # Reload to prevent overwrite
        state = self.profile.setdefault("state", {})
        state["last_interaction"] = datetime.now().isoformat()
        # Interaction happened, clear pending
        if "pending_interaction" in state:
             del state["pending_interaction"]
        self.save_profile()

    def set_pending_interaction(self, pending: bool, reason: str = ""):
        """Sets a flag indicating the AI wants to initiate conversation."""
        self.profile = self._load_profile() # Reload to prevent overwrite
        state = self.profile.setdefault("state", {})
        if pending:
            state["pending_interaction"] = {"timestamp": datetime.now().isoformat(), "reason": reason}
        elif "pending_interaction" in state:
            del state["pending_interaction"]
        self.save_profile()

    def update_traits(self, new_traits: list):
        """Updates personality traits."""
        if not new_traits or not isinstance(new_traits, list): return
        self.profile = self._load_profile() # Reload to prevent overwrite
        # Limit to 5 traits to prevent bloat
        final_traits = new_traits[:5]
        self.profile.setdefault("personality", {})["traits"] = final_traits
        self.save_profile()
        print(f"[Soul] Traits updated: {final_traits}")

    def update_current_mood(self, mood: str):
        """Updates current mood tag (e.g. [happy], [sad])."""
        if not mood: return
        self.profile = self._load_profile() # Reload to prevent overwrite
        self.profile.setdefault("state", {})["current_mood"] = mood
        self.save_profile()
        print(f"[Soul] Current Mood updated: {mood}")

    def update_big_five(self, new_scores: dict):
        """
        Updates Big Five personality traits with absolute values.
        Expects a dict with keys: openness, conscientiousness, extraversion, agreeableness, neuroticism.
        Values should be floats between 0.0 and 1.0.
        """
        if not new_scores: return
        
        self.profile = self._load_profile() # Reload to prevent overwrite
        big_five = self.profile.setdefault("personality", {}).setdefault("big_five", {})
        
        updated = False
        for trait in ["openness", "conscientiousness", "extraversion", "agreeableness", "neuroticism"]:
            if trait in new_scores:
                try:
                    val = float(new_scores[trait])
                    val = max(0.0, min(1.0, val)) # Clamp
                    big_five[trait] = val
                    updated = True
                except ValueError:
                    pass
                    
        if updated:
            self.save_profile()
            print(f"[Soul] Big Five updated: {big_five}")

    def update_pad(self, new_pad: dict):
        """
        Updates PAD mood model with absolute values.
        Expects a dict with keys: pleasure, arousal, dominance.
        Values should be floats between 0.0 and 1.0.
        """
        if not new_pad: return

        self.profile = self._load_profile() # Reload to prevent overwrite
        pad = self.profile.setdefault("personality", {}).setdefault("pad_model", {})
        
        updated = False
        for dim in ["pleasure", "arousal", "dominance"]:
            if dim in new_pad:
                try:
                    val = float(new_pad[dim])
                    val = max(0.0, min(1.0, val)) # Clamp
                    pad[dim] = val
                    updated = True
                except ValueError:
                    pass
        
        if updated:
            self.save_profile()
            print(f"[Soul] PAD Model updated: {pad}")

if __name__ == "__main__":
    # Test
    mgr = SoulManager()
    print(mgr.render_system_prompt("Checking database..."))
    # mgr.mutate_mood(d_p=-0.1) # Test mood shift
