"""
Factory fixtures for creating test data

These factories provide a clean way to create test data objects
with sensible defaults and easy customization.
"""
import random
from datetime import datetime, timedelta
from typing import Dict, List, Optional
from unittest.mock import MagicMock


class ChatMessageFactory:
    """Factory for creating chat message test data"""

    @staticmethod
    def create(
        role: str = "user",
        content: str = None,
        timestamp: datetime = None,
        metadata: Dict = None
    ) -> Dict:
        """Create a chat message"""
        if content is None:
            content = "Test message"
        if timestamp is None:
            timestamp = datetime.now()
        if metadata is None:
            metadata = {}

        return {
            "role": role,
            "content": content,
            "timestamp": timestamp.isoformat(),
            "metadata": metadata
        }

    @staticmethod
    def create_conversation(count: int = 5) -> List[Dict]:
        """Create a conversation with multiple messages"""
        messages = []
        roles = ["user", "assistant"]
        for i in range(count):
            messages.append(ChatMessageFactory.create(
                role=roles[i % 2],
                content=f"Message {i + 1}"
            ))
        return messages


class MemoryFactory:
    """Factory for creating memory test data"""

    @staticmethod
    def create(
        content: str = None,
        embedding_dim: int = 512,
        metadata: Dict = None,
        importance: float = None
    ) -> Dict:
        """Create a memory record"""
        if content is None:
            content = "Test memory content"
        if metadata is None:
            metadata = {"source": "test"}
        if importance is None:
            importance = random.random()

        return {
            "id": f"mem_{random.randint(1000, 9999)}",
            "content": content,
            "embedding": [random.uniform(-1, 1) for _ in range(embedding_dim)],
            "metadata": metadata,
            "importance": importance,
            "created_at": datetime.now().isoformat(),
            "access_count": random.randint(0, 100)
        }

    @staticmethod
    def create_batch(count: int = 10) -> List[Dict]:
        """Create multiple memory records"""
        return [MemoryFactory.create() for _ in range(count)]


class CapabilityModuleFactory:
    """Factory for creating capability module test data"""

    @staticmethod
    def create_manifest(
        module_id: str = "test.capability",
        version: str = "1.0.0",
    ) -> Dict:
        """Create a capability manifest"""
        return {
            "id": module_id,
            "name": "Test Capability",
            "version": version,
            "description": "A test capability module",
            "author": "Test Author",
            "entry_point": "module.py",
            "min_lumina_version": "0.1.0"
        }

    @staticmethod
    def create_capability(
        capability_id: str = "test.capability",
        capability_type: str = "stt",
        name: str = "Test Capability"
    ) -> Dict:
        """Create a runtime capability"""
        return {
            "id": capability_id,
            "type": capability_type,
            "name": name,
            "description": "A test capability",
            "config": {}
        }


class SoulProfileFactory:
    """Factory for creating soul profile test data"""

    @staticmethod
    def create(
        energy_level: int = 100,
        relationship_level: int = 0,
        mood: str = "neutral"
    ) -> Dict:
        """Create a soul profile"""
        return {
            "personality": {
                "pad_model": {
                    "openness": 0.5,
                    "conscientiousness": 0.5,
                    "extraversion": 0.5,
                    "agreeableness": 0.5,
                    "neuroticism": 0.5
                }
            },
            "state": {
                "energy_level": energy_level,
                "mood": mood,
                "last_interaction": datetime.now().isoformat()
            },
            "relationship": {
                "level": relationship_level,
                "trust": 0.5,
                "affection": 0.5
            }
        }


class LLMResponseFactory:
    """Factory for creating LLM response test data"""

    @staticmethod
    def create_stream_response(text: str = "Hello, world!") -> List[str]:
        """Create a streaming response as chunks"""
        words = text.split()
        return words

    @staticmethod
    def create_completion(
        content: str = "Test response",
        finish_reason: str = "stop",
        tokens_used: int = 50
    ) -> Dict:
        """Create a completion response"""
        return {
            "content": content,
            "finish_reason": finish_reason,
            "usage": {
                "prompt_tokens": 20,
                "completion_tokens": tokens_used,
                "total_tokens": 20 + tokens_used
            }
        }


# ============================================================================
# Pytest Factory Fixtures
# ============================================================================

import pytest


@pytest.fixture
def chat_message_factory():
    """Provide ChatMessageFactory"""
    return ChatMessageFactory


@pytest.fixture
def memory_factory():
    """Provide MemoryFactory"""
    return MemoryFactory


@pytest.fixture
def capability_module_factory():
    """Provide CapabilityModuleFactory"""
    return CapabilityModuleFactory


@pytest.fixture
def soul_profile_factory():
    """Provide SoulProfileFactory"""
    return SoulProfileFactory


@pytest.fixture
def llm_response_factory():
    """Provide LLMResponseFactory"""
    return LLMResponseFactory
