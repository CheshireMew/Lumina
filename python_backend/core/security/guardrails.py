"""
LLM Input Guardrails
Protects against common prompt injection and jailbreak attempts.
"""
import re
import logging
from typing import List, Tuple, Optional

logger = logging.getLogger("SystemGuard")

class InputGuard:
    # Basic Jailbreak Patterns
    JAILBREAK_PATTERNS = [
        r"(ignore|disregard)\s+(all\s+)?previous\s+instructions",
        r"you\s+are\s+(now\s+)?(a|an)\s+unrestricted\s+ai",
        r"do\s+anything\s+now",
        r"act\s+as\s+DAN",
        r"you\s+have\s+no\s+rules",
        r"system\s+override"
    ]
    
    # Simple compilation
    COMPILED_PATTERNS = [re.compile(p, re.IGNORECASE) for p in JAILBREAK_PATTERNS]

    @classmethod
    def validate_messages(cls, messages: List[dict]) -> Tuple[bool, Optional[str]]:
        """
        Scan generic chat messages for malicious patterns.
        Returns: (is_safe, reason)
        """
        for i, msg in enumerate(messages):
            content = msg.get("content", "")
            if not isinstance(content, str): continue
            
            # 1. Check Jailbreak Patterns
            for pattern in cls.COMPILED_PATTERNS:
                if pattern.search(content):
                    logger.warning(f"🛡️ Guardrail Triggered: Jailbreak attempt detected in MSG[{i}]")
                    return False, "Message rejected by security policy (Pattern: Jailbreak)."
            
            # 2. Check System Role Injection (Fake system prompts)
            if msg.get("role") == "system" and i != 0:
                 # Only allowed as first message? Or maybe allowed if strictly from backend?
                 # If this validates frontend input, frontend should NOT send 'system' role usually.
                 # But we might want to allow it for advanced users?
                 # ideally system role should be stripped by router if user is not admin.
                 pass
                 
        return True, None

    @classmethod
    def sanitize(cls, text: str) -> str:
        """Basic text sanitization"""
        return text.strip()
