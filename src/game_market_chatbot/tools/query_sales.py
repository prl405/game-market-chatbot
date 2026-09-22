"""
Sales and pricing query tools: ranking games by copies sold and by price band.
"""

from __future__ import annotations

from typing import Any

from game_market_chatbot.tools.db_helpers import _get_conn, _parse_json_field, _rows_to_dicts


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
