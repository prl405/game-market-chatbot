"""
Text-to-SQL fallback tool and schema introspection.

`run_sql_query` lets the LLM answer open-ended questions the predefined
query tools can't, while `_is_read_only` guards against write/DDL statements.
"""

from __future__ import annotations

import re
from typing import Any

from game_market_chatbot.tools.db_helpers import _get_conn, _rows_to_dicts

# Keywords that indicate a write or destructive operation.
# The check is case-insensitive and word-boundary aware.
_FORBIDDEN_KEYWORDS = (
    "INSERT", "UPDATE", "DELETE", "DROP", "CREATE", "ALTER",
    "REPLACE", "TRUNCATE", "ATTACH", "DETACH", "PRAGMA",
)


def _is_read_only(sql: str) -> bool:
    """
    Return True if the SQL is a read-only SELECT statement.

    Checks:
      1. The first non-whitespace token must be SELECT.
      2. None of the forbidden write/DDL keywords appear as whole words.
    """
    stripped = sql.strip()
    if not stripped.upper().startswith("SELECT"):
        return False

    upper = stripped.upper()
    for keyword in _FORBIDDEN_KEYWORDS:
        # Match the keyword as a whole word so e.g. "SELECTING" doesn't match
        # "SELECT", but "DROP" inside a comment still would — intentionally
        # conservative.
        if re.search(rf"\b{keyword}\b", upper):
            return False

    return True


def run_sql_query(
    sql: str,
    conn=None,
) -> list[dict[str, Any]]:
    """
    Execute a raw SELECT query and return up to 500 rows as a list of dicts.

    This is the text-to-SQL fallback tool — the LLM generates SQL for
    open-ended questions that predefined tools cannot answer.

    Args:
        sql:  A read-only SELECT statement. Must not contain INSERT, UPDATE,
              DELETE, DROP, CREATE, ALTER, REPLACE, TRUNCATE, ATTACH, DETACH,
              or PRAGMA.
        conn: Optional database connection (used in tests).

    Returns:
        List of dicts, one per row, keyed by column name. Capped at 500 rows.

    Raises:
        ValueError: If the SQL is not a read-only SELECT statement.

    JSON array columns reminder (for the LLM):
        genres, developers, and publishers are stored as JSON text, e.g.
        '["Action","RPG"]'. Use LIKE '%value%' to filter them — not equality.
    """
    if not _is_read_only(sql):
        raise ValueError(
            "Only read-only SELECT statements are permitted. "
            f"Received: {sql[:120]!r}"
        )

    # Enforce a row cap by injecting LIMIT if the query has none.
    _MAX_ROWS = 500
    upper = sql.strip().upper()
    if "LIMIT" not in upper:
        sql = sql.rstrip().rstrip(";") + f" LIMIT {_MAX_ROWS}"

    connection, should_close = _get_conn(conn)

    try:
        cursor = connection.cursor()
        cursor.execute(sql)
        return _rows_to_dicts(cursor)
    finally:
        if should_close:
            connection.close()


# Schema description string used in the system prompt and returned by
# get_schema_info(). Kept here so it stays in sync with schema.sql.
_SCHEMA_INFO = """
TABLE: steam_games
PRIMARY KEY: steam_id (INTEGER)

COLUMNS
-------
steam_id            INTEGER   Steam App ID — unique identifier for each game.
name                TEXT      Game title.
copies_sold         INTEGER   Estimated total units sold. May be NULL for unreleased games.
price               REAL      Current price in USD. 0.0 = free-to-play.
review_score        INTEGER   Steam review score 0–100. May be NULL.
publisher_class     TEXT      One of: 'AAA', 'AA', 'Indie', 'Hobbyist'.
unreleased          INTEGER   Boolean (0/1). 1 = game not yet released.
early_access        INTEGER   Boolean (0/1). 1 = currently in Early Access.
release_date        INTEGER   Unix timestamp in MILLISECONDS. Convert with:
                              strftime('%Y-%m-%d', release_date / 1000, 'unixepoch')
first_release_date  INTEGER   Unix timestamp in MILLISECONDS (first EA or full release).
ea_release_date     INTEGER   Unix timestamp in MILLISECONDS (Early Access exit date).
genres              TEXT      JSON array stored as text, e.g. '["Action","RPG"]'.
                              ALWAYS use LIKE for filtering: WHERE genres LIKE '%RPG%'
                              NEVER use equality: WHERE genres = 'RPG'  ← WRONG
developers          TEXT      JSON array stored as text, e.g. '["Valve"]'.
                              ALWAYS use LIKE for filtering.
publishers          TEXT      JSON array stored as text, e.g. '["Electronic Arts"]'.
                              ALWAYS use LIKE for filtering.
ingested_at         INTEGER   Unix timestamp in MILLISECONDS when row was last upserted.

INDEXES
-------
idx_steam_games_copies_sold    (copies_sold DESC)
idx_steam_games_review_score   (review_score DESC)
idx_steam_games_price          (price)
idx_steam_games_publisher_cls  (publisher_class)
idx_steam_games_release_date   (release_date DESC)

NOTES
-----
- Total rows: ~129,700 Steam games.
- Timestamp columns are in MILLISECONDS, not seconds. Divide by 1000 before
  passing to SQLite date functions.
- genres, developers, publishers are JSON text arrays — use LIKE for filtering,
  never equality operators.
- copies_sold and review_score can be NULL — always filter with IS NOT NULL
  in aggregations to avoid skewing results.
""".strip()


def get_schema_info() -> str:
    """
    Return a plain-text description of the steam_games table schema.

    This is injected into the LLM system prompt so the model understands
    the database structure before generating SQL queries. It includes:
      - Column names, types, and descriptions
      - Index definitions
      - Critical notes on JSON array columns and millisecond timestamps

    Returns:
        A multi-line string describing the schema. Not a database call —
        returns a static string that mirrors schema.sql.
    """
    return _SCHEMA_INFO
