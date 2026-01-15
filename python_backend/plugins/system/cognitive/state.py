from typing import List, Dict, Any, Optional
from pydantic import BaseModel, Field
from enum import Enum
from datetime import datetime

class InteractionPhase(str, Enum):
    IDLE = "idle"
    LISTENING = "listening"
    THINKING = "thinking"
    SPEAKING = "speaking"
    DREAMING = "dreaming"

class PersonaSpec(BaseModel):
    name: str
    description: str
    tone: str
    constraints: List[str] = Field(default_factory=list)

class SessionState(BaseModel):
    session_id: int
    phase: InteractionPhase = InteractionPhase.IDLE
    current_emotion: str = "neutral"
    arousal: float = 0.5
    valence: float = 0.5
    short_term_history: List[Dict[str, str]] = Field(default_factory=list)
    pending_tool_outputs: List[Dict] = Field(default_factory=list)

class CognitiveContext(BaseModel):
    persona: PersonaSpec
    state: SessionState
