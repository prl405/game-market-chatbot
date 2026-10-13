"""
Integration tests for end-to-end dispatch against the seeded database.

Registry, routing and error handling live in tests/unit/tools/test_dispatch.py.

Each test runs real SQL against the seeded in-memory turso database provided
by the shared `db` fixture in tests/conftest.py. No real database file or
network connection is required.
"""

from __future__ import annotations

import pytest

from game_market_chatbot.tools.dispatch import dispatch


# ---------------------------------------------------------------------------
# dispatch against the seeded database
# ---------------------------------------------------------------------------

class _NonClosingConnection:
    """Proxy that ignores close() so the fixture owns the connection."""

    def __init__(self, conn):
        self._conn = conn

    def close(self):
        pass

    def __getattr__(self, name):
        return getattr(self._conn, name)


@pytest.fixture
def seeded_dispatch_db(db, monkeypatch):
    """Route dispatch's default connection to the seeded in-memory database."""
    monkeypatch.setattr(
        "game_market_chatbot.db.client.get_connection",
        lambda: _NonClosingConnection(db),
    )


class TestDispatch:

    def test_dispatch_with_dict_args(self, seeded_dispatch_db):
        result = dispatch("get_publisher_class_breakdown", {})
        assert {row["publisher_class"] for row in result} == {
            "AAA", "AA", "Indie", "Hobbyist",
        }

    def test_dispatch_with_json_string_args(self, seeded_dispatch_db):
        import json

        result = dispatch("get_top_games_by_copies_sold", json.dumps({"limit": 5}))
        assert len(result) == 5
        assert result[0]["name"] == "Free To Play Shooter"

    def test_dispatch_empty_string_args(self, seeded_dispatch_db):
        result = dispatch("get_genre_market_share", "")
        assert any(row["genre"] == "Action" for row in result)
