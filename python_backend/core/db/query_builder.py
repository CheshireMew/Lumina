from abc import ABC, abstractmethod
from typing import Any, Dict, List, Optional, Tuple, Union
import re

class SecurityException(Exception):
    """Raised when query construction violates security rules."""
    pass

class QueryBuilder(ABC):
    """
    Abstract Base Class for Database Query Construction.
    Decouples business logic from specific SQL/NoSQL dialects.
    """
    
    @abstractmethod
    def sanitize_table(self, table_name: str) -> str:
        """Validate table name to prevent injection."""
        pass

    @abstractmethod
    def select(self, table: str, where: Optional[Dict[str, Any]] = None, limit: int = 50, order_by: str = "created_at DESC") -> Tuple[str, Dict[str, Any]]:
        """
        Builds a SELECT query.
        Returns: (query_string, parameters_dict)
        """
        pass

    @abstractmethod
    def delete(self, table: str, record_id: str) -> Tuple[str, Dict[str, Any]]:
        """
        Builds a DELETE query.
        Returns: (query_string, parameters_dict)
        """
        pass

class SurrealQueryBuilder(QueryBuilder):
    """
    SurrealDB Implementation of QueryBuilder.
    Constructs SurrealQL with parameterized placeholders ($param).
    """

    def sanitize_table(self, table_name: str) -> str:
        # Strict Alphanumeric + Underscore check
        if not re.match(r'^[a-zA-Z0-9_]+$', table_name):
            raise SecurityException(f"Invalid table name: {table_name}")
        return table_name

    def select(self, table: str, where: Optional[Dict[str, Any]] = None, limit: int = 50, order_by: str = "created_at DESC") -> Tuple[str, Dict[str, Any]]:
        table = self.sanitize_table(table)
        
        # Base Query
        # type::table($tb) is a safer way if supported, but strict table validation allows direct interpolation safely (and sometimes driver behaves better)
        # We will use direct interpolation for Table Name because we validated it strictly above.
        # Parameters usage for values is key.
        
        query = f"SELECT * FROM {table}"
        params = {}
        
        # Conditions
        conditions = []
        if where:
            for i, (key, value) in enumerate(where.items()):
                # Strict key validation (column name)
                if not re.match(r'^[a-zA-Z0-9_]+$', key):
                    raise SecurityException(f"Invalid column name: {key}")
                
                param_name = f"p_{i}" # p_0, p_1...
                conditions.append(f"{key} = ${param_name}")
                params[param_name] = value
        
        if conditions:
            query += " WHERE " + " AND ".join(conditions)
            
        # Limit & Order
        # Validate order_by roughly (prevent 'DROP TABLE' injection via order string)
        if not re.match(r'^[a-zA-Z0-9_ ]+(DESC|ASC)?$', order_by, re.IGNORECASE):
             order_by = "created_at DESC" # Fallback
             
        query += f" ORDER BY {order_by} LIMIT $limit;"
        params["limit"] = min(limit, 100) # Enforce max limit
        
        return query, params

    def delete(self, table: str, record_id: str) -> Tuple[str, Dict[str, Any]]:
        table = self.sanitize_table(table)
        
        # Verify ID format (table:id) or simple id
        # In Surreal, DELETE can take a record ID directly: DELETE type::thing('person', 'tobie');
        # Or DELETE person:tobie;
        
        # We will construct: DELETE type::thing($tb, $id);
        # Wait, type::thing needs two args.
        
        # If record_id is "table:id", we split it.
        if ":" in record_id:
            record_id = record_id.split(":", 1)[1]
            
        query = f"DELETE type::thing($tb, $id);"
        params = {"tb": table, "id": record_id}
        
        return query, params

    def create(self, table: str, data: Dict[str, Any]) -> Tuple[str, Dict[str, Any]]:
        # For create, we usually use the driver's .create() method directly which handles JSON.
        # But if we need raw query: CREATE type::table($tb) CONTENT $data;
        table = self.sanitize_table(table)
        query = f"CREATE type::table($tb) CONTENT $data;"
        params = {"tb": table, "data": data}
        return query, params

    def update(self, table: str, record_id: str, data: Dict[str, Any]) -> Tuple[str, Dict[str, Any]]:
        # UPDATE type::thing($tb, $id) MERGE $data;
        table = self.sanitize_table(table)
        if ":" in record_id:
            record_id = record_id.split(":", 1)[1]
            
        query = f"UPDATE type::thing($tb, $id) MERGE $data;"
        params = {"tb": table, "id": record_id, "data": data}
        return query, params
