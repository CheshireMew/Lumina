from typing import Any, Optional
from core.interfaces.context import ContextProvider
from .manager import GalgameManager

class GalgameContextProvider(ContextProvider):
    """
    Injects Game State (Energy, Relationship, etc.) into the context.
    """
    def __init__(self, manager: GalgameManager):
        self.manager = manager

    async def provide(self, ctx: Any) -> Optional[str]:
        if not self.manager.enabled:
            return None
            
        data = self.manager.load_data()
        
        # Energy
        energy = data.get("energy_level", 100)
        energy_desc = "High"
        if energy < 30: energy_desc = "Low - You are tired."
        elif energy < 60: energy_desc = "Medium"
        
        # Relationship
        rel = data.get("relationship", {})
        stage = rel.get("current_stage_label", "Stranger")
        
        return f"""## current_condition
Energy: {energy}% ({energy_desc})
Relationship: {stage}
"""
