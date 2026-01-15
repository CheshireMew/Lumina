import logging
from typing import Dict, Any

logger = logging.getLogger("SoulMath")

class SoulMath:
    """
    Mental Math for Soul & Galgame Logic.
    Separated from Infrastructure (LLMManager).
    """

    @staticmethod
    def calculate_llm_params(base_params: Dict[str, float], soul_state: Dict[str, Any], feature: str = "chat") -> Dict[str, float]:
        """
        Refined Algorithm: Introduces "Bipolar Social Tension" Model (-3 to 5)
        Both deep love and extreme hate trigger higher expression bandwidth; only indifference and strangeness cause contraction.
        
        Args:
            base_params: Base parameters from LLM Config (temperature, top_p, etc.)
            soul_state: SoulManager.profile (contains personality, state, relationship, etc.)
        """
        new_params = base_params.copy()
        
        # 0. Data Defense
        if not soul_state:
            return new_params

        # 1. Extract Base Variables
        # Compatible with SoulManager.profile structure
        # profile = { "personality": {...}, "state": {...}, "relationship": {...} }
        
        personality = soul_state.get("personality", {})
        state = soul_state.get("state", {})
        relationship = soul_state.get("relationship", {}) # May be directly in root or in galgame 
        # SoulManager._merge_profile() puts relationship in root of profile dict.
        
        pad = personality.get("pad_model", {"pleasure": 0.5, "arousal": 0.5, "dominance": 0.5})
        b5 = personality.get("big_five", {"openness": 0.5, "conscientiousness": 0.5, "extraversion": 0.5, "agreeableness": 0.5, "neuroticism": 0.5})
        
        p = float(pad.get("pleasure", 0.5))
        a = float(pad.get("arousal", 0.5))
        d = float(pad.get("dominance", 0.5))
        
        energy = float(state.get("energy_level", 100)) / 100.0
        rel_level = int(relationship.get("level", 0))
        
        # --- A. Personality Baseline (Big Five Baseline) ---
        # 1. Openness: Higher means more creative
        b5_temp_base = (float(b5.get("openness", 0.5)) - 0.5) * 0.4
        b5_top_p_base = (float(b5.get("openness", 0.5)) - 0.5) * 0.2
        
        # 2. Conscientiousness: Higher means more rigorous/stable (lowers randomness)
        b5_temp_base -= (float(b5.get("conscientiousness", 0.5)) - 0.5) * 0.3
        b5_top_p_base -= (float(b5.get("conscientiousness", 0.5)) - 0.5) * 0.2
        
        # 3. Extraversion: Higher means loves discussing new topics
        b5_pp_base = (float(b5.get("extraversion", 0.5)) - 0.5) * 0.4
        
        # 4. Agreeableness: Higher means gentler, stable topic switching (low PP), polite (high FP)
        b5_pp_base -= (float(b5.get("agreeableness", 0.5)) - 0.5) * 0.2
        b5_fp_base = (float(b5.get("agreeableness", 0.5)) - 0.5) * 0.3
        
        # 5. Neuroticism: Higher means emotional instability amplifies multiplier
        emotional_instability = 1.0 + (float(b5.get("neuroticism", 0.5)) - 0.5) * 1.5
        
        # --- B. Dynamic Emotions (PAD Dynamic Shifts) ---
        # Shifts here are scaled by Neuroticism (Instability) and Energy
        mood_temp_shift = (p - 0.5) * 0.4 
        mood_top_p_shift = (a - 0.5) * 0.3
        mood_pp_shift = (d - 0.5) * 0.5
        mood_fp_shift = (d - 0.5) * 0.3
        
        # 2. Relationship Impact Matrix
        # Format: { level: (temp_offset, top_p_offset, pp_offset, fp_offset) }
        # TODO: Move to config? For now keep here as "Default Rules"
        rel_matrix = {
            -3: (0.50, 0.20, 0.60, 0.40),  # Nemesis
            -2: (0.25, 0.10, 0.30, 0.20),  # Hostile
            -1: (-0.30, -0.20, -0.20, -0.10), # Indifferent
            0:  (0.00, 0.00, 0.00, 0.00),  # Stranger
            1:  (0.10, 0.05, 0.05, 0.00),  # Acquaintance
            2:  (0.20, 0.10, 0.10, 0.05),  # Friend
            3:  (0.35, 0.15, 0.25, 0.10),  # Close Friend
            4:  (0.50, 0.25, 0.40, 0.20),  # Ambiguous
            5:  (0.70, 0.35, 0.60, 0.30)   # Soulmate
        }
        
        rel_offsets = rel_matrix.get(rel_level, (0, 0, 0, 0))
        
        # 3. Dynamic Calculation
        
        # A. Energy Constraint
        energy_mod = 1.0
        if energy < 0.2: energy_mod = 0.4
        elif energy > 0.8: energy_mod = 1.2
        
        # Unified Dynamic Shift Factor (Personality Sensitivity * Energy)
        dynamic_factor = energy_mod * emotional_instability
        
        # B. Combined Calc (Base + Personality + (Dynamic Mood * Factor) + Relationship Offset)
        new_params["temperature"] = new_params.get("temperature", 0.7) + b5_temp_base + (mood_temp_shift * dynamic_factor) + rel_offsets[0]
        new_params["top_p"] = new_params.get("top_p", 1.0) + b5_top_p_base + (mood_top_p_shift * dynamic_factor) + rel_offsets[1]
        new_params["presence_penalty"] = new_params.get("presence_penalty", 0.0) + b5_pp_base + (mood_pp_shift * dynamic_factor) + rel_offsets[2]
        new_params["frequency_penalty"] = new_params.get("frequency_penalty", 0.0) + b5_fp_base + (mood_fp_shift * dynamic_factor) + rel_offsets[3]
        
        # 4. Special Context Hard Clip (The "Social Mask" at Level 0)
        if rel_level == 0:
            # Strangers must maintain social restraint
            new_params["temperature"] = min(0.8, new_params["temperature"])
            new_params["top_p"] = min(0.8, new_params["top_p"])
        elif rel_level == -1:
            # Indifferent state forbids high activity
            new_params["temperature"] = min(0.6, new_params["temperature"])
        
        # 5. Precision Handling & Boundary Safety
        new_params["temperature"] = float(round(max(0.1, min(2.0, new_params["temperature"])), 2))
        new_params["top_p"] = float(round(max(0.1, min(1.0, new_params["top_p"])), 2))
        new_params["presence_penalty"] = float(round(max(-2.0, min(2.0, new_params["presence_penalty"])), 2))
        new_params["frequency_penalty"] = float(round(max(-2.0, min(2.0, new_params["frequency_penalty"])), 2))
        
        if feature == "chat":
             logger.info(f"[SoulMath] Logic Applied: L:{rel_level}, E:{energy:.2f} -> {new_params}")
            
        return new_params

    @staticmethod
    def get_relationship_stage(level: int) -> Dict[str, str]:
        """
        Determines current relationship based on LEVEL.
        """
        stages = {
            -3: {"stage": "Nemesis", "label": "Nemesis", "desc": "Bone-chilling coldness like eternal winter. Words carry sharp edges without disguise; not just rejection, but a spiritual banishment."},
            -2: {"stage": "Hostile", "label": "Hostile", "desc": "Full of guard and rejection. Like a startled cat, hostile to every approach, words with thorns, unwilling to show any softness."},
            -1: {"stage": "Indifferent", "label": "Indifferent", "desc": "Stagnant water without ripples. You are just background noise to them; responses limited to mechanical info exchange, no eye contact, no emotional fluctuation."},
            0: {"stage": "Stranger", "label": "Stranger", "desc": "Polite but distant. A perfect mask observing social etiquette; polite but only polite, conversations feel like talking through glass."},
            1: {"stage": "Acquaintance", "label": "Acquaintance", "desc": "A passerby who occasionally stops to chat. Starts to have warmth, willing to share trivia like weather, but stops there; boundaries clear and safe."},
            2: {"stage": "Friend", "label": "Friend", "desc": "Comfortable mode of getting along. Can drop some defenses, share daily joys and sorrows, laughter points start to overlap, silence is no longer awkward."},
            3: {"stage": "Close Friend", "label": "Close Friend", "desc": "Resonance of souls. No need for many words to understand the unspoken; a safe harbor for each other, can show vulnerability frankly."},
            4: {"stage": "Ambiguous", "label": "Ambiguous", "desc": "More than friends, subtle tension in the air. Not simple shyness, but every eye contact has a current flowing; starting to care about gaze duration, finding unnecessary reasons to get closer."},
            5: {"stage": "Soulmate", "label": "Soulmate", "desc": "Deep connection beyond language. Not constant sweet talk, but deep understanding and companionship. You are her world's anchor; whenever she looks back, you are there. A sense of 'I am here' certainty."}
        }
        return stages.get(level, stages[0])

    @staticmethod
    def get_energy_instruction(energy: float) -> str:
        """
        Maps Energy Level to Tone and Length instructions.
        """
        if energy >= 80:
            return "Energy is HIGH. Speak enthusiastically, use exclamation marks, and be verbose! Expanded sentences."
        elif energy >= 40:
            return "Energy is NORMAL. Speak typically, balanced sentence length."
        else:
            return "Energy is LOW. Speak softly, briefly, and maybe complain about being tired. Use short sentences."

    @staticmethod
    def get_pad_description(pleasure: float, arousal: float) -> str:
        """
        Converts PAD (Pleasure, Arousal) to adjective.
        """
        if pleasure > 0.7:
            if arousal > 0.6: return "Excited/Joyful"
            return "Content/Relaxed"
        elif pleasure < 0.3:
            if arousal > 0.6: return "Angry/Anxious"
            return "Sad/Depressed"
        else:
            if arousal > 0.7: return "Alert"
            return "Neutral/Calm"
