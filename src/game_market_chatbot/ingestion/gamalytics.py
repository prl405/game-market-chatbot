"""
Gamalytics ingester — fetches Steam game data from the Gamalytics API
and upserts it into the local Turso database.

Rate limits (as of 2026):
  Free tier : 250 requests/day, limited data access.
  Paid tier : higher limits, full data access.

At limit=1000 per page the full catalogue (~130k games) requires ~130
requests. Run this script carefully on a free account — you can ingest
in batches using the --start-page / --end-page options if needed.

Usage (via CLI):
    uv run game-market-chatbot ingest gamalytics

Environment variables (set in .env or shell):
    GAMALYTICS_API_KEY   Optional. Passed as ?api_key= if present.
    DB_PATH              Path to the SQLite database file.
"""

from __future__ import annotations

import json
import os
import time

import httpx
from dotenv import load_dotenv

from game_market_chatbot.db.client import get_connection
from game_market_chatbot.ingestion.base import BaseIngester

load_dotenv()

_BASE_URL = "https://api.gamalytic.com/steam-games/list"
_PAGE_SIZE = 1000
# Be conservative with request timing to avoid hammering the API.
_REQUEST_DELAY_SECONDS = 0.5

# SQL for upserting a single game record.
# INSERT OR REPLACE uses the PRIMARY KEY (steam_id) for conflict resolution,
# effectively updating all columns if the row already exists.
_UPSERT_SQL = """
INSERT OR REPLACE INTO steam_games (
    steam_id,
    name,
    copies_sold,
    price,
    review_score,
    publisher_class,
    unreleased,
    early_access,
    release_date,
    first_release_date,
    ea_release_date,
    genres,
    developers,
    publishers,
    ingested_at
) VALUES (
    ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?,
    strftime('%s', 'now') * 1000
)
"""


def _serialize(value: list | None) -> str | None:
    """JSON-encode a list field (genres, developers, publishers)."""
    if value is None:
        return None
    return json.dumps(value)


def _build_record(game: dict) -> tuple:
    """Map an API response dict to the positional params for _UPSERT_SQL."""
    return (
        game.get("steamId"),
        game.get("name"),
        game.get("copiesSold"),
        game.get("price"),
        game.get("reviewScore"),
        game.get("publisherClass"),
        1 if game.get("unreleased") else 0,
        1 if game.get("earlyAccess") else 0,
        game.get("releaseDate"),
        game.get("firstReleaseDate"),
        # earlyAccessExitDate is the EA exit date; API field name varies
        game.get("earlyAccessExitDate") or game.get("EAReleaseDate"),
        _serialize(game.get("genres")),
        _serialize(game.get("developers")),
        _serialize(game.get("publishers")),
    )


class GamalyticsIngester(BaseIngester):
    """Ingests Steam game data from api.gamalytic.com."""

    source_name = "gamalytics"

    def ingest(self, start_page: int = 0, end_page: int | None = None) -> None:
        """
        Paginate through /steam-games/list and upsert all records.

        Args:
            start_page: First page to fetch (0-indexed). Defaults to 0.
            end_page:   Last page to fetch (exclusive). Defaults to all pages.
                        Useful for incremental ingestion on free-tier accounts.
        """
        api_key = os.environ.get("GAMALYTICS_API_KEY")
        conn = get_connection()
        cursor = conn.cursor()
        total_upserted = 0

        try:
            # Fetch the first page to discover total page count.
            first_response = self._fetch_page(0, api_key)
            total_pages = first_response["pages"]
            total_games = first_response["total"]

            effective_end = end_page if end_page is not None else total_pages
            effective_end = min(effective_end, total_pages)

            print(
                f"Gamalytics: {total_games:,} games across {total_pages} pages. "
                f"Ingesting pages {start_page}–{effective_end - 1}."
            )

            # Process page 0 if it falls within the requested range.
            if start_page == 0:
                count = self._upsert_page(cursor, first_response["result"])
                conn.commit()
                total_upserted += count
                print(f"  Page 0/{total_pages - 1} — {count} records upserted "
                      f"(running total: {total_upserted:,})")
                pages_to_fetch = range(1, effective_end)
            else:
                pages_to_fetch = range(start_page, effective_end)

            for page in pages_to_fetch:
                time.sleep(_REQUEST_DELAY_SECONDS)
                response = self._fetch_page(page, api_key)
                count = self._upsert_page(cursor, response["result"])
                conn.commit()
                total_upserted += count
                print(
                    f"  Page {page}/{total_pages - 1} — {count} records upserted "
                    f"(running total: {total_upserted:,})"
                )

        finally:
            conn.close()

        print(f"\nIngestion complete. Total records upserted: {total_upserted:,}")

    def _fetch_page(self, page: int, api_key: str | None) -> dict:
        """Fetch a single page from the Gamalytics API."""
        params: dict[str, str | int] = {"page": page, "limit": _PAGE_SIZE}
        if api_key:
            params["api_key"] = api_key

        response = httpx.get(_BASE_URL, params=params, timeout=30)
        response.raise_for_status()
        return response.json()

    def _upsert_page(self, cursor, records: list[dict]) -> int:
        """Upsert a list of game records. Returns the count of rows processed."""
        rows = [_build_record(game) for game in records]
        cursor.executemany(_UPSERT_SQL, rows)
        return len(rows)
