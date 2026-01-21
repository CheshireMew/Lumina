"""
REAL integration test for MemoryService.
Tests memory lifecycle and component delegation.
"""
import sys
import os
import pytest
import asyncio
from unittest.mock import MagicMock, AsyncMock, patch
from pathlib import Path

# Add python_backend to path
PROJECT_ROOT = Path(__file__).parents[2]
sys.path.insert(0, str(PROJECT_ROOT / "python_backend"))

from memory.core import MemoryService

@pytest.fixture
def memory_service():
    with patch("memory.factory.MemoryDriverFactory.create_driver") as mock_factory:
        mock_driver = MagicMock()
        mock_driver.connect = AsyncMock()
        mock_driver.initialize_schema = AsyncMock()
        mock_factory.return_value = mock_driver
        
        svc = MemoryService(character_id="test_char")
        return svc, mock_driver

@pytest.mark.asyncio
async def test_memory_service_init(memory_service):
    svc, _ = memory_service
    assert svc.character_id == "test_char"
    assert svc.driver is not None
    assert svc.vector_store is not None

@pytest.mark.asyncio
async def test_memory_service_connect(memory_service):
    svc, mock_driver = memory_service
    
    await svc.connect()
    
    mock_driver.connect.assert_called_once()
    mock_driver.initialize_schema.assert_called_once()
    assert svc._worker_thread is not None
    assert svc._worker_thread.is_alive()

@pytest.mark.asyncio
async def test_log_conversation_delegation(memory_service):
    svc, mock_driver = memory_service
    mock_driver.create = AsyncMock(return_value="msg_123")
    
    # Mock encoder to avoid actual embeddings
    svc.encoder = None
    
    result = await svc.log_conversation("test_char", "hello world")
    
    assert result == "msg_123"
    mock_driver.create.assert_called_once()
    args, _ = mock_driver.create.call_args
    assert args[0] == "conversation_log"
    assert args[1]["narrative"] == "hello world"

@pytest.mark.asyncio
async def test_retrieve_context_flow(memory_service):
    svc, _ = memory_service
    
    # Mock encoder and search_hybrid
    mock_encoder = MagicMock(return_value=[0.1, 0.2])
    svc.set_encoder(mock_encoder)
    
    svc.search_hybrid = AsyncMock(return_value=[{"content": "memory 1"}, {"content": "memory 2"}])
    
    context = await svc.retrieve_context("query test", character_id="test_char")
    
    assert "memory 1" in context
    assert "memory 2" in context
    svc.search_hybrid.assert_called_once()
