
import logging
from typing import Optional
from services.infra.surreal_client import SurrealSystem  # Assuming this exists or Logic is in routers

logger = logging.getLogger("MemoryManager")

class MemoryPluginManager:
    """
    Manages Memory Backend (SurrealDB, Vector Store).
    Wraps the SurrealSystem logic.
    """
    def __init__(self):
        self.surreal: Optional[SurrealSystem] = None
        self.status = "initializing"

    async def initialize(self):
        """Initialize connection to SurrealDB / Vector DB"""
        self.status = "connecting"
        try:
            # Reusing existing Logic from services.infra or wherever it lived
            # Previously in routers/memory.py, it used _get_surreal() -> services.get_memory()
            # services.get_memory() -> SurrealSystem instance.
            # We need to instantiate SurrealSystem here.
            
            # Check availability of SurrealSystem class
            # It seems it was in 'services.infra.surreal_client' (inferred) specific path check needed?
            # User earlier saw 'routers/memory.py' imports _get_surreal.
            
            # Let's import it safely
            from services.infra.surreal_client import SurrealSystem
            
            self.surreal = SurrealSystem()
            await self.surreal.initialize()
            
            self.status = "ready"
            logger.info("Memory Manager Ready (SurrealDB Connected)")
            
        except ImportError:
            logger.error("Could not import SurrealSystem. Is the file path correct?")
            self.status = "error"
        except Exception as e:
            logger.error(f"Memory Manager Initialization Failed: {e}")
            self.status = "error"

    async def shutdown(self):
        if self.surreal:
            # Assuming close method exists
            if hasattr(self.surreal, 'close'):
                await self.surreal.close()
            elif hasattr(self.surreal, 'client') and hasattr(self.surreal.client, 'close'):
                await self.surreal.client.close()

    # Proxy methods for Routes
    async def log_conversation(self, *args, **kwargs):
        if not self.surreal: raise RuntimeError("Memory Not Ready")
        return await self.surreal.log_conversation(*args, **kwargs)

    async def search(self, *args, **kwargs):
        if not self.surreal: raise RuntimeError("Memory Not Ready")
        return await self.surreal.search(*args, **kwargs)
        
    async def search_hybrid(self, *args, **kwargs):
        if not self.surreal: raise RuntimeError("Memory Not Ready")
        return await self.surreal.search_hybrid(*args, **kwargs)

    async def query(self, *args, **kwargs):
        if not self.surreal: raise RuntimeError("Memory Not Ready")
        return await self.surreal.query(*args, **kwargs)
