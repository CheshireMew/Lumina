
import logging
from typing import Dict, Any, List, Optional
from core.interfaces.tool import ToolProvider

logger = logging.getLogger("SkillManager")

class SkillManager:
    """
    Decentralized Tool/Skill Registry.
    Phase 16 Framework.
    
    Responsibilities:
    1. Hold the registry of available Tools (from plugins).
    2. Provide tool definitions to LLM.
    3. Route tool execution requests to the correct provider.
    """
    
    def __init__(self):
        self._tools: Dict[str, ToolProvider] = {}
        
    def register_tool(self, provider: ToolProvider):
        """Register a tool provider."""
        if provider.name in self._tools:
            logger.warning(f"Overwriting existing tool: {provider.name}")
        
        self._tools[provider.name] = provider
        logger.info(f"馃洔 Skill Registered: {provider.name}")

    def get_tool(self, name: str) -> Optional[ToolProvider]:
        return self._tools.get(name)

    def get_all_tools(self) -> List[ToolProvider]:
        return list(self._tools.values())

    def get_tool_definitions(self) -> List[Dict[str, Any]]:
        """Return OpenAI-compatible definitions for all registered tools."""
        return [t.get_definition() for t in self._tools.values()]

    async def execute_tool(self, name: str, args: Dict[str, Any]) -> str:
        """Execute a managed tool."""
        tool = self.get_tool(name)
        if not tool:
            return f"Error: Tool '{name}' not found."
            
        try:
            return await tool.execute(args)
        except Exception as e:
            logger.error(f"Tool execution failed ({name}): {e}")
            return f"Error executing {name}: {str(e)}"
