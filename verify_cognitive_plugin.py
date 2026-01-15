
import asyncio
import logging
import sys
import os
import builtins
from unittest.mock import MagicMock

# Add python path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "python_backend"))

from core.protocol import EventPacket, EventType
from core.events.bus import EventBus
from services.container import services as service_instance
print(f"DEBUG: service_instance type is {type(service_instance)}")

# 1. Setup Mock Services
class MockGateway:
    async def emit(self, packet):
        print(f"📡 [GATEWAY] {packet.type} | {packet.payload}")

class MockContext:
    event_bus = EventBus()

service_instance.gateway = MockGateway()
reversed_services = MagicMock() # Plugin expects container
reversed_services.event_bus = service_instance.gateway # Simple mock for plugin.container.event_bus

# Mock Unified Chat
class MockUnifiedChat:
    async def process(self, *args, **kwargs):
        yield "Unified Response"

import services.unified_chat
services.unified_chat.unified_chat = MockUnifiedChat()


# 2. Import Plugin
from plugins.system.cognitive.plugin import CognitivePlugin

async def test_plugin():
    print("🧠 Initializing Plugin Test...")
    
    # Init Plugin (No Args)
    plugin = CognitivePlugin()
    
    # Prepare Context with EventBus
    class MockLuminaContext:
        def __init__(self, services):
            self.bus = services.event_bus
            self.container = services
        
        def load_data(self, plugin_id):
            return {"enabled": True} # Mock config
            
    context = MockLuminaContext(service_instance)
    
    # Initialize
    await plugin.initialize(context)
    
    # Verify enabled
    if not plugin.config.get("enabled"):
        print("❌ Plugin not enabled!")
        return
        
    print(f"✅ Plugin Initialized. Enabled: {plugin.enabled}")

    # 3. Simulate Input Event
    print("\n--- Test 1: Chat Input 'Hello' (Should go to Fast Path inside Loop) ---")
    packet = EventPacket(session_id=1, type=EventType.INPUT_TEXT, source="user", payload={"text": "Hello"})
    
    # Manually invoke handler since we are unit testing the handler logic
    await plugin.handle_input_text(packet)

    # 4. Simulate Task Input
    print("\n--- Test 2: Task Input 'Calculate 1+1' ---")
    packet_task = EventPacket(session_id=2, type=EventType.INPUT_TEXT, source="user", payload={"text": "Calculate 1+1"})
    await plugin.handle_input_text(packet_task)

if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    asyncio.run(test_plugin())
