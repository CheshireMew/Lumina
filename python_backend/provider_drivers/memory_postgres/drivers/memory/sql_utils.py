"""Compatibility imports for the former Postgres-local validators."""

from core.db.sql_identifiers import (
    sanitize_column_name,
    sanitize_identifier,
    sanitize_order_by,
    sanitize_table_name,
)

__all__ = [
    "sanitize_column_name",
    "sanitize_identifier",
    "sanitize_order_by",
    "sanitize_table_name",
]
