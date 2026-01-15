import asyncio
import logging
from core.events.bus import init_event_bus
from core.protocol import EventType, EventPacket
from services.chat_bridge import BasicChatBridge

# Configure Logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("TestChain")

async def test_llm_chain():
    logger.info("1. Initializing Event Bus...")
    bus = init_event_bus()

    logger.info("2. Starting BasicChatBridge...")
    bridge = BasicChatBridge()
    bridge.start()
    
    # Capture Responses
    responses = []
    
    async def capture_response(event):
        logger.info(f"📩 RECEIVED: {event.type} -> {event.data.payload}")
        if event.type == EventType.BRAIN_RESPONSE:
            responses.append(event.data.payload.get("content", ""))
    
    bus.subscribe(EventType.BRAIN_RESPONSE, capture_response)
    bus.subscribe(EventType.BRAIN_THINKING, capture_response)
    bus.subscribe("brain_response_end", capture_response)
    
    logger.info("3. Emitting 'input_text'...")
    packet = EventPacket(
        session_id=0,
        type=EventType.INPUT_TEXT,
        source="test_script",
        payload={"text": "Hello, are you working?", "user_id": "test", "character_id": "test"}
    )
    
    await bus.emit(EventType.INPUT_TEXT, packet)
    
    # Wait for processing
    logger.info("4. Waiting for response...")
    await asyncio.sleep(10) # Give it time
    
    if responses:
        logger.info(f"✅ SUCCESS. Response content: {''.join(responses)}")
    else:
        logger.error("❌ FAILURE. No response received.")

if __name__ == "__main__":
    asyncio.run(test_llm_chain())
