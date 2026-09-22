"""
Market-level aggregate query tools: genre share, publisher tiers, review scores.
"""

from __future__ import annotations

from typing import Any

from game_market_chatbot.tools.db_helpers import _get_conn, _rows_to_dicts


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
