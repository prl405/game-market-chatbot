"""
Predefined query tools for the game market chatbot.

Each function runs a parameterised SQL query against the steam_games table
and returns plain serialisable Python data (lists of dicts) ready to be
passed to the LLM as tool call results.

All functions accept an optional `conn` parameter. When omitted the live
database connection from `db.client.get_connection()` is used. Passing an
explicit connection (e.g. an in-memory turso connection) makes the functions
fully testable without touching the real database.

JSON array columns note
-----------------------
`genres`, `developers`, and `publishers` are stored as JSON-encoded text,
e.g. '["Action","RPG"]'. Filtering must use LIKE '%value%' — never equality.
This is enforced throughout and documented in each relevant function.
"""

from __future__ import annotations

import json
from datetime import datetime, timezone
from typing import Any


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------

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


# ---------------------------------------------------------------------------
# Query functions
# ---------------------------------------------------------------------------

def get_top_games_by_copies_sold(
    limit: int = 10,
    genre_filter: str | None = None,
    conn=None,
) -> list[dict[str, Any]]:
    """
    Return the top N games ranked by copies sold.

    Args:
        limit:        Number of games to return (default 10, max 100).
        genre_filter: Optional genre name to filter by, e.g. "RPG".
                      Matched with LIKE against the JSON genres column.
        conn:         Optional database connection (used in tests).

    Returns:
        List of dicts with keys: steam_id, name, copies_sold, price,
        review_score, publisher_class, genres.
    """
    limit = min(int(limit), 100)
    connection, should_close = _get_conn(conn)

    try:
        cursor = connection.cursor()

        if genre_filter:
            # genres is a JSON array stored as text — use LIKE for filtering.
            cursor.execute(
                """
                SELECT steam_id, name, copies_sold, price,
                       review_score, publisher_class, genres
                FROM   steam_games
                WHERE  copies_sold IS NOT NULL
                AND    genres LIKE ?
                ORDER  BY copies_sold DESC
                LIMIT  ?
                """,
                (f"%{genre_filter}%", limit),
            )
        else:
            cursor.execute(
                """
                SELECT steam_id, name, copies_sold, price,
                       review_score, publisher_class, genres
                FROM   steam_games
                WHERE  copies_sold IS NOT NULL
                ORDER  BY copies_sold DESC
                LIMIT  ?
                """,
                (limit,),
            )

        rows = _rows_to_dicts(cursor)
        for row in rows:
            row["genres"] = _parse_json_field(row.get("genres"))
        return rows

    finally:
        if should_close:
            connection.close()


def get_genre_market_share(conn=None) -> list[dict[str, Any]]:
    """
    Return total copies sold and game count aggregated by genre.

    Because genres is a JSON array each game may contribute to multiple
    genre rows. This function expands genres using a JSON workaround
    compatible with SQLite: it uses a known fixed set of genres derived
    from the Gamalytics data and queries each with LIKE.

    Returns:
        List of dicts sorted by total_copies_sold desc, with keys:
        genre, game_count, total_copies_sold, avg_copies_sold,
        avg_review_score.
    """
    # Known genres from the Gamalytics dataset.
    genres = [
        "Action", "Adventure", "Casual", "Early Access", "Free To Play",
        "Indie", "Massively Multiplayer", "RPG", "Racing", "Simulation",
        "Sports", "Strategy",
    ]

    connection, should_close = _get_conn(conn)
    results = []

    try:
        cursor = connection.cursor()
        for genre in genres:
            cursor.execute(
                """
                SELECT
                    COUNT(*)            AS game_count,
                    SUM(copies_sold)    AS total_copies_sold,
                    AVG(copies_sold)    AS avg_copies_sold,
                    AVG(review_score)   AS avg_review_score
                FROM steam_games
                WHERE genres LIKE ?
                AND   copies_sold IS NOT NULL
                """,
                (f"%{genre}%",),
            )
            row = cursor.fetchone()
            if row and row[0] > 0:
                results.append({
                    "genre":             genre,
                    "game_count":        row[0],
                    "total_copies_sold": row[1],
                    "avg_copies_sold":   round(row[2]) if row[2] else 0,
                    "avg_review_score":  round(row[3], 1) if row[3] else None,
                })

    finally:
        if should_close:
            connection.close()

    results.sort(key=lambda r: r["total_copies_sold"] or 0, reverse=True)
    return results


def get_publisher_class_breakdown(conn=None) -> list[dict[str, Any]]:
    """
    Return game count and total copies sold grouped by publisher class.

    Publisher classes in the dataset: AAA, AA, Indie, Hobbyist.

    Returns:
        List of dicts sorted by total_copies_sold desc, with keys:
        publisher_class, game_count, total_copies_sold, avg_copies_sold,
        avg_review_score, avg_price.
    """
    connection, should_close = _get_conn(conn)

    try:
        cursor = connection.cursor()
        cursor.execute(
            """
            SELECT
                publisher_class,
                COUNT(*)            AS game_count,
                SUM(copies_sold)    AS total_copies_sold,
                AVG(copies_sold)    AS avg_copies_sold,
                AVG(review_score)   AS avg_review_score,
                AVG(price)          AS avg_price
            FROM  steam_games
            WHERE publisher_class IS NOT NULL
            AND   copies_sold IS NOT NULL
            GROUP BY publisher_class
            ORDER BY total_copies_sold DESC
            """
        )
        rows = _rows_to_dicts(cursor)
        for row in rows:
            row["avg_copies_sold"]  = round(row["avg_copies_sold"])  if row["avg_copies_sold"]  else 0
            row["avg_review_score"] = round(row["avg_review_score"], 1) if row["avg_review_score"] else None
            row["avg_price"]        = round(row["avg_price"], 2)     if row["avg_price"]        else None
        return rows

    finally:
        if should_close:
            connection.close()


def get_games_by_price_range(
    min_price: float = 0.0,
    max_price: float = 70.0,
    limit: int = 50,
    conn=None,
) -> list[dict[str, Any]]:
    """
    Return games within a price band, ordered by copies sold.

    Args:
        min_price: Minimum price in USD (inclusive). Default 0.
        max_price: Maximum price in USD (inclusive). Default 70.
        limit:     Maximum rows to return (default 50, max 200).
        conn:      Optional database connection (used in tests).

    Returns:
        List of dicts with keys: steam_id, name, price, copies_sold,
        review_score, publisher_class, genres.
    """
    limit = min(int(limit), 200)

    connection, should_close = _get_conn(conn)

    try:
        cursor = connection.cursor()
        cursor.execute(
            """
            SELECT steam_id, name, price, copies_sold,
                   review_score, publisher_class, genres
            FROM   steam_games
            WHERE  price       >= ?
            AND    price       <= ?
            AND    copies_sold IS NOT NULL
            ORDER  BY copies_sold DESC
            LIMIT  ?
            """,
            (float(min_price), float(max_price), limit),
        )
        rows = _rows_to_dicts(cursor)
        for row in rows:
            row["genres"] = _parse_json_field(row.get("genres"))
        return rows

    finally:
        if should_close:
            connection.close()


def get_review_score_distribution(conn=None) -> list[dict[str, Any]]:
    """
    Return a histogram of games bucketed by review score bands.

    Buckets: 0-9, 10-19, …, 90-100.

    Returns:
        List of dicts ordered by bucket asc, with keys:
        bucket_label (e.g. "90-100"), min_score, max_score, game_count,
        total_copies_sold, avg_copies_sold.
    """
    connection, should_close = _get_conn(conn)

    try:
        cursor = connection.cursor()
        cursor.execute(
            """
            SELECT
                (review_score / 10) * 10            AS bucket_start,
                COUNT(*)                            AS game_count,
                SUM(copies_sold)                    AS total_copies_sold,
                AVG(copies_sold)                    AS avg_copies_sold
            FROM  steam_games
            WHERE review_score IS NOT NULL
            AND   copies_sold  IS NOT NULL
            GROUP BY bucket_start
            ORDER BY bucket_start ASC
            """
        )
        rows = []
        for row in cursor.fetchall():
            bucket_start = int(row[0])
            bucket_end   = min(bucket_start + 9, 100)
            rows.append({
                "bucket_label":     f"{bucket_start}-{bucket_end}",
                "min_score":        bucket_start,
                "max_score":        bucket_end,
                "game_count":       row[1],
                "total_copies_sold": row[2],
                "avg_copies_sold":  round(row[3]) if row[3] else 0,
            })
        return rows

    finally:
        if should_close:
            connection.close()


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
