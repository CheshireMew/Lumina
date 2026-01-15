from typing import Any, Dict, Optional, Literal
from pydantic import BaseModel, Field
import time
import uuid

# --- Event Types (The Whitelist) ---
class EventType:
    # Input (Source: Frontend/Hardware)
    INPUT_TEXT = "input_text"
    INPUT_AUDIO = "input_audio"        # Raw chunks
    INPUT_AUDIO_END = "input_audio_end" # VAD End
    
    # Brain (Source: Orchestrator/LLM)
    BRAIN_THINKING = "brain_thinking"  # "Lett me think..."
    BRAIN_RESPONSE = "brain_response"  # Final text segment
    BRAIN_TOOL_CALL = "brain_tool_call"
    
    # Output (Source: TTS/Frontend)
    OUTPUT_AUDIO = "output_audio"      # TTS chunks
    OUTPUT_SUBTITLE = "output_subtitle"
    
    # Control (Source: System)
    CONTROL_INTERRUPT = "control_interrupt" # "Stop!"
    CONTROL_SESSION = "control_session"     # New Session ID
    SYSTEM_STATUS = "system_status"         # Heartbeat/Ready
    COGNITIVE_STATE = "cognitive_state"     # State Machine (Idle/Thinking/Speaking)

# --- The Unified Packet ---
class EventPacket(BaseModel):
    """
    Standard Data Unit for the Lumina Event Bus.
    Conforms to 'First Principles' architecture.
    """
    # 1. Transport Layer
    trace_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    session_id: int = Field(..., description="Global interaction version for interrupt logic")
    type: str = Field(..., description="EventType string")
    source: str = Field(..., description="Plugin Name or Component ID")
    
    # 2. Payload Layer (Flexible)
    payload: Any = Field(default_factory=dict)
    
    # 3. Governance Layer
    timestamp: float = Field(default_factory=time.time)
    
    # 4. Routing Hooks (Optional)
    # ttl: int = 10 
    # parent_id: Optional[str] = None
