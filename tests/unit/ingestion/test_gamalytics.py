"""Unit tests for Gamalytics record mapping, serialization and paging.

HTTP and the DB connection are mocked/in-memory; no network is used.
"""

import json
from pathlib import Path
from unittest.mock import MagicMock

import httpx
import pytest
import turso

from game_market_chatbot.ingestion import gamalytics
from game_market_chatbot.ingestion.gamalytics import (
    GamalyticsIngester,
    _build_record,
    _serialize,
)

# The CREATE TABLE statement from the production schema, so the tests can't
# drift from the real table definition.
_SCHEMA_PATH = (
    Path(__file__).resolve().parents[3]
    / "src" / "game_market_chatbot" / "db" / "schema.sql"
)
_CREATE_TABLE_SQL = _SCHEMA_PATH.read_text().split(";")[0]

FULL_PAYLOAD = {
    "steamId": 42,
    "name": "Test Game",
    "copiesSold": 1000,
    "price": 19.99,
    "reviewScore": 90,
    "publisherClass": "Indie",
    "unreleased": False,
    "earlyAccess": True,
    "releaseDate": 1_600_000_000_000,
    "firstReleaseDate": 1_500_000_000_000,
    "earlyAccessExitDate": 1_550_000_000_000,
    "genres": ["Action", "Indie"],
    "developers": ["Dev"],
    "publishers": ["Pub"],
}


# --- _serialize -----------------------------------------------------------

def test_serialize_list_returns_json():
    assert _serialize(["A", "B"]) == '["A", "B"]'


def test_serialize_none_returns_none():
    assert _serialize(None) is None


def test_serialize_empty_list_returns_empty_json_array():
    assert _serialize([]) == "[]"


# --- _build_record --------------------------------------------------------

def test_build_record_maps_full_payload():
    rec = _build_record(FULL_PAYLOAD)
    assert rec == (
        42, "Test Game", 1000, 19.99, 90, "Indie",
        0, 1,
        1_600_000_000_000, 1_500_000_000_000, 1_550_000_000_000,
        '["Action", "Indie"]', '["Dev"]', '["Pub"]',
    )


def test_build_record_missing_fields_become_none_and_flags_zero():
    rec = _build_record({"steamId": 1, "name": "Bare"})
    assert rec == (1, "Bare", None, None, None, None, 0, 0,
                   None, None, None, None, None, None)


def test_build_record_falls_back_to_alternate_ea_date_field():
    rec = _build_record({"steamId": 1, "EAReleaseDate": 123})
    assert rec[10] == 123


def test_build_record_prefers_earlyAccessExitDate_over_alternate():
    rec = _build_record({"earlyAccessExitDate": 1, "EAReleaseDate": 2})
    assert rec[10] == 1


def test_build_record_truthy_flags_normalized_to_int():
    rec = _build_record({"unreleased": True, "earlyAccess": None})
    assert rec[6] == 1
    assert rec[7] == 0


def test_build_record_empty_dict_yields_all_defaults():
    rec = _build_record({})
    assert len(rec) == 14
    assert rec[6] == 0 and rec[7] == 0
    assert rec[0] is None


# --- _upsert_page against in-memory DB -----------------------------------

@pytest.fixture()
def empty_db():
    conn = turso.connect(":memory:")
    conn.cursor().execute(_CREATE_TABLE_SQL)
    conn.commit()
    yield conn
    conn.close()


def test_upsert_page_inserts_rows_and_returns_count(empty_db):
    cur = empty_db.cursor()
    n = GamalyticsIngester()._upsert_page(
        cur, [FULL_PAYLOAD, {"steamId": 43, "name": "Other"}]
    )
    empty_db.commit()
    assert n == 2
    rows = cur.execute(
        "SELECT steam_id, name, genres, early_access, ingested_at "
        "FROM steam_games ORDER BY steam_id"
    ).fetchall()
    assert rows[0][:4] == (42, "Test Game", '["Action", "Indie"]', 1)
    assert json.loads(rows[0][2]) == ["Action", "Indie"]
    assert rows[0][4] > 0
    assert rows[1][0] == 43 and rows[1][2] is None


def test_upsert_page_replaces_existing_steam_id(empty_db):
    cur = empty_db.cursor()
    ing = GamalyticsIngester()
    ing._upsert_page(cur, [{"steamId": 1, "name": "Old"}])
    ing._upsert_page(cur, [{"steamId": 1, "name": "New"}])
    rows = cur.execute("SELECT name FROM steam_games").fetchall()
    assert rows == [("New",)]


def test_upsert_page_empty_list_returns_zero(empty_db):
    assert GamalyticsIngester()._upsert_page(empty_db.cursor(), []) == 0


# --- _fetch_page (httpx mocked) ------------------------------------------

def test_fetch_page_sends_params_and_returns_json(monkeypatch):
    resp = MagicMock()
    resp.json.return_value = {"pages": 1, "total": 0, "result": []}
    get = MagicMock(return_value=resp)
    monkeypatch.setattr(gamalytics.httpx, "get", get)

    out = GamalyticsIngester()._fetch_page(3, "KEY")

    assert out == {"pages": 1, "total": 0, "result": []}
    _, kwargs = get.call_args
    assert kwargs["params"] == {"page": 3, "limit": 1000, "api_key": "KEY"}


def test_fetch_page_omits_api_key_when_absent(monkeypatch):
    resp = MagicMock()
    resp.json.return_value = {}
    get = MagicMock(return_value=resp)
    monkeypatch.setattr(gamalytics.httpx, "get", get)

    GamalyticsIngester()._fetch_page(0, None)

    assert "api_key" not in get.call_args.kwargs["params"]


def test_fetch_page_propagates_http_errors(monkeypatch):
    resp = MagicMock()
    resp.raise_for_status.side_effect = httpx.HTTPStatusError(
        "boom", request=MagicMock(), response=MagicMock()
    )
    monkeypatch.setattr(gamalytics.httpx, "get", MagicMock(return_value=resp))

    with pytest.raises(httpx.HTTPStatusError):
        GamalyticsIngester()._fetch_page(0, None)


# --- ingest paging (fetch + connection mocked) ---------------------------

def _run_ingest(monkeypatch, pages, **kwargs):
    conn = MagicMock()
    monkeypatch.setattr(gamalytics, "get_connection", lambda: conn)
    monkeypatch.setattr(gamalytics.time, "sleep", lambda s: None)
    monkeypatch.delenv("GAMALYTICS_API_KEY", raising=False)
    fetched = []

    def fake_fetch(self, page, api_key):
        fetched.append(page)
        return pages[page]

    monkeypatch.setattr(GamalyticsIngester, "_fetch_page", fake_fetch)
    GamalyticsIngester().ingest(**kwargs)
    return fetched, conn


def _pages(n):
    return [
        {"pages": n, "total": n, "result": [{"steamId": i, "name": f"g{i}"}]}
        for i in range(n)
    ]


def test_ingest_fetches_all_pages_and_closes_connection(monkeypatch, capsys):
    fetched, conn = _run_ingest(monkeypatch, _pages(3))
    # page 0 is fetched once for discovery and reused, not re-fetched
    assert fetched == [0, 1, 2]
    conn.close.assert_called_once()
    assert "Total records upserted: 3" in capsys.readouterr().out


def test_ingest_respects_end_page(monkeypatch, capsys):
    fetched, _ = _run_ingest(monkeypatch, _pages(5), end_page=2)
    assert fetched == [0, 1]
    assert "Total records upserted: 2" in capsys.readouterr().out


def test_ingest_start_page_skips_page_zero_records(monkeypatch, capsys):
    fetched, _ = _run_ingest(monkeypatch, _pages(4), start_page=2)
    # page 0 still fetched for discovery only
    assert fetched == [0, 2, 3]
    assert "Total records upserted: 2" in capsys.readouterr().out


def test_ingest_closes_connection_on_error(monkeypatch):
    conn = MagicMock()
    monkeypatch.setattr(gamalytics, "get_connection", lambda: conn)

    def boom(self, page, api_key):
        raise RuntimeError("api down")

    monkeypatch.setattr(GamalyticsIngester, "_fetch_page", boom)
    with pytest.raises(RuntimeError):
        GamalyticsIngester().ingest()
    conn.close.assert_called_once()
