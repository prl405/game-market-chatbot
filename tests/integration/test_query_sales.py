"""
Integration tests for tools.query_sales against the seeded in-memory db fixture.
"""

from __future__ import annotations

from game_market_chatbot.tools.query_sales import (
    get_games_by_price_range,
    get_top_games_by_copies_sold,
)



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
