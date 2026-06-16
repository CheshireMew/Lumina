from typing import Any, Dict, Optional, Type
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
    BRAIN_THINKING = "brain_thinking"  # "Let me think..."
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
    SYSTEM_READY = "system.ready"           # System startup complete
    SYSTEM_SHUTDOWN = "system.shutdown"     # Graceful shutdown
    SYSTEM_TICK = "system.tick"             # Global ticker
    SYSTEM_TICK_MINUTE = "system.tick.minute"
    SYSTEM_CONFIG_RELOADED = "system.config_reloaded"
    COGNITIVE_STATE = "cognitive_state"     # State Machine (Idle/Thinking/Speaking)
    
    # Plugin Lifecycle (Source: PluginManager)
    PLUGIN_STATUS = "plugin_status"         # [Architecture 4.2] Real-time Plugin Lifecycle
    PLUGIN_LOADED = "plugin.loaded"
    PLUGIN_UNLOADED = "plugin.unloaded"
    PLUGIN_STATE_LOCAL = "plugin.state.local"
    PLUGIN_STATE_WORKER = "plugin.state.worker"
    
    # Emotion/Avatar
    EMOTION_CHANGED = "emotion:changed"
    AVATAR_EMOTION = "avatar.emotion"
    
    # UI Events
    UI_REGISTER_WIDGET = "ui:register_widget"
    UI_REMOVE_WIDGET = "ui:remove_widget"
    UI_NOTIFICATION = "ui.notification"
    UI_TOAST = "ui.toast"
    UI_DIALOG = "ui.dialog"
    
    # Service Registration
    SERVICE_REGISTERED = "service.registered"
    SERVICE_UNREGISTERED = "service.unregistered"

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
    character_id: Optional[str] = "hiyori"
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
