from enum import StrEnum
from typing import Dict, Any, List, Optional
from dataclasses import dataclass, field
import re
import logging

logger = logging.getLogger("IntentClassifier")

class IntentType(StrEnum):
    CHAT = "chat"       # Standard conversation
    TASK = "task"       # Complex task requesting tools
    QUERY = "query"     # Knowledge retrieval (RAG)
    VISION = "vision"   # Visual request
    CONTROL = "control" # System control (stop, pause)

@dataclass
class IntentResult:
    type: IntentType
    confidence: float
    details: Dict[str, Any] = field(default_factory=dict)

class IntentClassifier:
    """
    Classifies user input into cognitive intents.
    Strategy: Rule-based (Fast) -> LLM-based (Slow/Accurate).
    """
    
    def __init__(self):
        # Regex Rules [Pattern, Intent, Confidence]
        self.rules = [
            (r"(?i)^(search|find|look up|google)\b", IntentType.TASK, 0.8),
            (r"(?i)^(calculate|compute|solve)\b", IntentType.TASK, 0.9),
            (r"(?i)^(draw|generate|paint|create an image)\b", IntentType.TASK, 0.9),
            (r"(?i)^(remember|save|note that)\b", IntentType.TASK, 0.8), # Application Control
            (r"(?i)^(see|look at|what is on|screenshot)\b", IntentType.VISION, 0.9),
            (r"(?i)^(stop|pause|shut down|terminate)\b", IntentType.CONTROL, 1.0),
        ]
        
    async def classify(self, text: str, user_id: str = None) -> Dict[str, Any]:
        """
        Determine intent from text.
        Returns dict matching IntentResult structure.
        """
        if not text:
             return {"type": IntentType.CHAT, "confidence": 1.0}

        # 1. Rule-based Check
        for pattern, intent, conf in self.rules:
            if re.search(pattern, text):
                logger.info(f"Rule Matched: {pattern} -> {intent}")
                return {"type": intent, "confidence": conf, "details": {"source": "rule"}}

        # 2. Heuristics
        # If text is very long, might be a task?
        if len(text) > 500:
             return {"type": IntentType.TASK, "confidence": 0.6, "details": {"reason": "length"}}
        
        # 3. Default to Chat (System 1)
        # Future: Call small LLM classifier here
        return {"type": IntentType.CHAT, "confidence": 0.5, "details": {"source": "default"}}
