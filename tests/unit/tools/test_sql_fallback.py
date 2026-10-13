"""
Unit tests for tools.sql_fallback: read-only validation, row limits, and
result shaping.

Validation and shaping run against the shared seeded in-memory database
(see tests/conftest.py). Row-cap boundaries use a small fake connection so
they don't need 1000+ seeded rows.
"""

from __future__ import annotations

import pytest

from game_market_chatbot.tools.sql_fallback import (
    _is_read_only,
    get_schema_info,
    run_sql_query,
)


class _FakeCursor:
    def __init__(self, row_count: int, executed: list[str]):
        self.description = [("value",)]
        self._row_count = row_count
        self._executed = executed

    def execute(self, sql):
        self._executed.append(sql)

    def fetchmany(self, size):
        return [(value,) for value in range(min(size, self._row_count))]


class _FakeConnection:
    """Connection whose cursor returns `row_count` rows and records the SQL."""

    def __init__(self, row_count: int = 0):
        self.executed: list[str] = []
        self._row_count = row_count

    def cursor(self):
        return _FakeCursor(self._row_count, self.executed)


# ---------------------------------------------------------------------------
# Validation
# ---------------------------------------------------------------------------

@pytest.mark.parametrize(
    "sql",
    [
        "SELECT * FROM steam_games",
        "select name from steam_games",
        "  \n SELECT name FROM steam_games WHERE price > 10;",
        "SELECT genres FROM steam_games WHERE genres LIKE '%RPG%'",
    ],
)
def test_is_read_only_accepts_select_statements(sql):
    assert _is_read_only(sql) is True


@pytest.mark.parametrize(
    "sql",
    [
        "INSERT INTO steam_games (steam_id, name) VALUES (1, 'x')",
        "UPDATE steam_games SET price = 0",
        "DELETE FROM steam_games",
        "DROP TABLE steam_games",
        "PRAGMA table_info(steam_games)",
        "WITH t AS (SELECT 1) SELECT * FROM t",
        "",
        "SELECT 1; DROP TABLE steam_games",
        "SELECT * FROM steam_games; delete from steam_games",
        "SELECT * FROM (SELECT 1) WHERE 1 = 1 OR ATTACH",
    ],
)
def test_is_read_only_rejects_writes_and_non_select(sql):
    assert _is_read_only(sql) is False


def test_is_read_only_matches_whole_words_only():
    # Column names that merely contain a forbidden keyword are allowed.
    assert _is_read_only("SELECT updated_at, created_by FROM steam_games") is True


def test_run_sql_query_rejects_write_without_touching_connection():
    conn = _FakeConnection()

    with pytest.raises(ValueError, match="Only read-only SELECT"):
        run_sql_query("DELETE FROM steam_games", conn=conn)

    assert conn.executed == []


def test_rejection_message_truncates_long_sql():
    sql = "DROP TABLE " + "x" * 500

    with pytest.raises(ValueError) as excinfo:
        run_sql_query(sql, conn=_FakeConnection())

    assert len(str(excinfo.value)) < 300


# ---------------------------------------------------------------------------
# Result shaping (seeded in-memory database)
# ---------------------------------------------------------------------------

def test_run_sql_query_returns_list_of_dicts_keyed_by_column(db):
    rows = run_sql_query(
        "SELECT name, price FROM steam_games WHERE steam_id = 1", conn=db
    )

    assert rows == [{"name": "Action RPG Blockbuster", "price": 59.99}]


def test_run_sql_query_honours_column_aliases(db):
    rows = run_sql_query(
        "SELECT COUNT(*) AS total FROM steam_games WHERE publisher_class = 'AAA'",
        conn=db,
    )

    assert rows == [{"total": 3}]


def test_run_sql_query_returns_empty_list_when_nothing_matches(db):
    rows = run_sql_query(
        "SELECT name FROM steam_games WHERE price > 1000", conn=db
    )

    assert rows == []


def test_run_sql_query_filters_json_array_columns_with_like(db):
    rows = run_sql_query(
        "SELECT name FROM steam_games WHERE genres LIKE '%Racing%'", conn=db
    )

    assert rows == [{"name": "Racing Sim"}]


def test_run_sql_query_respects_explicit_limit_and_order(db):
    rows = run_sql_query(
        "SELECT name FROM steam_games ORDER BY copies_sold DESC LIMIT 2",
        conn=db,
    )

    assert [row["name"] for row in rows] == [
        "Free To Play Shooter",
        "Action RPG Blockbuster",
    ]


def test_run_sql_query_does_not_close_caller_owned_connection(db):
    run_sql_query("SELECT 1 AS one", conn=db)

    # Connection is still usable afterwards.
    assert run_sql_query("SELECT 2 AS two", conn=db) == [{"two": 2}]


# ---------------------------------------------------------------------------
# Row limits
# ---------------------------------------------------------------------------

def test_run_sql_query_appends_default_limit_when_missing():
    conn = _FakeConnection()

    run_sql_query("SELECT value FROM t;", conn=conn)

    assert conn.executed == ["SELECT value FROM t LIMIT 1000"]


def test_run_sql_query_keeps_explicit_limit_unchanged():
    conn = _FakeConnection()

    run_sql_query("SELECT value FROM t LIMIT 5", conn=conn)

    assert conn.executed == ["SELECT value FROM t LIMIT 5"]


def test_run_sql_query_returns_exactly_1000_rows():
    rows = run_sql_query("SELECT value FROM t", conn=_FakeConnection(1000))

    assert len(rows) == 1000
    assert rows[0] == {"value": 0}
    assert rows[-1] == {"value": 999}


def test_sql_query_rejects_explicit_limits_over_1000_rows():
    conn = _FakeConnection(row_count=5000)

    with pytest.raises(ValueError, match="cannot exceed 1000 rows"):
        run_sql_query("SELECT value LIMIT 5000", conn=conn)


# ---------------------------------------------------------------------------
# Schema info
# ---------------------------------------------------------------------------

def test_get_schema_info_describes_table_and_json_columns():
    info = get_schema_info()

    assert "steam_games" in info
    assert "copies_sold" in info
    assert "LIKE" in info
