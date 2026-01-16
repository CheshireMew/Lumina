
import asyncio
import logging
import sys
import os

# Setup path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "python_backend")))

from core.events.bus import get_event_bus
from core.protocol import EventType, EventPacket
from services.chat_bridge import BasicChatBridge
from services.unified_chat import unified_chat

# Mock unified_chat.process
original_process = unified_chat.process
call_count = 0
last_model = None

async def mock_process(*args, **kwargs):
    global call_count, last_model
    call_count += 1
    last_model = kwargs.get("model")
    print(f"TEST: unified_chat.process called! Model: {last_model}")
    yield "mock_token"

unified_chat.process = mock_process

async def run_test():
    print("--- Test Start ---")
    
    # Init Bus & Bridge
    bus = get_event_bus()
    bridge = BasicChatBridge()
    bridge.start()
    
    # Simulate INPUT_TEXT
    payload = {
        "text": "Hello Test",
        "user_id": "test_user",
        "character_id": "test_char",
        "model": "mixtral-8x7b"
    }
    
    packet = EventPacket(
        session_id=1,
        type=EventType.INPUT_TEXT,
        source="test",
        payload=payload
    )
    
    print("TEST: Emitting INPUT_TEXT...")
    await bus.emit(EventType.INPUT_TEXT, packet)
    
    # Allow async processing
    await asyncio.sleep(1)
    
    print(f"--- Results ---")
    print(f"Call Count: {call_count}")
    print(f"Last Model: {last_model}")
    
    if call_count == 1 and last_model == "mixtral-8x7b":
        print("✅ SUCCESS: Single call with correct model.")
    elif call_count > 1:
        print("❌ FAILURE: Multiple calls detected.")
    else:
        print("❌ FAILURE: No call or wrong model.")

if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    asyncio.run(run_test())
