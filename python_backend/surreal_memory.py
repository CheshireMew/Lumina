"""
SurrealMemory Compatibility Shim
================================
This file acts as a compatibility layer for the refactored memory system.
The actual implementation has been moved to the `memory` package.

- `memory.core.SurrealMemory`: The main facade class.
- `memory.vector_store.VectorStore`: Episodic memory and vector search.
- `memory.connection.DBConnection`: Shared database connection.

This shim ensures that `from surreal_memory import SurrealMemory` continues to work.
"""

import logging
from memory.core import SurrealMemory as SurrealMemoryRefactored

# Re-export the class with the same name
SurrealMemory = SurrealMemoryRefactored

# Configure legacy logger to point to new location or just exist
logging.getLogger("surreal_memory").setLevel(logging.INFO)
