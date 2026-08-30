"""Compatibility name for the canonical memory driver contract."""

from core.interfaces.driver import BaseMemoryDriver

VectorDBInterface = BaseMemoryDriver

__all__ = ["VectorDBInterface"]
