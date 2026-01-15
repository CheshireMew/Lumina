
import asyncio
import logging
import sys
import os
from unittest.mock import MagicMock, AsyncMock
from datetime import datetime

# Add python path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "python_backend"))

from core.events.bus import EventBus
from plugins.system.evolution.manager import EvolutionManager

# Mock classes
class MockDB:
    async def query(self, query, params=None):
        print(f"💾 [DB Query] {query.strip().splitlines()[0]}... Params: {params}")
        if "episodic_memory" in query:
             return [{"result": [{"content": "User said hi", "created_at": "yesterday"}, {"content": "User asked for help", "created_at": "yesterday"}]}]
        if "conversation_log" in query:
             return [{"result": [{"role": "user", "content": "Hello AI"}, {"role": "assistant", "content": "Hi there"}]}]
        return []
        
    async def create(self, table, data):
        print(f"💾 [DB Create] {table}: {data}")
        return "id:123"

class MockMemory:
    async def connect(self):
        return MockDB()
    
    async def create(self, table, data):
        print(f"💾 [Driver Create] {table}: {data}")

class MockLLMDriver:
    async def chat_completion(self, messages, model, **kwargs):
        print(f"🤖 [LLM] Generating response for model {model}...")
        # Return summary or JSON for evolution
        last_msg = messages[-1]['content']
        if "Summarize" in last_msg:
            return "User greeted the AI and asked for help. AI responded friendly."
        if "evolve" in str(messages) or "json" in str(kwargs):
            return '```json\n{"new_traits": ["Evolved"], "current_mood": "Happy"}\n```'
        return "{}"

class MockLLMManager:
    async def get_driver(self, name):
        return MockLLMDriver()
    
    def get_model_name(self, name):
        return "mock-model"
        
    def get_parameters(self, name):
        return {}

class MockSoul:
    def __init__(self):
        self.character_id = "char_001"
        self.profile = {"personality": {}, "state": {}}
        
    def _load_soul(self):
        return {}
        
    def update_traits(self, traits):
        print(f"✨ [Soul] Traits updated: {traits}")
        
    def update_current_mood(self, mood):
        print(f"✨ [Soul] Mood updated: {mood}")

class MockContext:
    def __init__(self):
        self.bus = EventBus()
        self.memory = MockMemory()
        self.llm_manager = MockLLMManager()
        self.soul = MockSoul()
        self.container = MagicMock() # For legacy checks
    
    def register_service(self, name, instance):
        print(f"🔌 Service Registered: {name}")
        
    def load_data(self, id):
        return {"enabled": True, "auto_evolve": True, "scheduled_hour": 4}
        
    def save_data(self, id, data):
        pass

async def test_evolution():
    print("⏳ Starting Evolution Test...")
    
    # 1. Init Manager
    context = MockContext()
    manager = EvolutionManager()
    
    # Initialize Plugin
    try:
        if asyncio.iscoroutinefunction(manager.initialize):
            await manager.initialize(context)
        else:
            manager.initialize(context)
    except TypeError:
        # Fallback if signature mismatch in mock
        await manager.initialize(context)

    # 2. Simulate 4:00 AM Tick
    print("\n⏰ Simulating 04:00 AM Tick...")
    params = {"timestamp": datetime(2025, 1, 1, 4, 0, 0).isoformat()}
    
    # Verify via EventBus emission
    # Note: EventBus emits are fire-and-forget in some modes, or we await them.
    # Manager subscribed via `context.bus.subscribe`.
    
    await context.bus.emit("system.tick.minute", params)
    
    # Wait for async tasks if any
    await asyncio.sleep(0.5)

    print("\n✅ Test Complete. Check logs above for DB Create (Summary) and Soul Updates.")

if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    asyncio.run(test_evolution())
