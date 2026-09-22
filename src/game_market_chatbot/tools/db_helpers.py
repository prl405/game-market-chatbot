"""
Internal database helpers shared by the query modules.

All functions accept an optional `conn` parameter. When omitted the live
database connection from `db.client.get_connection()` is used. Passing an
explicit connection (e.g. an in-memory turso connection) makes the query
functions fully testable without touching the real database.
"""

from __future__ import annotations

import json
from typing import Any


def _get_conn(conn=None):
    """Return conn if provided, otherwise open a live database connection."""
    if conn is not None:
        return conn, False          # caller owns it — don't close
    from game_market_chatbot.db.client import get_connection
    return get_connection(), True   # we opened it — we close it


def _rows_to_dicts(cursor) -> list[dict[str, Any]]:
    """Convert cursor rows to a list of dicts using column names."""
    cols = [d[0] for d in cursor.description]
    return [dict(zip(cols, row)) for row in cursor.fetchall()]


def _parse_json_field(value: str | None) -> list:
    """Safely parse a JSON-encoded list column back to a Python list."""
    if value is None:
        return []
    try:
        return json.loads(value)
    except (json.JSONDecodeError, TypeError):
        return []
