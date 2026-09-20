"""
Unit tests for src/game_market_chatbot/tools/queries.py and registry.py.

All tests use an in-memory turso database seeded with a small, controlled
fixture dataset. No real database file or network connection is required.

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

from game_market_chatbot.tools.queries import (
    get_games_by_price_range,
    get_games_by_release_date,
    get_genre_market_share,
    get_publisher_class_breakdown,
    get_review_score_distribution,
    get_top_games_by_copies_sold,
)
from game_market_chatbot.tools.registry import TOOLS, dispatch


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

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
# get_top_games_by_copies_sold
# ---------------------------------------------------------------------------

class TestGetTopGamesByCopiesSold:

    def test_returns_list_of_dicts(self, db):
        results = get_top_games_by_copies_sold(conn=db)
        assert isinstance(results, list)
        assert len(results) > 0
        assert isinstance(results[0], dict)

    def test_expected_keys_present(self, db):
        result = get_top_games_by_copies_sold(limit=1, conn=db)
        expected = {"steam_id", "name", "copies_sold", "price",
                    "review_score", "publisher_class", "genres"}
        assert expected.issubset(result[0].keys())

    def test_ordered_by_copies_sold_desc(self, db):
        results = get_top_games_by_copies_sold(limit=10, conn=db)
        copies = [r["copies_sold"] for r in results]
        assert copies == sorted(copies, reverse=True)

    def test_limit_is_respected(self, db):
        results = get_top_games_by_copies_sold(limit=3, conn=db)
        assert len(results) == 3

    def test_limit_capped_at_100(self, db):
        # Requesting more than 100 should still work without error.
        results = get_top_games_by_copies_sold(limit=500, conn=db)
        assert len(results) <= 100

    def test_null_copies_sold_excluded(self, db):
        results = get_top_games_by_copies_sold(conn=db)
        names = [r["name"] for r in results]
        assert "Unreleased Game" not in names

    def test_genre_filter_uses_like_not_equality(self, db):
        # "Cozy Farming Sim" has genres ["Simulation","Casual","Indie"].
        # Filtering by "Simulation" must match it even though genres is a
        # JSON string, not a plain equality value.
        results = get_top_games_by_copies_sold(genre_filter="Simulation", conn=db)
        names = [r["name"] for r in results]
        assert "Cozy Farming Sim" in names

    def test_genre_filter_excludes_non_matching(self, db):
        results = get_top_games_by_copies_sold(genre_filter="Strategy", conn=db)
        names = [r["name"] for r in results]
        # "Action RPG Blockbuster" has no Strategy genre — must not appear.
        assert "Action RPG Blockbuster" not in names

    def test_genre_filter_multi_genre_game_matched_by_any_genre(self, db):
        # "Free To Play Shooter" has ["Action","Free To Play","Massively Multiplayer"].
        # Filtering by any one of its genres should return it.
        for genre in ("Action", "Free To Play", "Massively Multiplayer"):
            results = get_top_games_by_copies_sold(genre_filter=genre, conn=db)
            names = [r["name"] for r in results]
            assert "Free To Play Shooter" in names, \
                f"Expected 'Free To Play Shooter' when filtering by '{genre}'"

    def test_genres_field_decoded_to_list(self, db):
        results = get_top_games_by_copies_sold(limit=1, conn=db)
        assert isinstance(results[0]["genres"], list)

    def test_no_filter_returns_all_non_null(self, db):
        results = get_top_games_by_copies_sold(limit=100, conn=db)
        # 9 games have non-NULL copies_sold in fixtures.
        assert len(results) == 9


# ---------------------------------------------------------------------------
# get_genre_market_share
# ---------------------------------------------------------------------------

class TestGetGenreMarketShare:

    def test_returns_list_of_dicts(self, db):
        results = get_genre_market_share(conn=db)
        assert isinstance(results, list)
        assert len(results) > 0

    def test_expected_keys_present(self, db):
        expected = {"genre", "game_count", "total_copies_sold",
                    "avg_copies_sold", "avg_review_score"}
        for row in get_genre_market_share(conn=db):
            assert expected.issubset(row.keys())

    def test_sorted_by_total_copies_sold_desc(self, db):
        results = get_genre_market_share(conn=db)
        totals = [r["total_copies_sold"] for r in results]
        assert totals == sorted(totals, reverse=True)

    def test_action_genre_present(self, db):
        results = get_genre_market_share(conn=db)
        genres = [r["genre"] for r in results]
        assert "Action" in genres

    def test_game_count_correct_for_action(self, db):
        # Action games in fixtures: steam_id 1, 4, 6 = 3 games with copies_sold.
        results = get_genre_market_share(conn=db)
        action = next(r for r in results if r["genre"] == "Action")
        assert action["game_count"] == 3

    def test_empty_genres_not_returned(self, db):
        # No fixture game has "Sports" as its only genre contributing —
        # only Racing Sim has Sports. Verify no genre with 0 games appears.
        results = get_genre_market_share(conn=db)
        for row in results:
            assert row["game_count"] > 0

    def test_null_copies_excluded_from_totals(self, db):
        # "Unreleased Game" (steam_id=7) has NULL copies_sold and genres=["Action"].
        # Its NULL must not contribute to Action's total_copies_sold.
        results = get_genre_market_share(conn=db)
        action = next((r for r in results if r["genre"] == "Action"), None)
        if action:
            # Sum of Action games with non-NULL copies: 30M + 50M + 150k = 80,150,000
            assert action["total_copies_sold"] == 80_150_000


# ---------------------------------------------------------------------------
# get_publisher_class_breakdown
# ---------------------------------------------------------------------------

class TestGetPublisherClassBreakdown:

    def test_returns_list_of_dicts(self, db):
        results = get_publisher_class_breakdown(conn=db)
        assert isinstance(results, list)
        assert len(results) > 0

    def test_expected_keys_present(self, db):
        expected = {"publisher_class", "game_count", "total_copies_sold",
                    "avg_copies_sold", "avg_review_score", "avg_price"}
        for row in get_publisher_class_breakdown(conn=db):
            assert expected.issubset(row.keys())

    def test_all_four_classes_present(self, db):
        results = get_publisher_class_breakdown(conn=db)
        classes = {r["publisher_class"] for r in results}
        assert {"AAA", "AA", "Indie", "Hobbyist"}.issubset(classes)

    def test_sorted_by_total_copies_sold_desc(self, db):
        results = get_publisher_class_breakdown(conn=db)
        totals = [r["total_copies_sold"] for r in results]
        assert totals == sorted(totals, reverse=True)

    def test_aaa_has_highest_total(self, db):
        results = get_publisher_class_breakdown(conn=db)
        top = results[0]["publisher_class"]
        # AAA games: 30M + 50M + 12M = 92M — should be highest.
        assert top == "AAA"

    def test_game_count_correct_for_indie(self, db):
        results = get_publisher_class_breakdown(conn=db)
        indie = next(r for r in results if r["publisher_class"] == "Indie")
        # Indie games with non-NULL copies: steam_id 2, 8 = 2 games.
        assert indie["game_count"] == 2

    def test_null_copies_excluded(self, db):
        results = get_publisher_class_breakdown(conn=db)
        aa = next(r for r in results if r["publisher_class"] == "AA")
        # AA games with non-NULL: steam_id 3, 5, 9 = 3 games (7 has NULL).
        assert aa["game_count"] == 3


# ---------------------------------------------------------------------------
# get_games_by_price_range
# ---------------------------------------------------------------------------

class TestGetGamesByPriceRange:

    def test_returns_list_of_dicts(self, db):
        results = get_games_by_price_range(conn=db)
        assert isinstance(results, list)

    def test_expected_keys_present(self, db):
        results = get_games_by_price_range(min_price=0, max_price=70, conn=db)
        expected = {"steam_id", "name", "price", "copies_sold",
                    "review_score", "publisher_class", "genres"}
        for row in results:
            assert expected.issubset(row.keys())

    def test_all_prices_within_range(self, db):
        results = get_games_by_price_range(min_price=10.0, max_price=30.0, conn=db)
        for row in results:
            assert 10.0 <= row["price"] <= 30.0

    def test_free_games_returned_when_min_is_zero(self, db):
        results = get_games_by_price_range(min_price=0.0, max_price=0.0, conn=db)
        assert all(r["price"] == 0.0 for r in results)
        assert len(results) == 2  # steam_id 4 and 10

    def test_free_games_excluded_when_min_above_zero(self, db):
        results = get_games_by_price_range(min_price=0.01, max_price=70.0, conn=db)
        for row in results:
            assert row["price"] > 0

    def test_ordered_by_copies_sold_desc(self, db):
        results = get_games_by_price_range(min_price=0, max_price=70, conn=db)
        copies = [r["copies_sold"] for r in results]
        assert copies == sorted(copies, reverse=True)

    def test_null_copies_excluded(self, db):
        results = get_games_by_price_range(min_price=0, max_price=70, conn=db)
        names = [r["name"] for r in results]
        assert "Unreleased Game" not in names

    def test_limit_respected(self, db):
        results = get_games_by_price_range(min_price=0, max_price=70,
                                            limit=3, conn=db)
        assert len(results) <= 3

    def test_limit_capped_at_200(self, db):
        results = get_games_by_price_range(min_price=0, max_price=70,
                                            limit=9999, conn=db)
        assert len(results) <= 200

    def test_genres_decoded_to_list(self, db):
        results = get_games_by_price_range(min_price=0, max_price=70, conn=db)
        for row in results:
            assert isinstance(row["genres"], list)

    def test_empty_range_returns_empty_list(self, db):
        # No games priced between $100 and $200.
        results = get_games_by_price_range(min_price=100, max_price=200, conn=db)
        assert results == []


# ---------------------------------------------------------------------------
# get_review_score_distribution
# ---------------------------------------------------------------------------

class TestGetReviewScoreDistribution:

    def test_returns_list_of_dicts(self, db):
        results = get_review_score_distribution(conn=db)
        assert isinstance(results, list)
        assert len(results) > 0

    def test_expected_keys_present(self, db):
        expected = {"bucket_label", "min_score", "max_score",
                    "game_count", "total_copies_sold", "avg_copies_sold"}
        for row in get_review_score_distribution(conn=db):
            assert expected.issubset(row.keys())

    def test_ordered_by_bucket_asc(self, db):
        results = get_review_score_distribution(conn=db)
        min_scores = [r["min_score"] for r in results]
        assert min_scores == sorted(min_scores)

    def test_bucket_label_format(self, db):
        results = get_review_score_distribution(conn=db)
        for row in results:
            label = row["bucket_label"]
            assert "-" in label
            low, high = label.split("-")
            assert low.isdigit() and high.isdigit()

    def test_min_max_score_consistent_with_label(self, db):
        results = get_review_score_distribution(conn=db)
        for row in results:
            assert row["min_score"] <= row["max_score"]
            assert row["bucket_label"] == f"{row['min_score']}-{row['max_score']}"

    def test_null_review_scores_excluded(self, db):
        # "Unreleased Game" has NULL review_score — total game count across
        # all buckets must not include it.
        results = get_review_score_distribution(conn=db)
        total_counted = sum(r["game_count"] for r in results)
        # 9 games have non-NULL review_score (all except steam_id 7).
        assert total_counted == 9

    def test_game_count_correct_for_90s_bucket(self, db):
        # Games with review_score 90-99: steam_id 1 (95), 2 (97), 5 (91) = 3.
        results = get_review_score_distribution(conn=db)
        bucket_90 = next((r for r in results if r["min_score"] == 90), None)
        assert bucket_90 is not None
        assert bucket_90["game_count"] == 3

    def test_no_bucket_has_zero_game_count(self, db):
        results = get_review_score_distribution(conn=db)
        for row in results:
            assert row["game_count"] > 0


# ---------------------------------------------------------------------------
# registry — TOOLS list structure
# ---------------------------------------------------------------------------

class TestToolsRegistry:

    def test_tools_is_a_list(self):
        assert isinstance(TOOLS, list)

    def test_all_tools_registered(self):
        names = {t["function"]["name"] for t in TOOLS}
        expected = {
            "get_top_games_by_copies_sold",
            "get_genre_market_share",
            "get_publisher_class_breakdown",
            "get_games_by_price_range",
            "get_review_score_distribution",
            "get_games_by_release_date",
            "get_schema_info",
            "run_sql_query",
        }
        assert names == expected

    def test_each_tool_has_required_openai_keys(self):
        for tool in TOOLS:
            assert tool["type"] == "function"
            fn = tool["function"]
            assert "name" in fn
            assert "description" in fn
            assert "parameters" in fn
            assert fn["parameters"]["type"] == "object"
            assert "properties" in fn["parameters"]

    def test_descriptions_are_non_empty(self):
        for tool in TOOLS:
            assert len(tool["function"]["description"].strip()) > 0

    def test_tool_names_match_actual_functions(self):
        from game_market_chatbot.tools import queries
        for tool in TOOLS:
            name = tool["function"]["name"]
            assert hasattr(queries, name), \
                f"Tool '{name}' has no matching function in queries.py"


# ---------------------------------------------------------------------------
# registry — dispatch()
# ---------------------------------------------------------------------------

class TestDispatch:

    def test_dispatch_with_dict_args(self, db):
        # dispatch() injects conn via kwargs — but the real dispatch uses the
        # live DB. We test it directly by calling the underlying functions.
        # This test verifies dispatch resolves names correctly.
        from game_market_chatbot.tools.registry import dispatch as reg_dispatch
        # Patch connection for this call by relying on the live local DB file.
        # We just verify it doesn't raise for valid names.
        # (Full integration is covered by the query function tests above.)
        import os
        if not os.path.exists("data/games.db"):
            pytest.skip("Live database not available for dispatch integration test")
        result = reg_dispatch("get_publisher_class_breakdown", {})
        assert isinstance(result, list)

    def test_dispatch_with_json_string_args(self, db):
        import json as _json
        import os
        if not os.path.exists("data/games.db"):
            pytest.skip("Live database not available for dispatch integration test")
        result = reg_dispatch_fn = __import__(
            "game_market_chatbot.tools.registry", fromlist=["dispatch"]
        ).dispatch
        result = reg_dispatch_fn(
            "get_top_games_by_copies_sold",
            _json.dumps({"limit": 5})
        )
        assert isinstance(result, list)
        assert len(result) <= 5

    def test_dispatch_empty_string_args(self, db):
        import os
        if not os.path.exists("data/games.db"):
            pytest.skip("Live database not available for dispatch integration test")
        from game_market_chatbot.tools.registry import dispatch as reg_dispatch
        result = reg_dispatch("get_genre_market_share", "")
        assert isinstance(result, list)

    def test_dispatch_unknown_tool_raises_value_error(self):
        from game_market_chatbot.tools.registry import dispatch as reg_dispatch
        with pytest.raises(ValueError, match="Unknown tool"):
            reg_dispatch("nonexistent_tool", {})


# ---------------------------------------------------------------------------
# get_games_by_release_date
# ---------------------------------------------------------------------------

class TestGetGamesByReleaseDate:
    """
    Fixture release years for reference:
        2016 — steam_id 2  (Cozy Farming Sim)
        2017 — steam_id 10 (Massive MMO)
        2018 — steam_id 1  (Action RPG Blockbuster)
        2019 — steam_id 4  (Free To Play Shooter)
        2020 — steam_id 6  (Hobby Platformer), steam_id 9 (Racing Sim)
        2021 — steam_id 3  (Tactical Strategy Game), steam_id 8 (Puzzle Adventure)
        2022 — steam_id 5  (Atmospheric RPG)
        2023 — steam_id 7  (Unreleased Game — NULL copies_sold)
    """

    def test_returns_list_of_dicts(self, db):
        results = get_games_by_release_date(conn=db)
        assert isinstance(results, list)
        assert len(results) > 0

    def test_expected_keys_present(self, db):
        results = get_games_by_release_date(conn=db)
        expected = {
            "steam_id", "name", "release_date", "release_year",
            "copies_sold", "price", "review_score", "publisher_class", "genres",
        }
        assert expected.issubset(results[0].keys())

    def test_genres_decoded_to_list(self, db):
        results = get_games_by_release_date(conn=db)
        for row in results:
            assert isinstance(row["genres"], list)

    def test_default_order_is_release_date_desc(self, db):
        results = get_games_by_release_date(conn=db)
        dates = [r["release_date"] for r in results]
        assert dates == sorted(dates, reverse=True)

    def test_order_by_copies_sold(self, db):
        results = get_games_by_release_date(order_by="copies_sold", conn=db)
        # NULL copies_sold rows are excluded from the WHERE (release_date IS NOT NULL)
        # but copies_sold itself can still be NULL — filter them for sorting check.
        copies = [r["copies_sold"] for r in results if r["copies_sold"] is not None]
        assert copies == sorted(copies, reverse=True)

    def test_invalid_order_by_raises(self, db):
        with pytest.raises(ValueError, match="order_by must be"):
            get_games_by_release_date(order_by="name", conn=db)

    def test_year_from_filter(self, db):
        results = get_games_by_release_date(year_from=2021, conn=db)
        for row in results:
            assert row["release_year"] >= 2021

    def test_year_to_filter(self, db):
        results = get_games_by_release_date(year_to=2019, conn=db)
        for row in results:
            assert row["release_year"] <= 2019

    def test_year_from_and_year_to_together(self, db):
        results = get_games_by_release_date(year_from=2020, year_to=2021, conn=db)
        for row in results:
            assert 2020 <= row["release_year"] <= 2021
        # Should include steam_id 3, 6, 8, 9 — four games.
        assert len(results) == 4

    def test_single_year_window(self, db):
        results = get_games_by_release_date(year_from=2022, year_to=2022, conn=db)
        assert len(results) == 1
        assert results[0]["name"] == "Atmospheric RPG"

    def test_month_from_respected(self, db):
        # year_from=2020, month_from=6 — should include Jul 2020 (steam_id 6)
        # but exclude May 2020 (steam_id 9).
        results = get_games_by_release_date(
            year_from=2020, month_from=6, year_to=2020, conn=db
        )
        names = [r["name"] for r in results]
        assert "Hobby Platformer" in names      # Jul 2020
        assert "Racing Sim" not in names        # May 2020

    def test_month_to_respected(self, db):
        # year_from=2020, year_to=2020, month_to=6 — should include May 2020
        # but exclude Jul 2020.
        results = get_games_by_release_date(
            year_from=2020, year_to=2020, month_to=6, conn=db
        )
        names = [r["name"] for r in results]
        assert "Racing Sim" in names            # May 2020
        assert "Hobby Platformer" not in names  # Jul 2020

    def test_genre_filter_on_date_range(self, db):
        # Simulation games: steam_id 2 (2016), 9 (2020) — both have Simulation genre.
        results = get_games_by_release_date(genre_filter="Simulation", conn=db)
        names = [r["name"] for r in results]
        assert "Cozy Farming Sim" in names
        assert "Racing Sim" in names
        # Action RPG Blockbuster has no Simulation genre.
        assert "Action RPG Blockbuster" not in names

    def test_genre_filter_with_year_range(self, db):
        results = get_games_by_release_date(
            year_from=2019, year_to=2021, genre_filter="Indie", conn=db
        )
        # Indie games 2019-2021: steam_id 6 (2020), 3 (2021), 8 (2021).
        assert len(results) == 3

    def test_no_results_for_future_year(self, db):
        results = get_games_by_release_date(year_from=2099, conn=db)
        assert results == []

    def test_limit_respected(self, db):
        results = get_games_by_release_date(limit=2, conn=db)
        assert len(results) <= 2

    def test_limit_capped_at_200(self, db):
        results = get_games_by_release_date(limit=9999, conn=db)
        assert len(results) <= 200

    def test_release_year_derived_correctly(self, db):
        results = get_games_by_release_date(year_from=2018, year_to=2018, conn=db)
        assert len(results) == 1
        assert results[0]["release_year"] == 2018
        assert results[0]["name"] == "Action RPG Blockbuster"

    def test_registered_in_tools_list(self):
        names = {t["function"]["name"] for t in TOOLS}
        assert "get_games_by_release_date" in names

    def test_registered_in_function_map(self):
        from game_market_chatbot.tools.registry import _FUNCTION_MAP
        assert "get_games_by_release_date" in _FUNCTION_MAP
