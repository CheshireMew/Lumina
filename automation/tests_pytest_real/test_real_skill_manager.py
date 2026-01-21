"""
REAL integration test for SkillManager.
Tests tool registration and execution.
"""
import sys
import os
import pytest
import asyncio
from unittest.mock import MagicMock, AsyncMock
from pathlib import Path

# Add python_backend to path
PROJECT_ROOT = Path(__file__).parents[2]
sys.path.insert(0, str(PROJECT_ROOT / "python_backend"))

from services.skill_manager import SkillManager
from core.interfaces.tool import ToolProvider

class MockToolProvider(ToolProvider):
    @property
    def name(self) -> str: return "test_tool"
    async def execute(self, args: dict) -> str:
        return f"result_{args.get('val')}"
    def get_definition(self) -> dict:
        return {"name": "test_tool", "description": "test"}

@pytest.mark.asyncio
async def test_skill_manager_registration_and_execution():
    sm = SkillManager()
    provider = MockToolProvider()
    
    sm.register_tool(provider)
    
    assert sm.get_tool("test_tool") == provider
    assert len(sm.get_tool_definitions()) == 1
    
    result = await sm.execute_tool("test_tool", {"val": "hello"})
    assert result == "result_hello"

@pytest.mark.asyncio
async def test_skill_manager_tool_not_found():
    sm = SkillManager()
    result = await sm.execute_tool("non_existent", {})
    assert "not found" in result.lower()

@pytest.mark.asyncio
async def test_skill_manager_execution_failure():
    sm = SkillManager()
    mock_tool = MagicMock(spec=ToolProvider)
    mock_tool.name = "fail_tool"
    mock_tool.execute = AsyncMock(side_effect=ValueError("Boom"))
    
    sm.register_tool(mock_tool)
    result = await sm.execute_tool("fail_tool", {})
    assert "Error executing" in result
    assert "Boom" in result
