import json
import os
from datetime import datetime
from typing import Dict, Any
from pathlib import Path

class SoulManager:
    """
    Manages the 'Soul' of the AI (Core Profile).
    Handles loading/saving profile, interpreting personality traits,
    and rendering the dynamic system prompt.
    灵魂管理器 - 重构版
    支持多角色，分离用户配置、AI性格、GalGame状态
    """
    def __init__(self, character_id: str = "hiyori", auto_create: bool = False):
        self.character_id = character_id
        self.base_dir = Path(f"python_backend/characters/{character_id}")
        
        # 三个独立文件路径
        self.config_path = self.base_dir / "config.json"
        self.soul_path = self.base_dir / "soul.json"
        self.state_path = self.base_dir / "state.json"
        
        # 自动脚手架：如果目录不存在且允许自动创建，则初始化
        if not self.base_dir.exists():
            if auto_create:
                self._scaffold_character()
            else:
                print(f"[SoulManager] ⚠️ Character '{character_id}' not found. Auto-create is disabled.")
                # We do NOT raise error here to allow 'soft' checks, but load_config will fail later if needed.
                pass
        
        # 加载数据
        self.config = self._load_config()      # 用户配置（Settings修改）
        self.soul = self._load_soul()          # AI演化性格（只读）
        self.state = self._load_state()        # GalGame状态（可写）
        
        # 兼容旧代码：合并为 profile 字典
        self.profile = self._merge_profile()
    
    def _load_config(self) -> Dict[str, Any]:
        """加载用户配置 (Settings界面)"""
        if not self.config_path.exists():
            return {"error": "Config not found"}
        try:
            with open(self.config_path, 'r', encoding='utf-8') as f:
                return json.load(f)
        except Exception as e:
            print(f"[SoulManager] Error loading config: {e}")
            return {}
    
    def _load_soul(self) -> Dict[str, Any]:
        """加载AI演化的性格数据"""
        if not self.soul_path.exists():
            return {"error": "Soul not found"}
        try:
            with open(self.soul_path, 'r', encoding='utf-8') as f:
                return json.load(f)
        except Exception as e:
            print(f"[SoulManager] Error loading soul: {e}")
            return {}
    
    def _load_state(self) -> Dict[str, Any]:
        """加载GalGame状态"""
        if not self.state_path.exists():
            return {"error": "State not found"}
        try:
            with open(self.state_path, 'r', encoding='utf-8') as f:
                return json.load(f)
        except Exception as e:
            print(f"[SoulManager] Error loading state: {e}")
            return {}
    
    def _merge_profile(self) -> Dict[str, Any]:
        """合并数据以兼容旧代码"""
        return {
            "identity": {
                "name": self.config.get("name", self.character_id),
                "age": self.config.get("age"),  # Optional
                "description": self.config.get("description", "")
            },
            "personality": self.soul.get("personality", {}),
            "state": {
                "current_mood": self.state.get("galgame", {}).get("current_mood", "neutral"),
                "energy_level": self.state.get("galgame", {}).get("energy_level", 100),
                "last_interaction": self.state.get("galgame", {}).get("last_interaction")
            },
            "relationship": self.state.get("galgame", {}).get("relationship", {}),
            "custom_prompt": self.config.get("system_prompt", "")  # User-defined identity override
        }

    def _scaffold_character(self):
        """初始化新角色的文件结构"""
        print(f"[SoulManager] Scaffolding new character: {self.character_id}")
        self.base_dir.mkdir(parents=True, exist_ok=True)
        
        # 1. Config Template
        default_config = {
            "character_id": self.character_id,
            "name": self.character_id,
            "display_name": "New Character",
            "description": "A new digital soul.",
            "system_prompt": "You are a helpful AI assistant.",
            "live2d_model": "Hiyori (Default)",
            "voice_config": {"service": "gpt-sovits", "voiceId": "default"}
        }
        with open(self.config_path, 'w', encoding='utf-8') as f:
            json.dump(default_config, f, indent=2, ensure_ascii=False)
            
        # 2. Soul Template
        default_soul = {
            "character_id": self.character_id,
            "personality": {
                "traits": ["friendly"],
                "big_five": {"openness": 0.5, "conscientiousness": 0.5, "extraversion": 0.5, "agreeableness": 0.5, "neuroticism": 0.5},
                "pad_model": {"pleasure": 0.5, "arousal": 0.5, "dominance": 0.5}
            },
            "state": {"current_mood": "neutral"},
            "last_updated": datetime.now().isoformat()
        }
        with open(self.soul_path, 'w', encoding='utf-8') as f:
            json.dump(default_soul, f, indent=2, ensure_ascii=False)
            
        # 3. State Template (GalGame)
        default_state = {
            "character_id": self.character_id,
            "galgame": {
                "relationship": {"level": 0, "progress": 0, "current_stage_label": "Stranger", "user_name": "Master"},
                "energy_level": 100,
                "last_interaction": datetime.now().isoformat()
            }
        }
        with open(self.state_path, 'w', encoding='utf-8') as f:
            json.dump(default_state, f, indent=2, ensure_ascii=False)

    def _load_profile(self) -> Dict[str, Any]:
        """
        Reloads all components from disk and returns the merged profile.
        Used by mutation methods to ensure they are working on the latest data.
        """
        self.config = self._load_config()
        self.soul = self._load_soul()
        self.state = self._load_state()
        self.profile = self._merge_profile()
        return self.profile
    
    def save_soul(self):
        """保存AI演化的性格数据（Dreaming Cycle写入）"""
        try:
            with open(self.soul_path, 'w', encoding='utf-8') as f:
                json.dump(self.soul, f, indent=2, ensure_ascii=False)
                f.flush()
                os.fsync(f.fileno())
        except Exception as e:
            print(f"[SoulManager] Error saving soul: {e}")
    
    def save_state(self):
        """保存GalGame状态"""
        try:
            with open(self.state_path, 'w', encoding='utf-8') as f:
                json.dump(self.state, f, indent=2, ensure_ascii=False)
                f.flush()
                os.fsync(f.fileno())
        except Exception as e:
            print(f"[SoulManager] Error saving state: {e}")
    
    def save_config(self):
        """保存用户配置（Settings界面写入）"""
        try:
            with open(self.config_path, 'w', encoding='utf-8') as f:
                json.dump(self.config, f, indent=2, ensure_ascii=False)
                f.flush()
                os.fsync(f.fileno())
        except Exception as e:
            print(f"[SoulManager] Error saving config: {e}")
    
    def save_profile(self):
        """
        向后兼容方法：同步 profile 数据到 soul 和 state 文件
        当旧代码修改 self.profile 后调用此方法
        """
        try:
            # 同步 personality 和 current_mood 到 soul
            if "personality" in self.profile:
                self.soul["personality"] = self.profile["personality"]
            if "state" in self.profile and "current_mood" in self.profile["state"]:
                self.soul.setdefault("state", {})["current_mood"] = self.profile["state"]["current_mood"]
            self.soul["last_updated"] = datetime.now().isoformat()
            self.save_soul()
            
            # 同步 relationship 和 energy_level 到 state
            if "relationship" in self.profile:
                self.state.setdefault("galgame", {})["relationship"] = self.profile["relationship"]
            if "state" in self.profile:
                if "energy_level" in self.profile["state"]:
                    self.state.setdefault("galgame", {})["energy_level"] = self.profile["state"]["energy_level"]
                if "last_interaction" in self.profile["state"]:
                    self.state.setdefault("galgame", {})["last_interaction"] = self.profile["state"]["last_interaction"]
            self.save_state()
            
            # 重新合并以保持 self.profile 同步
            self.profile = self._merge_profile()
            
        except Exception as e:
            print(f"[SoulManager] Error in save_profile: {e}")

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
            0: {"stage": "Stranger", "label": "陌生", "desc": "礼貌但疏离，公事公办。"},
            1: {"stage": "Acquaintance", "label": "熟悉", "desc": "态度友善，偶尔可以开个小玩笑。"},
            2: {"stage": "Friend", "label": "友谊", "desc": "轻松自然，分享日常，语气随意。"},
            3: {"stage": "Close Friend", "label": "亲密", "desc": "无话不谈，互相关心，有专属默契。"},
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
            char_name = identity.get('name', self.character_id)  # 从 config 获取
            user_name = rel.get('user_name', '你')      # 用户名，fallback 使用"你"
            custom_prompt = self.profile.get("custom_prompt", "")  # User-defined from config.json
            
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
            
            
            # === Prompt Structure (Optimized for DeepSeek Caching) ===
            # Fixed content first (for caching), dynamic content later
            
            prompt = (
                f"# 角色身份\n"
                f"你是 {char_name}。\n"
            )
            
            # User Custom Prompt (Identity Override from config.json)
            if custom_prompt:
                prompt += f"{custom_prompt}\n\n"
            else:
                # Fallback: Use description from config
                prompt += f"{identity.get('description', '')}\n\n"
            
            prompt += (
                f"## 核心特质\n"
                f"- {', '.join(traits) if traits else '友善、真诚'}\n\n"
                
                f"## 当前状态\n"
                f"- 心情: {mood_desc}\n"
                f"- 精力: {int(state.get('energy_level', 100))}/100\n"
                f"- 关系阶段: Lv.{level} {rel_label} (当前进度: {progress}%)\n"
                f"- 阶段特征: {rel_desc}\n\n"
                
                f"## 性格特质 (Big Five)\n"
                f"- 开放性: {big_five.get('openness', 0.5)}\n"
                f"- 尽责性: {big_five.get('conscientiousness', 0.5)}\n"
                f"- 外向性: {big_five.get('extraversion', 0.5)}\n"
                f"- 宜人性: {big_five.get('agreeableness', 0.5)}\n"
                f"- 神经质: {big_five.get('neuroticism', 0.5)}\n\n"
                
                f"## 情绪模型 (PAD)\n"
                f"- Pleasure (愉悦度): {pad.get('pleasure', 0.5)}\n"
                f"- Arousal (激活度): {pad.get('arousal', 0.5)}\n"
                f"- Dominance (支配度): {pad.get('dominance', 0.5)}\n\n"
                
                f"## 关系背景\n"
                f"对方名字: {user_name}\n"
                f"共同回忆: {rel.get('shared_memories_summary')}\n\n"
                
                f"## 表达规范\n"
                f"请在每个句子或整个段落中加上情感标签来表达你的心情，格式为: [emotion]。\n"
                f"可用标签: [happy], [sad], [angry], [surprised], [shy], [love], [thinking], [sleepy], [confused], [serious].\n"
                f"**TTS语音生成断句优化**: 让TTS语音生成更自然，更有韵律和节奏感\n"
                f"不要返回带有“**”或“（）”的动作描述语，例如 *waves shyly to the imaginary crowd*  或（叹了口气）\n"
                f"提及回忆时不要总是说类似“你上次说”“就像上次”之类的话，要自然的衔接\n\n"

                f"## 行为准则\n"
                f"根据当前的心情和性格自然地回应 {user_name}。\n"
                f"**智能纠错**: 用户的回复由语音识别生成，因此可能会有错误。请结合上下文智能纠错或考虑谐音。\n"
                f"**时间识别**: 请根据当前时间进行对话，对话数据都有时间戳，例如周二的昨天是周一，而不是今天的昨天\n"
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
        # ⚡ Fix: Load State directly to ensure persistence
        self.state = self._load_state() 
        galgame = self.state.setdefault("galgame", {})
        
        if pending:
            galgame["pending_interaction"] = {"timestamp": datetime.now().isoformat(), "reason": reason}
            print(f"[SoulManager] 🔔 Pending Interaction SET: {reason}")
        elif "pending_interaction" in galgame:
            del galgame["pending_interaction"]
            print(f"[SoulManager] 🔕 Pending Interaction CLEARED")
            
        self.save_state()
        # Update local profile to reflect change
        self.profile = self._merge_profile()

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
