from plugins.base import BaseSystemPlugin
# Removed: from services.container import services (use EventBus instead)
from core.protocol import EventPacket, EventType
from .state import CognitiveContext, PersonaSpec, SessionState
from .logic.loop import CognitiveLoop
import logging

logger = logging.getLogger("CognitivePlugin")

class CognitivePlugin(BaseSystemPlugin):
    @property
    def id(self) -> str:
        return "system.cognitive"

    @property
    def name(self) -> str:
        return "Cognitive Brain"

    @property
    def description(self) -> str:
        return "Core reasoning engine (System 2) for complex task management and logic."



    def initialize(self, context):
        super().initialize(context) # Standard Phase 30 init
        logger.info("馃 Cognitive Brain Plugin Initializing...")
        
        # Access EventBus via Context
        # Note: LuminaContext exposes .bus (shortcut) or .container.event_bus
        bus = getattr(self.context, 'bus', None) or getattr(self.context.container, 'event_bus', None)
        
        if bus:
            # [Fix] Disabled to prevent double-processing with Core ChatBridge
            # bus.subscribe(EventType.INPUT_TEXT, self.handle_input_text)
            
            # Register as service for direct access
            # Create a persistent loop instance
            self._loop = CognitiveLoop(CognitiveContext(
                persona=PersonaSpec(name="Lumina", description="AI", tone="friendly"),
                state=SessionState(session_id=0)  # Will be updated per-request
            ))
            bus.register_service("cognitive_loop", self._loop)
            logger.info("鉁?Cognitive Loop registered as service")
        else:
            logger.error("鉂?EventBus not found in context!")

    async def handle_input_text(self, event):
        """
        Intercepts user text input.
        EventBus passes an Event object. event.data is the EventPacket.
        """
        # Unwrap
        packet = event.data
        if not hasattr(packet, "payload"):
            # Fallback for dict?
            logger.warning(f"CognitivePlugin received invalid packet data: {type(packet)}")
            return

        # Check if enabled in config
        if not self.config.get("enabled", True): # Default True!
            return 
            
        logger.info(f"馃 Brain picked up input: {packet.payload.get('text', '')[:20]}...")
        
        # Setup ephemeral context (Loop handles persistence loading)
        context = CognitiveContext(
            persona=PersonaSpec(name="Lumina", description="AI", tone="friendly"),
            state=SessionState(session_id=packet.session_id)
        )
        
        loop = CognitiveLoop(context)
        await loop.process_input(packet)

