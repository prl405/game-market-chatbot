"""
Integration tests for tools.query_releases against the seeded in-memory db fixture.
"""

from __future__ import annotations

import pytest

from game_market_chatbot.tools.query_releases import get_games_by_release_date



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
