from abc import ABC, abstractmethod
from typing import Any, Dict, Optional, Tuple


class SecurityException(Exception):
    """Raised when query construction violates security rules."""


class QueryBuilder(ABC):
    """
    Abstract base class for safe database query construction.
    """

    @abstractmethod
    def sanitize_table(self, table_name: str) -> str:
        """Validate table name to prevent injection."""
        pass

    @abstractmethod
    def select(
        self,
        table: str,
        where: Optional[Dict[str, Any]] = None,
        limit: int = 50,
        order_by: str = "created_at DESC",
    ) -> Tuple[str, Dict[str, Any]]:
        """
        Build a SELECT query and its bound parameters.
        """
        pass

    @abstractmethod
    def delete(self, table: str, record_id: str) -> Tuple[str, Dict[str, Any]]:
        """
        Build a DELETE query and its bound parameters.
        """
        pass
