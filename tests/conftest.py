"""Fixtures shared across Python test suites.

Only setup needed by more than one suite belongs here. Module-specific
fixtures stay beside the tests that use them.

The seeded in-memory database is used by query, SQL-fallback, and dispatch
tests. No checked-in database file or network connection is involved.

Fixture data covers:
  - Multi-genre games (verifies LIKE filtering works on JSON arrays)
  - Multiple publisher classes (AAA, AA, Indie)
  - A range of prices and review scores
  - A free-to-play game (price = 0)
  - A game with NULL copies_sold (should be excluded from aggregations)
"""

from __future__ import annotations

import json
from datetime import datetime, timezone

import pytest
import turso


SCHEMA_SQL = """
CREATE TABLE steam_games (
    steam_id            INTEGER PRIMARY KEY,
    name                TEXT    NOT NULL,
    copies_sold         INTEGER,
    price               REAL,
    review_score        INTEGER,
    publisher_class     TEXT,
    unreleased          INTEGER,
    early_access        INTEGER,
    release_date        INTEGER,
    first_release_date  INTEGER,
    ea_release_date     INTEGER,
    genres              TEXT,
    developers          TEXT,
    publishers          TEXT,
    ingested_at         INTEGER
)
"""

# Columns match the INSERT order used in _seed_db.
FIXTURE_GAMES = [
    # (steam_id, name, copies_sold, price, review_score, publisher_class,
    #  genres, developers, publishers)
    (
        1, "Action RPG Blockbuster",
        30_000_000, 59.99, 95, "AAA",
        ["Action", "RPG"],
        ["Big Studio"], ["Big Publisher"],
    ),
    (
        2, "Cozy Farming Sim",
        8_000_000, 19.99, 97, "Indie",
        ["Simulation", "Casual", "Indie"],
        ["Solo Dev"], ["Solo Dev"],
    ),
    (
        3, "Tactical Strategy Game",
        3_500_000, 39.99, 82, "AA",
        ["Strategy", "Indie"],
        ["Mid Studio"], ["Mid Publisher"],
    ),
    (
        4, "Free To Play Shooter",
        50_000_000, 0.0, 71, "AAA",
        ["Action", "Free To Play", "Massively Multiplayer"],
        ["Live Service Co"], ["Live Service Co"],
    ),
    (
        5, "Atmospheric RPG",
        5_000_000, 49.99, 91, "AA",
        ["RPG", "Adventure"],
        ["Narrative Studio"], ["AA Publisher"],
    ),
    (
        6, "Hobby Platformer",
        150_000, 9.99, 78, "Hobbyist",
        ["Action", "Indie"],
        ["One Person"], ["One Person"],
    ),
    (
        7, "Unreleased Game",
        None, 29.99, None, "AA",   # NULL copies_sold — must be excluded
        ["Action"],
        ["Dev"], ["Pub"],
    ),
    (
        8, "Puzzle Adventure",
        2_000_000, 14.99, 88, "Indie",
        ["Adventure", "Casual", "Indie"],
        ["Small Team"], ["Indie Label"],
    ),
    (
        9, "Racing Sim",
        1_200_000, 24.99, 84, "AA",
        ["Racing", "Simulation", "Sports"],
        ["Sim Studio"], ["Sim Publisher"],
    ),
    (
        10, "Massive MMO",
        12_000_000, 0.0, 69, "AAA",
        ["Massively Multiplayer", "RPG", "Free To Play"],
        ["MMO Corp"], ["MMO Corp"],
    ),
]


def _seed_db(conn) -> None:
    """Create the steam_games table and insert all fixture rows."""
    cur = conn.cursor()
    cur.execute(SCHEMA_SQL)

    for game in FIXTURE_GAMES:
        steam_id, name, copies_sold, price, review_score, publisher_class, \
            genres, developers, publishers = game

        cur.execute(
            """
            INSERT INTO steam_games (
                steam_id, name, copies_sold, price, review_score,
                publisher_class, genres, developers, publishers, ingested_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, 0)
            """,
            (
                steam_id, name, copies_sold, price, review_score,
                publisher_class,
                json.dumps(genres),
                json.dumps(developers),
                json.dumps(publishers),
            ),
        )

    # Assign release dates (ms timestamps) so release-date tests are meaningful.
    # steam_id → (year, month)
    release_dates = {
        1:  (2018, 10),   # Action RPG Blockbuster — Oct 2018
        2:  (2016, 2),    # Cozy Farming Sim       — Feb 2016
        3:  (2021, 4),    # Tactical Strategy Game — Apr 2021
        4:  (2019, 3),    # Free To Play Shooter   — Mar 2019
        5:  (2022, 11),   # Atmospheric RPG        — Nov 2022
        6:  (2020, 7),    # Hobby Platformer       — Jul 2020
        7:  (2023, 1),    # Unreleased Game        — Jan 2023 (NULL copies)
        8:  (2021, 9),    # Puzzle Adventure       — Sep 2021
        9:  (2020, 5),    # Racing Sim             — May 2020
        10: (2017, 6),    # Massive MMO            — Jun 2017
    }
    for steam_id, (year, month) in release_dates.items():
        ts_ms = int(datetime(year, month, 1, tzinfo=timezone.utc).timestamp() * 1000)
        cur.execute(
            "UPDATE steam_games SET release_date = ? WHERE steam_id = ?",
            (ts_ms, steam_id),
        )

    conn.commit()


@pytest.fixture()
def db():
    """Provide a seeded in-memory turso connection for each test."""
    conn = turso.connect(":memory:")
    _seed_db(conn)
    yield conn
    conn.close()


# ---------------------------------------------------------------------------
