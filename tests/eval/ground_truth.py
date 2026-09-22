"""
Ground-truth computations for the answer-quality eval suite.

Every function here queries the real `steam_games` table directly with raw
SQL / Python, deliberately WITHOUT importing anything from
`game_market_chatbot.tools.queries` — the point is to have an oracle that is
independent of the app's own (possibly buggy) query implementations.

All functions accept a DB-API 2.0 connection (e.g. from
`game_market_chatbot.db.client.get_connection()`).
"""

from __future__ import annotations

import json
import statistics
from collections import Counter
from typing import Any

# Genres known to appear in the Gamalytics dataset (mirrors the fixed list
# used by the app's get_genre_market_share, kept in sync intentionally so
# both sides are answering the same question about the same genre set).
KNOWN_GENRES = [
    "Action", "Adventure", "Casual", "Early Access", "Free To Play",
    "Indie", "Massively Multiplayer", "RPG", "Racing", "Simulation",
    "Sports", "Strategy",
]

# Explicit definition of "comparable game" for eval case 9 — a game is
# comparable to a mid-priced Indie RPG if it shares the genre, sits within
# a $10 price band, and released in the same broad era.
COMPARABLE_GAME_FILTER = {
    "genre": "RPG",
    "min_price": 10.0,
    "max_price": 30.0,
    "publisher_class": "Indie",
    "year_from": 2020,
    "year_to": 2024,
}


def _fetchall_dicts(cursor) -> list[dict[str, Any]]:
    cols = [d[0] for d in cursor.description]
    return [dict(zip(cols, row)) for row in cursor.fetchall()]


def top_games_by_copies_sold(conn, limit: int = 10) -> list[str]:
    """Return the names of the top-N games by copies sold."""
    cur = conn.cursor()
    cur.execute(
        """
        SELECT name FROM steam_games
        WHERE copies_sold IS NOT NULL
        ORDER BY copies_sold DESC
        LIMIT ?
        """,
        (limit,),
    )
    return [row[0] for row in cur.fetchall()]


def genre_market_share(conn) -> dict[str, float]:
    """Return {genre: percent_of_total_copies_sold} for each known genre.

    Because genres is a JSON array, a game can contribute to more than one
    genre's total, so percentages need not sum to 100.
    """
    cur = conn.cursor()
    cur.execute("SELECT SUM(copies_sold) FROM steam_games WHERE copies_sold IS NOT NULL")
    total = cur.fetchone()[0] or 0
    if total == 0:
        return {genre: 0.0 for genre in KNOWN_GENRES}

    shares: dict[str, float] = {}
    for genre in KNOWN_GENRES:
        cur.execute(
            """
            SELECT SUM(copies_sold) FROM steam_games
            WHERE copies_sold IS NOT NULL AND genres LIKE ?
            """,
            (f"%{genre}%",),
        )
        genre_total = cur.fetchone()[0] or 0
        shares[genre] = round(genre_total / total * 100, 2)
    return shares


def games_priced_at_or_below(conn, threshold: float = 9.99) -> int:
    """Return the count of games priced at or below `threshold`."""
    cur = conn.cursor()
    cur.execute(
        "SELECT COUNT(*) FROM steam_games WHERE price IS NOT NULL AND price <= ?",
        (threshold,),
    )
    return cur.fetchone()[0]


def median_price(conn) -> float:
    """Return the median price across all games with a non-null price."""
    cur = conn.cursor()
    cur.execute("SELECT price FROM steam_games WHERE price IS NOT NULL")
    prices = [row[0] for row in cur.fetchall()]
    return statistics.median(prices)


def games_released_in_year(conn, year: int = 2024) -> int:
    """Return the count of games released in `year` (release_date is ms epoch)."""
    cur = conn.cursor()
    cur.execute(
        """
        SELECT COUNT(*) FROM steam_games
        WHERE release_date IS NOT NULL
        AND strftime('%Y', release_date / 1000, 'unixepoch') = ?
        """,
        (str(year),),
    )
    return cur.fetchone()[0]


def review_score_distribution(conn) -> dict[str, int]:
    """Return {bucket_label: game_count} in 10-point review-score bands."""
    cur = conn.cursor()
    cur.execute(
        """
        SELECT (review_score / 10) * 10 AS bucket_start, COUNT(*)
        FROM steam_games
        WHERE review_score IS NOT NULL AND copies_sold IS NOT NULL
        GROUP BY bucket_start
        ORDER BY bucket_start ASC
        """
    )
    buckets: dict[str, int] = {}
    for bucket_start, count in cur.fetchall():
        bucket_start = int(bucket_start)
        bucket_end = min(bucket_start + 9, 100)
        buckets[f"{bucket_start}-{bucket_end}"] = count
    return buckets


def top_publishers_by_game_count(conn, top_n: int = 10) -> list[tuple[str, int]]:
    """Return the top-N publishers by number of games, tallied in Python.

    `publishers` is a JSON array column, so unnesting is done row-by-row
    with json.loads + Counter rather than in SQL.
    """
    cur = conn.cursor()
    cur.execute("SELECT publishers FROM steam_games WHERE publishers IS NOT NULL")
    counts: Counter[str] = Counter()
    for (raw,) in cur.fetchall():
        try:
            names = json.loads(raw)
        except (json.JSONDecodeError, TypeError):
            continue
        counts.update(names)
    return counts.most_common(top_n)


def top_games_in_genre(conn, genre: str = "RPG", limit: int = 10) -> list[str]:
    """Return the names of the top-N games by copies sold within `genre`."""
    cur = conn.cursor()
    cur.execute(
        """
        SELECT name FROM steam_games
        WHERE copies_sold IS NOT NULL AND genres LIKE ?
        ORDER BY copies_sold DESC
        LIMIT ?
        """,
        (f"%{genre}%", limit),
    )
    return [row[0] for row in cur.fetchall()]


def comparable_games_count(conn, filt: dict[str, Any] = COMPARABLE_GAME_FILTER) -> int:
    """Return the count of games matching the explicit COMPARABLE_GAME_FILTER."""
    cur = conn.cursor()
    cur.execute(
        """
        SELECT COUNT(*) FROM steam_games
        WHERE genres LIKE ?
        AND price BETWEEN ? AND ?
        AND publisher_class = ?
        AND strftime('%Y', release_date / 1000, 'unixepoch') BETWEEN ? AND ?
        """,
        (
            f"%{filt['genre']}%",
            filt["min_price"],
            filt["max_price"],
            filt["publisher_class"],
            str(filt["year_from"]),
            str(filt["year_to"]),
        ),
    )
    return cur.fetchone()[0]


def percentile_outliers(conn, percentile: float = 95.0) -> tuple[float, list[str]]:
    """Return (threshold, names) for games at or above the given percentile
    of copies_sold.
    """
    cur = conn.cursor()
    cur.execute("SELECT copies_sold FROM steam_games WHERE copies_sold IS NOT NULL")
    values = sorted(row[0] for row in cur.fetchall())
    cutpoints = statistics.quantiles(values, n=100, method="inclusive")
    threshold = cutpoints[int(percentile) - 1]

    cur.execute(
        "SELECT name FROM steam_games WHERE copies_sold >= ?",
        (threshold,),
    )
    names = [row[0] for row in cur.fetchall()]
    return threshold, names
