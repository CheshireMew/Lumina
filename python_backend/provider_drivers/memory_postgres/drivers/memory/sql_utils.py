import re

from core.db.query_builder import SecurityException

_IDENTIFIER_RE = re.compile(r"^[A-Za-z0-9_]+$")
_ORDER_BY_RE = re.compile(r"^[A-Za-z0-9_ ]+(?:\s+(?:ASC|DESC))?$", re.IGNORECASE)


def sanitize_identifier(value: str, kind: str = "identifier") -> str:
    if not _IDENTIFIER_RE.fullmatch(value):
        raise SecurityException(f"Invalid {kind}: {value}")
    return value


def sanitize_table_name(table_name: str) -> str:
    return sanitize_identifier(table_name, "table name")


def sanitize_column_name(column_name: str) -> str:
    return sanitize_identifier(column_name, "column name")


def sanitize_order_by(order_by: str) -> str:
    if not _ORDER_BY_RE.fullmatch(order_by):
        return "created_at DESC"
    return order_by
