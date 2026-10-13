"""Unit tests for the shared helpers in tools.db_helpers."""

from __future__ import annotations


from game_market_chatbot.tools.db_helpers import (
    _get_conn,
    _parse_json_field,
    _rows_to_dicts,
)


class TestGetConn:
    def test_returns_supplied_connection_not_owned(self):
        sentinel = object()
        conn, owned = _get_conn(sentinel)
        assert conn is sentinel
        assert owned is False

    def test_opens_live_connection_when_none_supplied(self, monkeypatch):
        sentinel = object()
        monkeypatch.setattr(
            "game_market_chatbot.db.client.get_connection", lambda: sentinel
        )
        conn, owned = _get_conn()
        assert conn is sentinel
        assert owned is True


class TestRowsToDicts:
    def test_maps_column_names_to_values(self, db):
        cur = db.cursor()
        cur.execute(
            "SELECT steam_id, name FROM steam_games WHERE steam_id = 2"
        )
        assert _rows_to_dicts(cur) == [
            {"steam_id": 2, "name": "Cozy Farming Sim"}
        ]

    def test_empty_result_gives_empty_list(self, db):
        cur = db.cursor()
        cur.execute("SELECT name FROM steam_games WHERE steam_id = -1")
        assert _rows_to_dicts(cur) == []

    def test_respects_aliases_and_row_count(self, db):
        cur = db.cursor()
        cur.execute("SELECT COUNT(*) AS n FROM steam_games")
        assert _rows_to_dicts(cur) == [{"n": 10}]

    def test_preserves_null_values(self, db):
        cur = db.cursor()
        cur.execute("SELECT copies_sold FROM steam_games WHERE steam_id = 7")
        assert _rows_to_dicts(cur) == [{"copies_sold": None}]


class TestParseJsonField:
    def test_none_gives_empty_list(self):
        assert _parse_json_field(None) == []

    def test_valid_json_list(self):
        assert _parse_json_field('["Action", "RPG"]') == ["Action", "RPG"]

    def test_empty_json_list(self):
        assert _parse_json_field("[]") == []

    def test_malformed_json_gives_empty_list(self):
        assert _parse_json_field("[not json") == []

    def test_empty_string_gives_empty_list(self):
        assert _parse_json_field("") == []

    def test_non_string_input_gives_empty_list(self):
        assert _parse_json_field(object()) == []
