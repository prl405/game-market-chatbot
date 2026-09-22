"""
Release-date windowed query tool with human-friendly year/month inputs.
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from game_market_chatbot.tools.db_helpers import _get_conn, _parse_json_field, _rows_to_dicts


def get_games_by_release_date(
    year_from: int | None = None,
    year_to: int | None = None,
    month_from: int | None = None,
    month_to: int | None = None,
    genre_filter: str | None = None,
    order_by: str = "release_date",
    limit: int = 50,
    conn=None,
) -> list[dict[str, Any]]:
    """
    Return games released within a date window, with optional genre filter.

    Dates are stored as Unix timestamps in milliseconds. This function
    accepts human-friendly year/month integers and converts them to the
    correct millisecond boundaries internally.

    Args:
        year_from:    Start year (inclusive). e.g. 2020. Defaults to no lower bound.
        year_to:      End year (inclusive). e.g. 2023. Defaults to no upper bound.
        month_from:   Start month 1-12, only applied when year_from is set.
                      Defaults to January (1) when year_from is provided.
        month_to:     End month 1-12, only applied when year_to is set.
                      Defaults to December (12) when year_to is provided.
        genre_filter: Optional genre to filter by (LIKE match on JSON array).
        order_by:     Column to sort by. One of "release_date" (default) or
                      "copies_sold". Both sort descending.
        limit:        Maximum rows to return (default 50, max 200).
        conn:         Optional database connection (used in tests).

    Returns:
        List of dicts with keys: steam_id, name, release_date,
        release_year, copies_sold, price, review_score,
        publisher_class, genres.
    """
    limit = min(int(limit), 200)

    if order_by not in ("release_date", "copies_sold"):
        raise ValueError(
            f"order_by must be 'release_date' or 'copies_sold', got {order_by!r}"
        )

    # Convert year/month inputs to millisecond timestamps.
    ts_from: int | None = None
    ts_to:   int | None = None

    if year_from is not None:
        m = month_from if month_from is not None else 1
        ts_from = int(datetime(year_from, m, 1, tzinfo=timezone.utc).timestamp() * 1000)

    if year_to is not None:
        m = month_to if month_to is not None else 12
        # Use the first day of the *next* month as the exclusive upper bound
        # so the entire final month is included.
        if m == 12:
            end_dt = datetime(year_to + 1, 1, 1, tzinfo=timezone.utc)
        else:
            end_dt = datetime(year_to, m + 1, 1, tzinfo=timezone.utc)
        ts_to = int(end_dt.timestamp() * 1000) - 1  # inclusive last ms

    # Build WHERE clauses dynamically.
    conditions = ["release_date IS NOT NULL"]
    params: list = []

    if ts_from is not None:
        conditions.append("release_date >= ?")
        params.append(ts_from)

    if ts_to is not None:
        conditions.append("release_date <= ?")
        params.append(ts_to)

    if genre_filter:
        conditions.append("genres LIKE ?")
        params.append(f"%{genre_filter}%")

    where = " AND ".join(conditions)
    params.append(limit)

    connection, should_close = _get_conn(conn)

    try:
        cursor = connection.cursor()
        cursor.execute(
            f"""
            SELECT
                steam_id,
                name,
                release_date,
                -- Derive a human-readable year from the ms timestamp.
                CAST(strftime('%Y', release_date / 1000, 'unixepoch') AS INTEGER)
                    AS release_year,
                copies_sold,
                price,
                review_score,
                publisher_class,
                genres
            FROM  steam_games
            WHERE {where}
            ORDER BY {order_by} DESC
            LIMIT ?
            """,
            params,
        )
        rows = _rows_to_dicts(cursor)
        for row in rows:
            row["genres"] = _parse_json_field(row.get("genres"))
        return rows

    finally:
        if should_close:
            connection.close()
