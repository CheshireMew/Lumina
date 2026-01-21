from typing import Any, Dict, Optional, Literal, List, Type
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
    BRAIN_RESPONSE_END = "brain_response_end"
    BRAIN_TOOL_CALL = "brain_tool_call"
    
    # Output (Source: TTS/Frontend)
    OUTPUT_AUDIO = "output_audio"      # TTS chunks
    OUTPUT_SUBTITLE = "output_subtitle"
    
    # Control (Source: System)
    CONTROL_INTERRUPT = "control_interrupt" # "Stop!"
    CONTROL_SESSION = "control_session"     # New Session ID
    SYSTEM_STATUS = "system_status"         # Heartbeat/Ready
    COGNITIVE_STATE = "cognitive_state"     # State Machine (Idle/Thinking/Speaking)
    PLUGIN_STATUS = "plugin_status"         # [Architecture 4.2] Real-time Plugin Lifecycle
    EMOTION_CHANGED = "emotion:changed"
    UI_REGISTER_WIDGET = "ui:register_widget"
    UI_REMOVE_WIDGET = "ui:remove_widget"

# --- The Unified Packet ---
class EventPacket(BaseModel):
    """
    Standard Data Unit for the Lumina Event Bus.
    Conforms to 'First Principles' architecture.
    """
    # 1. Transport Layer
    trace_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    session_id: int = Field(..., description="Global interaction version for interrupt logic")
    sequence_number: int = Field(0, description="Per-session sequence for deduplication")
    type: str = Field(..., description="EventType string")
    source: str = Field(..., description="Plugin Name or Component ID")
    
    # 2. Payload Layer (Flexible)
    # [Protocol Hardening] Enforce Dict for better serialization safety
    payload: Dict[str, Any] = Field(default_factory=dict)
    
    # 3. Governance Layer
    timestamp: float = Field(default_factory=time.time)
    
    # 4. Routing Hooks (Optional)
    # ttl: int = 10 
    # parent_id: Optional[str] = None
# --- 3. Payload Layer (Flexible) ---

class InputTextPayload(BaseModel):
    text: str
    user_id: Optional[str] = "default_user"
    character_id: Optional[str] = "default_char"
    user_name: Optional[str] = "User"
    char_name: Optional[str] = "Assistant"
    model: Optional[str] = None

class BrainResponsePayload(BaseModel):
    content: str

class BrainThinkingPayload(BaseModel):
    mode: str = "chat"
    text: Optional[str] = ""

class EmotionChangedPayload(BaseModel):
    emotion: str
    timestamp: float = Field(default_factory=time.time)

class SystemStatusPayload(BaseModel):
    status: str
    details: Optional[str] = ""

class PluginStatusPayload(BaseModel):
    plugin_id: str
    status: str
    details: Optional[str] = ""

# --- Protocol Schema Registry ---

# Map EventType to its expected Payload Model
CORE_SCHEMAS: Dict[str, Type[BaseModel]] = {
    EventType.INPUT_TEXT: InputTextPayload,
    EventType.BRAIN_RESPONSE: BrainResponsePayload,
    EventType.BRAIN_THINKING: BrainThinkingPayload,
    EventType.EMOTION_CHANGED: EmotionChangedPayload,
    EventType.SYSTEM_STATUS: SystemStatusPayload,
    EventType.PLUGIN_STATUS: PluginStatusPayload
}
