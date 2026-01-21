"""
REAL pytest tests for SoulService - Testing actual soul/character system
"""
import sys
from pathlib import Path
import pytest
from unittest.mock import MagicMock, AsyncMock, patch
import asyncio

# Add python_backend to path
PROJECT_ROOT = Path(__file__).parents[2]
sys.path.insert(0, str(PROJECT_ROOT / "python_backend"))

from services.soul_service import SoulService

@pytest.fixture
def soul_service():
    return SoulService()

@pytest.mark.asyncio
async def test_soul_service_initialization(soul_service):
    assert soul_service is not None
    assert soul_service._active_character_id == "hiyori"

@pytest.mark.asyncio
async def test_character_switching(soul_service):
    # Mock characters_root check
    with patch.object(Path, "exists", return_value=True):
         with patch.object(Path, "mkdir"):
             soul_service.set_active_character("sakura")
             assert soul_service._active_character_id == "sakura"

@pytest.mark.asyncio
async def test_soul_persistence_interaction(soul_service):
    # Mock persistence
    soul_service._persistence = MagicMock()
    soul_service._persistence.load_module_data.return_value = {"test": "data"}
    
    data = soul_service.load_module_data("test_module")
    assert data == {"test": "data"}
    
    soul_service.save_module_data("test_module", {"new": "data"})
    soul_service._persistence.save_module_data.assert_called_once()
